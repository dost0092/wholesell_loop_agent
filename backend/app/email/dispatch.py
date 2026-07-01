"""Execute a single scheduled email send — orchestrates validation, compliance, and logging."""

from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.interfaces import OutboundEmail
from app.compliance.gates import can_send_message
from app.db.models import (
    ApprovalQueueItem,
    Contact,
    DeliveryStatus,
    EmailLog,
    Lead,
    LeadStatus,
    Message,
    MessageStatus,
)
from app.email.interfaces import EmailProvider
from app.email.logger import EmailLogService
from app.email.sender import GmailEmailProvider
from app.email.validator import validate_outbound_email

logger = logging.getLogger(__name__)


def _get_provider() -> EmailProvider:
    from app.config import get_settings

    settings = get_settings()
    if settings.email_provider == "gmail_api":
        return GmailEmailProvider()
    from app.adapters.email import get_email_sender

    # Wrap legacy bool-based senders in a thin adapter
    legacy = get_email_sender()

    class _LegacyAdapter(EmailProvider):
        name = getattr(legacy, "name", "legacy")

        def send(self, email: OutboundEmail):
            from app.email.interfaces import SendResult

            ok = legacy.send(email)
            return SendResult(success=ok, is_retryable=not ok)

    return _LegacyAdapter()


def execute_email_log(db: Session, email_log_id: int) -> EmailLog:
    """Process one ``EmailLog`` entry: validate, send, update status.

  Never raises — failures are recorded on the log entry.
    """
    log_svc = EmailLogService(db)
    entry = db.get(EmailLog, email_log_id)
    if entry is None:
        logger.error("EmailLog %s not found", email_log_id)
        raise ValueError(f"EmailLog {email_log_id} not found")

    if entry.delivery_status == DeliveryStatus.SENT:
        logger.info("EmailLog %s already sent — skipping", email_log_id)
        return entry

    message = db.get(Message, entry.message_id) if entry.message_id else None
    contact: Contact | None = None
    if message and message.contact_id:
        contact = db.get(Contact, message.contact_id)

    body = message.body if message else ""
    subject = entry.subject

    validation = validate_outbound_email(
        db,
        lead_id=entry.lead_id,
        recipient_email=entry.recipient_email,
        subject=subject,
        body=body,
        message=message,
    )
    if not validation.allowed:
        log_svc.mark_skipped(entry, validation.reason)
        db.commit()
        return entry

    if message is not None and contact is not None:
        allowed, reason = can_send_message(db, message, contact.value)
        if not allowed:
            log_svc.mark_skipped(entry, f"compliance:{reason}")
            db.commit()
            return entry

    log_svc.mark_sending(entry)
    db.commit()

    provider = _get_provider()
    start = time.monotonic()
    result = provider.send(
        OutboundEmail(
            to_email=entry.recipient_email,
            subject=subject,
            body_plain=body,
            lead_id=entry.lead_id,
            message_id=entry.message_id,
        )
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    if result.success:
        log_svc.mark_sent(entry, gmail_message_id=result.provider_message_id, duration_ms=duration_ms)
        if message is not None:
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            lead = db.get(Lead, entry.lead_id)
            if lead and lead.status == LeadStatus.OUTREACH_PENDING:
                lead.status = LeadStatus.CONTACTED
    else:
        log_svc.mark_failed(
            entry,
            error_message=result.error_message or "unknown error",
            retryable=result.is_retryable,
        )

    db.commit()
    db.refresh(entry)
    return entry


def find_approved_leads(db: Session, limit: int) -> list[ApprovalQueueItem]:
    """Return up to ``limit`` approved queue items not yet scheduled or sent today."""
    from app.db.models import ApprovalStatus
    from app.email.utils import today_start
    from app.config import get_settings

    settings = get_settings()
    day_start = today_start(settings.email_timezone)

    # Leads already scheduled or sent today
    scheduled_lead_ids = {
        row.lead_id
        for row in db.query(EmailLog.lead_id)
        .filter(EmailLog.scheduled_time >= day_start)
        .all()
    }

    query = (
        db.query(ApprovalQueueItem)
        .join(Message, ApprovalQueueItem.message_id == Message.id)
        .filter(
            ApprovalQueueItem.status.in_(
                [ApprovalStatus.APPROVED, ApprovalStatus.EDITED]
            ),
            Message.status == MessageStatus.APPROVED,
        )
        .order_by(ApprovalQueueItem.created_at)
    )
    if scheduled_lead_ids:
        query = query.filter(~ApprovalQueueItem.lead_id.in_(scheduled_lead_ids))
    return query.limit(limit).all()
