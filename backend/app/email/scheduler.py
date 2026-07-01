"""APScheduler-based daily email scheduler with restart recovery."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from functools import lru_cache
from threading import Lock
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.config import get_settings
from app.db.models import Contact, DeliveryStatus, EmailLog
from app.db.session import SessionLocal
from app.email.dispatch import execute_email_log, find_approved_leads
from app.email.logger import EmailLogService
from app.email.utils import compute_send_schedule, parse_time_hm, today_start

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_lock = Lock()


class DailyEmailScheduler:
    """Plans and executes the daily batch of personalized outreach emails.

    On startup, ``resume_pending()`` re-schedules any unsent ``EmailLog``
    entries so restarts never cause duplicates or missed sends.
    """

    def __init__(self):
        self._settings = get_settings()

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self._settings.email_timezone)

    def plan_daily_sends(self) -> int:
        """Find approved leads and schedule up to ``emails_per_day`` sends.

        Returns the number of new ``EmailLog`` entries created.
        """
        settings = self._settings
        db = SessionLocal()
        try:
            log_svc = EmailLogService(db)
            already = log_svc.count_scheduled_today(settings.email_timezone)
            remaining = max(0, settings.emails_per_day - already)
            if remaining == 0:
                logger.info("Daily email quota already planned (%d)", already)
                return 0

            items = find_approved_leads(db, limit=remaining)
            if not items:
                logger.info("No approved leads available for scheduling")
                return 0

            hour, minute = parse_time_hm(settings.email_start_time)
            tz = self.timezone
            now = datetime.now(tz)
            start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if start < now:
                # If we're past start time today, begin from now + small buffer
                start = now + timedelta(minutes=1)

            send_times = compute_send_schedule(
                start,
                len(items),
                interval_minutes=settings.email_interval_minutes,
                jitter_min=settings.email_jitter_min_minutes,
                jitter_max=settings.email_jitter_max_minutes,
            )

            created = 0
            for item, scheduled_time in zip(items, send_times):
                message = item.message
                contact = (
                    db.get(Contact, message.contact_id) if message and message.contact_id else None
                )
                if contact is None:
                    logger.warning("Skipping approval item %s — no contact", item.id)
                    continue

                entry = log_svc.create_scheduled(
                    lead_id=item.lead_id,
                    message_id=message.id if message else None,
                    recipient_email=contact.value,
                    subject=message.subject or item.draft_subject or "",
                    body=message.body if message else item.draft_body,
                    scheduled_time=scheduled_time,
                )
                created += 1
                self._schedule_send(entry.id, scheduled_time)

            db.commit()
            logger.info("Planned %d emails for today", created)
            return created
        finally:
            db.close()

    def resume_pending(self) -> int:
        """Re-schedule unsent EmailLog entries after a restart."""
        db = SessionLocal()
        try:
            log_svc = EmailLogService(db)
            pending = log_svc.get_pending()
            tz = self.timezone
            now = datetime.now(tz)
            count = 0
            for entry in pending:
                fire_at = entry.scheduled_time
                if fire_at.tzinfo is None:
                    fire_at = fire_at.replace(tzinfo=tz)
                if fire_at < now:
                    # Overdue — fire soon with small stagger
                    fire_at = now + timedelta(seconds=random.randint(5, 30))
                self._schedule_send(entry.id, fire_at)
                count += 1
            logger.info("Resumed %d pending email sends", count)
            return count
        finally:
            db.close()

    def _schedule_send(self, email_log_id: int, run_at: datetime) -> None:
        scheduler = get_email_scheduler()
        scheduler.add_job(
            _job_send_email,
            trigger=DateTrigger(run_date=run_at),
            id=f"email_send_{email_log_id}",
            replace_existing=True,
            kwargs={"email_log_id": email_log_id},
            misfire_grace_time=3600,
        )

    def schedule_retry(self, email_log_id: int, retry_count: int) -> None:
        """Schedule a failed send for exponential-backoff retry."""
        settings = self._settings
        delay_sec = settings.email_retry_base_seconds * (2 ** max(0, retry_count - 1))
        # Cap at 1 hour
        delay_sec = min(delay_sec, 3600)
        run_at = datetime.now(self.timezone) + timedelta(seconds=delay_sec)
        self._schedule_send(email_log_id, run_at)
        logger.info(
            "Retry scheduled for email_log %s in %ds", email_log_id, delay_sec
        )


def _job_send_email(email_log_id: int) -> None:
    """APScheduler job target — isolated DB session per execution."""
    db = SessionLocal()
    try:
        entry = execute_email_log(db, email_log_id)
        if entry.delivery_status == DeliveryStatus.RETRY_PENDING:
            planner = DailyEmailScheduler()
            planner.schedule_retry(entry.id, entry.retry_count)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error in email send job %s: %s", email_log_id, exc)
    finally:
        db.close()


def _job_plan_daily() -> None:
    try:
        DailyEmailScheduler().plan_daily_sends()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Daily email planning failed: %s", exc)


def start_email_scheduler() -> BackgroundScheduler | None:
    """Start the background scheduler if ``EMAIL_SCHEDULER_ENABLED=true``."""
    global _scheduler
    settings = get_settings()
    if not settings.email_scheduler_enabled:
        logger.info("Email scheduler disabled (EMAIL_SCHEDULER_ENABLED=false)")
        return None

    with _lock:
        if _scheduler is not None and _scheduler.running:
            return _scheduler

        tz = settings.email_timezone
        hour, minute = settings.email_start_hour_minute

        _scheduler = BackgroundScheduler(timezone=tz)
        _scheduler.add_job(
            _job_plan_daily,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id="daily_email_plan",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            "Email scheduler started (daily plan at %02d:%02d %s)",
            hour,
            minute,
            tz,
        )

        planner = DailyEmailScheduler()
        planner.resume_pending()

        # If we're starting after today's plan time and nothing scheduled yet, plan now
        db = SessionLocal()
        try:
            log_svc = EmailLogService(db)
            if log_svc.count_scheduled_today(tz) == 0:
                now = datetime.now(ZoneInfo(tz))
                plan_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if now >= plan_time:
                    planner.plan_daily_sends()
        finally:
            db.close()

        return _scheduler


def stop_email_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("Email scheduler stopped")
        _scheduler = None


@lru_cache
def get_email_scheduler() -> BackgroundScheduler:
    """Return the running scheduler instance (starts it if needed)."""
    sched = start_email_scheduler()
    if sched is None:
        # Return a dormant scheduler for test injection
        return BackgroundScheduler()
    return sched
