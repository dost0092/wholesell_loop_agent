"""Production-grade Gmail email sending module.

Provides OAuth 2.0 authentication, scheduled daily sends, retry logic,
and persistent logging for the wholesaling outreach pipeline.
"""

from app.email.monitoring import EmailMonitoringStats, get_email_stats
from app.email.scheduler import DailyEmailScheduler, get_email_scheduler

__all__ = [
    "DailyEmailScheduler",
    "EmailMonitoringStats",
    "get_email_scheduler",
    "get_email_stats",
]
