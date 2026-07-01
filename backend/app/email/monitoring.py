"""Email send monitoring and statistics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import DeliveryStatus, EmailLog
from app.email.utils import today_start


@dataclass
class EmailMonitoringStats:
    total_scheduled: int
    total_sent: int
    total_failed: int
    total_skipped: int
    total_retry_pending: int
    next_scheduled_email: datetime | None
    average_send_duration_ms: float | None
    retry_total: int
    retry_average: float


def get_email_stats(db: Session, *, tz_name: str = "America/Chicago") -> EmailMonitoringStats:
    """Aggregate send statistics for monitoring dashboards and health checks."""
    day_start = today_start(tz_name)

    today_logs = db.query(EmailLog).filter(EmailLog.scheduled_time >= day_start)

    total_scheduled = today_logs.count()
    total_sent = today_logs.filter(EmailLog.delivery_status == DeliveryStatus.SENT).count()
    total_failed = today_logs.filter(EmailLog.delivery_status == DeliveryStatus.FAILED).count()
    total_skipped = today_logs.filter(EmailLog.delivery_status == DeliveryStatus.SKIPPED).count()
    total_retry = today_logs.filter(
        EmailLog.delivery_status == DeliveryStatus.RETRY_PENDING
    ).count()

    next_entry = (
        db.query(EmailLog)
        .filter(
            EmailLog.delivery_status.in_(
                [DeliveryStatus.SCHEDULED, DeliveryStatus.RETRY_PENDING]
            ),
            EmailLog.scheduled_time >= day_start,
        )
        .order_by(EmailLog.scheduled_time)
        .first()
    )

    avg_duration = (
        db.query(func.avg(EmailLog.send_duration_ms))
        .filter(
            EmailLog.delivery_status == DeliveryStatus.SENT,
            EmailLog.scheduled_time >= day_start,
            EmailLog.send_duration_ms.isnot(None),
        )
        .scalar()
    )

    retry_sum = (
        db.query(func.sum(EmailLog.retry_count))
        .filter(EmailLog.scheduled_time >= day_start)
        .scalar()
    ) or 0

    sent_with_retries = today_logs.filter(EmailLog.retry_count > 0).count()
    retry_avg = (retry_sum / sent_with_retries) if sent_with_retries else 0.0

    return EmailMonitoringStats(
        total_scheduled=total_scheduled,
        total_sent=total_sent,
        total_failed=total_failed,
        total_skipped=total_skipped,
        total_retry_pending=total_retry,
        next_scheduled_email=next_entry.scheduled_time if next_entry else None,
        average_send_duration_ms=float(avg_duration) if avg_duration else None,
        retry_total=int(retry_sum),
        retry_average=retry_avg,
    )
