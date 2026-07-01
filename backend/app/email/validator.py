"""Pre-send safety checks — every outbound email passes through here."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email as ev_validate

from app.compliance.gates import is_on_dnc_list
from app.db.models import DeliveryStatus, EmailLog, Message
from app.email.utils import hash_body
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Common spam-trigger phrases to flag (logged, not hard-blocked)
_SPAM_PHRASES = (
    "act now",
    "limited time",
    "guaranteed",
    "100% free",
    "click here",
    "buy now",
    "no obligation",
    "risk-free",
    "make money fast",
)


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    reason: str = "ok"


def _valid_email_format(address: str) -> bool:
    try:
        ev_validate(address, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _has_spam_phrases(text: str) -> list[str]:
    lower = text.lower()
    return [p for p in _SPAM_PHRASES if p in lower]


def validate_outbound_email(
    db: Session,
    *,
    lead_id: int,
    recipient_email: str,
    subject: str,
    body: str,
    message: Message | None = None,
) -> ValidationResult:
    """Run all safety checks before a send attempt.

    Returns ``ValidationResult(allowed=False, reason=...)`` when the email
    must be skipped. Every skip reason is suitable for audit logging.
    """
    if not recipient_email or not recipient_email.strip():
        return ValidationResult(False, "empty_recipient")

    if not _valid_email_format(recipient_email.strip()):
        return ValidationResult(False, "invalid_email_format")

    if not subject or not subject.strip():
        return ValidationResult(False, "empty_subject")

    if not body or not body.strip():
        return ValidationResult(False, "empty_body")

    if is_on_dnc_list(db, recipient_email):
        return ValidationResult(False, "opted_out_dnc")

    # Bounced addresses — prior permanent failure logged as bounced
    bounced = (
        db.query(EmailLog)
        .filter(
            EmailLog.recipient_email == recipient_email.strip().lower(),
            EmailLog.delivery_status == DeliveryStatus.BOUNCED,
        )
        .first()
    )
    if bounced:
        return ValidationResult(False, "previously_bounced")

    # Duplicate send to same lead (already sent successfully)
    already_sent = (
        db.query(EmailLog)
        .filter(
            EmailLog.lead_id == lead_id,
            EmailLog.delivery_status == DeliveryStatus.SENT,
        )
        .first()
    )
    if already_sent:
        return ValidationResult(False, "duplicate_lead_send")

    # Duplicate send to same message
    if message is not None:
        msg_sent = (
            db.query(EmailLog)
            .filter(
                EmailLog.message_id == message.id,
                EmailLog.delivery_status == DeliveryStatus.SENT,
            )
            .first()
        )
        if msg_sent:
            return ValidationResult(False, "duplicate_message_send")

    spam_hits = _has_spam_phrases(subject + " " + body)
    if spam_hits:
        logger.warning(
            "Email to lead %s contains spam-trigger phrases: %s",
            lead_id,
            spam_hits,
        )

    return ValidationResult(True)
