"""EmailLog persistence service — every send attempt is recorded."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import DeliveryStatus, EmailLog
from app.email.utils import hash_body, today_start

logger = logging.getLogger(__name__)


class EmailLogService:
    """CRUD helpers for the ``email_logs`` table."""

    def __init__(self, db: Session):
        self._db = db

    def create_scheduled(
        self,
        *,
        lead_id: int,
        message_id: int | None,
        recipient_email: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
    ) -> EmailLog:
        entry = EmailLog(
            lead_id=lead_id,
            message_id=message_id,
            recipient_email=recipient_email.strip().lower(),
            subject=subject,
            body_hash=hash_body(body),
            scheduled_time=scheduled_time,
            delivery_status=DeliveryStatus.SCHEDULED,
        )
        self._db.add(entry)
        self._db.flush()
        logger.info(
            "Scheduled email log %s for lead %s at %s",
            entry.id,
            lead_id,
            scheduled_time.isoformat(),
        )
        return entry

    def mark_sending(self, entry: EmailLog) -> None:
        entry.delivery_status = DeliveryStatus.SENDING
        self._db.flush()

    def mark_sent(
        self,
        entry: EmailLog,
        *,
        gmail_message_id: str | None,
        duration_ms: int,
    ) -> None:
        entry.delivery_status = DeliveryStatus.SENT
        entry.sent_time = datetime.utcnow()
        entry.gmail_message_id = gmail_message_id
        entry.send_duration_ms = duration_ms
        entry.error_message = None
        self._db.flush()
        logger.info("Email log %s sent (gmail_id=%s)", entry.id, gmail_message_id)

    def mark_failed(
        self,
        entry: EmailLog,
        *,
        error_message: str,
        retryable: bool,
    ) -> None:
        entry.retry_count += 1
        entry.error_message = error_message[:2000]
        if retryable and entry.retry_count < _max_retries():
            entry.delivery_status = DeliveryStatus.RETRY_PENDING
        else:
            entry.delivery_status = DeliveryStatus.FAILED
        self._db.flush()
        logger.warning(
            "Email log %s failed (retry=%s, retryable=%s): %s",
            entry.id,
            entry.retry_count,
            retryable,
            error_message,
        )

    def mark_skipped(self, entry: EmailLog, reason: str) -> None:
        entry.delivery_status = DeliveryStatus.SKIPPED
        entry.skip_reason = reason
        self._db.flush()
        logger.info("Email log %s skipped: %s", entry.id, reason)

    def mark_bounced(self, entry: EmailLog, reason: str) -> None:
        entry.delivery_status = DeliveryStatus.BOUNCED
        entry.error_message = reason
        self._db.flush()

    def count_scheduled_today(self, tz_name: str) -> int:
        day_start = today_start(tz_name)
        return (
            self._db.query(EmailLog)
            .filter(EmailLog.scheduled_time >= day_start)
            .count()
        )

    def get_pending(self) -> list[EmailLog]:
        """Return logs that still need to be sent (scheduled or awaiting retry)."""
        return (
            self._db.query(EmailLog)
            .filter(
                EmailLog.delivery_status.in_(
                    [DeliveryStatus.SCHEDULED, DeliveryStatus.RETRY_PENDING]
                )
            )
            .order_by(EmailLog.scheduled_time)
            .all()
        )

    def commit(self) -> None:
        self._db.commit()


def _max_retries() -> int:
    from app.config import get_settings

    return get_settings().email_max_retries
