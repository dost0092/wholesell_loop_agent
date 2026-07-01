"""Shared helpers for the email module."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def hash_body(body: str) -> str:
    """SHA-256 hex digest of email body for deduplication checks."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def compute_send_schedule(
    start: datetime,
    count: int,
    interval_minutes: int = 60,
    jitter_min: int = 5,
    jitter_max: int = 10,
) -> list[datetime]:
    """Build staggered send times with random ± jitter between sends.

    First email fires at ``start``; each subsequent slot adds
    ``interval_minutes`` plus a random offset of ±[jitter_min, jitter_max].
    """
    if count <= 0:
        return []

    times = [start]
    current = start
    for _ in range(count - 1):
        jitter = random.randint(jitter_min, jitter_max)
        sign = random.choice([-1, 1])
        delta = timedelta(minutes=interval_minutes + sign * jitter)
        current = current + delta
        times.append(current)
    return times


def today_start(tz_name: str) -> datetime:
    """Midnight today in the configured timezone."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_time_hm(value: str) -> tuple[int, int]:
    """Parse ``HH:MM`` into hour and minute integers."""
    parts = value.strip().split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
