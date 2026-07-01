"""Low-level Gmail API client — handles MIME encoding and API errors."""

from __future__ import annotations

import base64
import logging
import time
from email.message import EmailMessage

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app.adapters.interfaces import OutboundEmail
from app.config import get_settings
from app.email.interfaces import SendResult

logger = logging.getLogger(__name__)

# Gmail API user alias for the authenticated account
_GMAIL_USER = "me"

# HTTP status codes that warrant a retry
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GmailClient:
    """Thin wrapper around the Gmail API ``users.messages.send`` endpoint."""

    def __init__(self, credentials: Credentials):
        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self._settings = get_settings()

    def _build_mime(self, email: OutboundEmail) -> EmailMessage:
        settings = self._settings
        msg = EmailMessage()
        from_email = settings.sender_email or settings.smtp_from_email
        from_name = settings.email_sender_name or settings.smtp_from_name
        from_header = f"{from_name} <{from_email}>" if from_name else from_email
        msg["From"] = from_header
        msg["To"] = email.to_email
        msg["Subject"] = email.subject
        msg.set_content(email.body_plain)
        return msg

    @staticmethod
    def _encode_message(msg: EmailMessage) -> dict:
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        return {"raw": raw}

    def send(self, email: OutboundEmail) -> SendResult:
        """Send a single plain-text email via the Gmail API."""
        mime = self._build_mime(email)
        body = self._encode_message(mime)

        try:
            result = (
                self._service.users()
                .messages()
                .send(userId=_GMAIL_USER, body=body)
                .execute()
            )
            message_id = result.get("id")
            logger.info("Gmail API sent to %s (id=%s)", email.to_email, message_id)
            return SendResult(success=True, provider_message_id=message_id)

        except HttpError as exc:
            status = exc.resp.status if exc.resp else 0
            error_text = str(exc)
            retryable = status in _RETRYABLE_STATUS
            logger.error(
                "Gmail API error sending to %s (status=%s): %s",
                email.to_email,
                status,
                error_text,
            )
            return SendResult(
                success=False,
                error_message=error_text,
                is_retryable=retryable,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected Gmail send error to %s: %s", email.to_email, exc)
            return SendResult(
                success=False,
                error_message=str(exc),
                is_retryable=True,
            )

    def send_with_backoff(
        self,
        email: OutboundEmail,
        *,
        max_attempts: int = 3,
        base_delay: float = 2.0,
    ) -> SendResult:
        """Send with inline exponential backoff for rate-limit bursts."""
        last: SendResult = SendResult(success=False, error_message="no attempt")
        for attempt in range(max_attempts):
            last = self.send(email)
            if last.success or not last.is_retryable:
                return last
            delay = base_delay * (2**attempt)
            logger.info("Gmail rate limit — retrying in %.1fs (attempt %s)", delay, attempt + 1)
            time.sleep(delay)
        return last
