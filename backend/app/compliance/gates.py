"""Compliance gates checked before every outbound send path."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import DncEntry, Message


def is_on_dnc_list(db: Session, value: str) -> bool:
    normalized = value.strip().lower()
    return db.query(DncEntry).filter(DncEntry.value == normalized).first() is not None


def can_send_message(db: Session, message: Message, contact_value: str) -> tuple[bool, str]:
    """
    Returns (allowed, reason). Every send path must call this — no exceptions.
    """
    settings = get_settings()

    if settings.require_human_approval and message.status.value not in ("approved",):
        return False, "Human approval required (REQUIRE_HUMAN_APPROVAL=true)"

    if not message.compliance_checked:
        return False, "Message has not passed compliance review"

    if is_on_dnc_list(db, contact_value):
        return False, "Contact is on Do Not Contact list"

    return True, "ok"
