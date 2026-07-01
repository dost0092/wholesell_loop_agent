"""Gmail API email provider — implements the swappable ``EmailProvider`` interface."""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.adapters.interfaces import OutboundEmail
from app.config import get_settings
from app.db.session import SessionLocal
from app.email.gmail_client import GmailClient
from app.email.interfaces import EmailProvider, SendResult
from app.email.oauth import OAuthError, get_gmail_credentials
from app.email.templates import ensure_signature

logger = logging.getLogger(__name__)


class GmailEmailProvider(EmailProvider):
    """Production Gmail sender using OAuth 2.0 and the Gmail API."""

    name = "gmail_api"

    def __init__(self, db: Session | None = None):
        self._db = db

    def _get_client(self) -> GmailClient:
        db = self._db
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True
        try:
            creds = get_gmail_credentials(db)
            return GmailClient(creds)
        except OAuthError:
            if own_session:
                db.close()
            raise
        finally:
            if own_session:
                db.close()

    def send(self, email: OutboundEmail) -> SendResult:
        settings = get_settings()
        body = ensure_signature(email.body_plain)

        outbound = OutboundEmail(
            to_email=email.to_email,
            subject=email.subject,
            body_plain=body,
            lead_id=email.lead_id,
            message_id=email.message_id,
        )

        start = time.monotonic()
        try:
            client = self._get_client()
            result = client.send_with_backoff(
                outbound,
                max_attempts=settings.email_max_retries,
                base_delay=settings.email_retry_base_seconds / 60.0,
            )
        except OAuthError as exc:
            logger.error("Gmail OAuth error: %s", exc)
            return SendResult(success=False, error_message=str(exc), is_retryable=False)

        if result.success:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "Gmail send OK to %s in %dms (msg_id=%s)",
                email.to_email,
                duration_ms,
                result.provider_message_id,
            )
        return result
