"""Lead ingestion service tests."""

from app.adapters.interfaces import RawLead
from app.db.models import Lead
from app.services.lead_ingestion import ingest_raw_leads


def test_ingest_creates_new_lead(db_session, sample_raw_lead):
    stats = ingest_raw_leads(db_session, [sample_raw_lead])
    assert stats["created"] == 1
    assert stats["updated"] == 0
    lead = db_session.query(Lead).one()
    assert lead.parcel_id == "TEST123"
    assert "tax_delinquent" in lead.distress_signals


def test_ingest_updates_existing_lead(db_session, sample_raw_lead):
    ingest_raw_leads(db_session, [sample_raw_lead])

    updated = RawLead(
        state="TX",
        county="Harris",
        source_module="tx.harris.tax_sale",
        property_address="123 Main St HOUSTON TX 77002",
        parcel_id="TEST123",
        distress_signals=["tax_sale_scheduled"],
        raw_data={"fixture_fallback": True},
    )
    stats = ingest_raw_leads(db_session, [updated])
    assert stats["created"] == 0
    assert stats["updated"] == 1

    lead = db_session.query(Lead).one()
    assert set(lead.distress_signals) == {"tax_delinquent", "tax_sale_scheduled"}
    assert lead.raw_data.get("fixture_fallback") is True


def test_ingest_skips_empty_address(db_session):
    bad = RawLead(
        state="TX",
        county="Dallas",
        source_module="tx.dallas.trw",
        property_address="   ",
        parcel_id="X",
    )
    stats = ingest_raw_leads(db_session, [bad])
    assert stats["skipped"] == 1
    assert db_session.query(Lead).count() == 0
