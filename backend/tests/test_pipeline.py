"""Tests for Phase 3-5: scoring, owner discovery, validation, outreach."""

from __future__ import annotations

from app.db.models import (
    ApprovalStatus,
    Contact,
    DncEntry,
    Lead,
    LeadStatus,
    MessageStatus,
    Owner,
)
from app.services.contact_validation import validate_email, validate_lead_contacts, validate_phone
from app.services.outreach import approve_item, generate_drafts, reject_item, send_item
from app.services.owner_discovery import trace_lead
from app.services.pipeline import run_pipeline
from app.services.scoring import score_lead


def _make_lead(db, **overrides) -> Lead:
    lead = Lead(
        state="TX",
        county="Harris",
        source_module="tx.harris.tax_sale",
        property_address="123 Main St HOUSTON TX 77002",
        city="Houston",
        zip_code="77002",
        parcel_id="TEST123",
        distress_signals=["tax_sale_scheduled", "vacant"],
        raw_data={"owner_of_record": "John Smith", "minimum_bid": 15000.0, "adjudged_value": 120000.0},
        status=LeadStatus.NEW,
    )
    for k, v in overrides.items():
        setattr(lead, k, v)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


# --- Phase 3: scoring ---------------------------------------------------------


def test_score_lead_sets_fields_and_status(db_session):
    lead = _make_lead(db_session)
    score_lead(db_session, lead)

    assert lead.deal_score is not None
    assert 0 <= lead.deal_score <= 100
    assert lead.score_reasoning
    assert lead.motivation_summary
    assert lead.offer_strategy
    assert lead.status == LeadStatus.SCORED


def test_high_urgency_scores_higher(db_session):
    hot = _make_lead(db_session, distress_signals=["tax_sale_scheduled"], parcel_id="HOT")
    cold = _make_lead(
        db_session, distress_signals=["code_violation"], parcel_id="COLD", raw_data={}
    )
    score_lead(db_session, hot)
    score_lead(db_session, cold)
    assert hot.deal_score > cold.deal_score


# --- Phase 4: owner discovery -------------------------------------------------


def test_trace_creates_owner_and_contacts(db_session):
    lead = _make_lead(db_session)
    owner = trace_lead(db_session, lead)

    assert owner.id is not None
    assert owner.name == "John Smith"
    assert len(owner.contacts) >= 1
    assert lead.status == LeadStatus.TRACED
    assert any(c.contact_type == "email" for c in owner.contacts)


def test_trace_detects_llc(db_session):
    lead = _make_lead(
        db_session, raw_data={"owner_of_record": "ACME HOLDINGS LLC"}, parcel_id="LLC1"
    )
    owner = trace_lead(db_session, lead)
    assert owner.is_llc is True


# --- Phase 5a: validation -----------------------------------------------------


def test_validate_email_syntax():
    assert validate_email("bad").is_valid is False
    assert validate_email("a@b.test").is_valid is False  # non-deliverable domain


def test_validate_phone_normalizes():
    result = validate_phone("(713) 555-1234")
    assert result.is_valid is True
    assert result.details["normalized"] == "+17135551234"


def test_validate_lead_contacts_scrubs_dnc(db_session):
    lead = _make_lead(db_session)
    owner = Owner(lead_id=lead.id, name="John Smith")
    db_session.add(owner)
    db_session.flush()
    db_session.add(
        Contact(owner_id=owner.id, contact_type="email", value="john@gmail.com", source="mock")
    )
    db_session.add(DncEntry(value="john@gmail.com", contact_type="email"))
    lead.status = LeadStatus.TRACED
    db_session.commit()

    result = validate_lead_contacts(db_session, lead)
    contact = db_session.query(Contact).first()
    assert contact.validated is False
    assert result["invalid"] >= 1


# --- Phase 5b: outreach + approval --------------------------------------------


def _lead_with_valid_email(db_session) -> Lead:
    lead = _make_lead(db_session)
    owner = Owner(lead_id=lead.id, name="John Smith")
    db_session.add(owner)
    db_session.flush()
    db_session.add(
        Contact(
            owner_id=owner.id,
            contact_type="email",
            value="john@gmail.com",
            validated=True,
            confidence_score=0.9,
            source="mock",
        )
    )
    lead.status = LeadStatus.VALIDATED
    db_session.commit()
    db_session.refresh(lead)
    return lead


def test_generate_draft_creates_approval_item(db_session):
    lead = _lead_with_valid_email(db_session)
    item = generate_drafts(db_session, lead)
    assert item.status == ApprovalStatus.PENDING
    assert item.draft_body
    assert lead.status == LeadStatus.OUTREACH_PENDING


def test_approve_and_send_flow(db_session):
    lead = _lead_with_valid_email(db_session)
    item = generate_drafts(db_session, lead)

    approve_item(db_session, item, reviewer="tester")
    assert item.status == ApprovalStatus.APPROVED
    assert item.message.status == MessageStatus.APPROVED
    assert item.message.compliance_checked is True

    message = send_item(db_session, item)
    assert message.status == MessageStatus.SENT
    db_session.refresh(lead)
    assert lead.status == LeadStatus.CONTACTED


def test_reject_flow(db_session):
    lead = _lead_with_valid_email(db_session)
    item = generate_drafts(db_session, lead)
    reject_item(db_session, item, reviewer="tester", notes="not a fit")
    assert item.status == ApprovalStatus.REJECTED
    assert item.message.status == MessageStatus.REJECTED


def test_full_pipeline(db_session):
    lead = _make_lead(db_session)
    result = run_pipeline(db_session, lead)
    assert result["lead_id"] == lead.id
    assert "score" in result["steps"]
    assert "trace" in result["steps"]
    assert "validate" in result["steps"]
