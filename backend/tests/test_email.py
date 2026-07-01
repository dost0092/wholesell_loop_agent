"""Unit tests for the Gmail email sending module."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.adapters.interfaces import OutboundEmail
from app.db.models import (
    ApprovalQueueItem,
    ApprovalStatus,
    Contact,
    DeliveryStatus,
    EmailLog,
    Lead,
    LeadStatus,
    Message,
    MessageChannel,
    MessageDirection,
    MessageStatus,
    Owner,
)
from app.email.dispatch import execute_email_log, find_approved_leads
from app.email.interfaces import SendResult
from app.email.logger import EmailLogService
from app.email.monitoring import get_email_stats
from app.email.utils import compute_send_schedule, hash_body
from app.email.validator import validate_outbound_email
from app.services.outreach import approve_item, generate_drafts


def _approved_lead_setup(db_session) -> tuple[Lead, ApprovalQueueItem]:
    lead = Lead(
        state="TX",
        county="Harris",
        source_module="tx.harris.tax_sale",
        property_address="456 Oak Ave HOUSTON TX 77002",
        city="Houston",
        parcel_id="EMAIL_TEST",
        status=LeadStatus.VALIDATED,
    )
    db_session.add(lead)
    db_session.flush()
    owner = Owner(lead_id=lead.id, name="Jane Doe")
    db_session.add(owner)
    db_session.flush()
    db_session.add(
        Contact(
            owner_id=owner.id,
            contact_type="email",
            value="jane@example.com",
            validated=True,
            confidence_score=0.95,
        )
    )
    db_session.commit()
    db_session.refresh(lead)
    item = generate_drafts(db_session, lead)
    approve_item(db_session, item, reviewer="tester")
    return lead, item


# --- utils -------------------------------------------------------------------


def test_hash_body_deterministic():
    assert hash_body("hello") == hash_body("hello")
    assert hash_body("hello") != hash_body("world")


def test_compute_send_schedule_count():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
    times = compute_send_schedule(start, 3, interval_minutes=60, jitter_min=5, jitter_max=10)
    assert len(times) == 3
    assert times[0] == start
    for i in range(1, len(times)):
        delta = times[i] - times[i - 1]
        # ~55-70 minutes between sends
        assert timedelta(minutes=50) < delta < timedelta(minutes=75)


# --- validator ---------------------------------------------------------------


def test_validator_rejects_empty_subject(db_session):
    lead, item = _approved_lead_setup(db_session)
    result = validate_outbound_email(
        db_session,
        lead_id=lead.id,
        recipient_email="jane@example.com",
        subject="",
        body="Hello there",
    )
    assert result.allowed is False
    assert result.reason == "empty_subject"


def test_validator_rejects_invalid_email(db_session):
    lead, _ = _approved_lead_setup(db_session)
    result = validate_outbound_email(
        db_session,
        lead_id=lead.id,
        recipient_email="not-an-email",
        subject="Hi",
        body="Hello",
    )
    assert result.allowed is False
    assert result.reason == "invalid_email_format"


# --- dispatch ----------------------------------------------------------------


def test_find_approved_leads(db_session):
    lead, item = _approved_lead_setup(db_session)
    found = find_approved_leads(db_session, limit=10)
    assert len(found) == 1
    assert found[0].id == item.id


@patch("app.email.dispatch._get_provider")
def test_execute_email_log_sends(mock_provider, db_session):
    lead, item = _approved_lead_setup(db_session)
    message = item.message

    mock_provider.return_value = MagicMock()
    mock_provider.return_value.send.return_value = SendResult(
        success=True, provider_message_id="gmail-abc123"
    )

    log_svc = EmailLogService(db_session)
    entry = log_svc.create_scheduled(
        lead_id=lead.id,
        message_id=message.id,
        recipient_email="jane@example.com",
        subject=message.subject or "",
        body=message.body,
        scheduled_time=datetime.utcnow(),
    )
    db_session.commit()

    result = execute_email_log(db_session, entry.id)
    assert result.delivery_status == DeliveryStatus.SENT
    assert result.gmail_message_id == "gmail-abc123"
    db_session.refresh(message)
    assert message.status == MessageStatus.SENT


@patch("app.email.dispatch._get_provider")
def test_execute_email_log_skips_duplicate(mock_provider, db_session):
    lead, item = _approved_lead_setup(db_session)
    message = item.message

    log_svc = EmailLogService(db_session)
    log_svc.create_scheduled(
        lead_id=lead.id,
        message_id=message.id,
        recipient_email="jane@example.com",
        subject="Hi",
        body=message.body,
        scheduled_time=datetime.utcnow(),
    )
    sent = EmailLog(
        lead_id=lead.id,
        message_id=message.id,
        recipient_email="jane@example.com",
        subject="Hi",
        body_hash=hash_body(message.body),
        scheduled_time=datetime.utcnow(),
        delivery_status=DeliveryStatus.SENT,
        sent_time=datetime.utcnow(),
    )
    db_session.add(sent)
    db_session.commit()

    entry = log_svc.create_scheduled(
        lead_id=lead.id,
        message_id=message.id,
        recipient_email="jane@example.com",
        subject="Hi again",
        body=message.body,
        scheduled_time=datetime.utcnow(),
    )
    db_session.commit()

    result = execute_email_log(db_session, entry.id)
    assert result.delivery_status == DeliveryStatus.SKIPPED
    mock_provider.assert_not_called()


# --- monitoring --------------------------------------------------------------


def test_email_stats_empty(db_session):
    stats = get_email_stats(db_session)
    assert stats.total_scheduled == 0
    assert stats.total_sent == 0


# --- gmail client (mocked) ---------------------------------------------------


@patch("app.email.gmail_client.build")
def test_gmail_client_send_success(mock_build):
    from app.email.gmail_client import GmailClient

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg-123"
    }

    client = GmailClient(credentials=MagicMock())
    result = client.send(
        OutboundEmail(to_email="test@example.com", subject="Hi", body_plain="Hello")
    )
    assert result.success is True
    assert result.provider_message_id == "msg-123"


# --- email agent -------------------------------------------------------------


def test_generate_personalized_email_template():
    from app.agents.email_agent import generate_personalized_email

    lead = Lead(
        state="TX",
        county="Harris",
        source_module="test",
        property_address="123 Main St",
        city="Houston",
        id=42,
    )
    owner = Owner(name="John Smith")
    subject, body = generate_personalized_email(lead, owner)
    assert subject
    assert "John" in body or "there" in body
    assert "STOP" in body
