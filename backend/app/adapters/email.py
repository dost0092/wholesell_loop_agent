"""Phase 5 — email senders.

- ConsoleEmailSender: logs the message instead of sending. Default when SMTP is
  not configured, so the full pipeline is testable without a mailbox.
- SmtpEmailSender: real send via the user's own SMTP (e.g. Gmail App Password).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.adapters.interfaces import EmailSender, OutboundEmail
from app.config import get_settings

logger = logging.getLogger(__name__)


class ConsoleEmailSender(EmailSender):
    name = "console"

    def send(self, email: OutboundEmail) -> bool:
        logger.info(
            "[CONSOLE EMAIL] to=%s subject=%s\n%s",
            email.to_email,
            email.subject,
            email.body_plain,
        )
        return True


class SmtpEmailSender(EmailSender):
    name = "smtp"

    def __init__(self):
        self._settings = get_settings()

    def send(self, email: OutboundEmail) -> bool:
        s = self._settings
        msg = EmailMessage()
        from_email = s.smtp_from_email or s.smtp_user
        from_display = f"{s.smtp_from_name} <{from_email}>" if s.smtp_from_name else from_email
        msg["From"] = from_display
        msg["To"] = email.to_email
        msg["Subject"] = email.subject
        msg.set_content(email.body_plain)

        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as server:
                if s.smtp_use_tls:
                    server.starttls()
                if s.smtp_user and s.smtp_password:
                    server.login(s.smtp_user, s.smtp_password)
                server.send_message(msg)
            logger.info("Sent email to %s", email.to_email)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("SMTP send failed to %s: %s", email.to_email, exc)
            return False


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.smtp_user and settings.smtp_password:
        return SmtpEmailSender()
    return ConsoleEmailSender()
