"""Persist RawLead records into the leads table with deduplication."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.adapters.interfaces import RawLead
from app.db.models import Lead, LeadStatus

logger = logging.getLogger(__name__)


def _merge_signals(existing: list | None, incoming: list | None) -> list[str]:
    return sorted(set((existing or []) + (incoming or [])))


def ingest_raw_leads(db: Session, raw_leads: list[RawLead]) -> dict:
    created = 0
    updated = 0
    skipped = 0

    for raw in raw_leads:
        if not raw.property_address or not raw.property_address.strip():
            skipped += 1
            continue

        query = db.query(Lead).filter(
            Lead.state == raw.state,
            Lead.county == raw.county,
        )
        if raw.parcel_id:
            existing = query.filter(Lead.parcel_id == raw.parcel_id).first()
        else:
            existing = query.filter(Lead.property_address == raw.property_address).first()

        if existing:
            existing.distress_signals = _merge_signals(
                existing.distress_signals, raw.distress_signals
            )
            existing.raw_data = {**(existing.raw_data or {}), **(raw.raw_data or {})}
            existing.source_module = raw.source_module
            if raw.city:
                existing.city = raw.city
            if raw.zip_code:
                existing.zip_code = raw.zip_code
            updated += 1
            continue

        lead = Lead(
            state=raw.state,
            county=raw.county,
            source_module=raw.source_module,
            parcel_id=raw.parcel_id,
            property_address=raw.property_address,
            city=raw.city,
            zip_code=raw.zip_code,
            raw_data=raw.raw_data,
            distress_signals=raw.distress_signals or [],
            status=LeadStatus.NEW,
        )
        db.add(lead)
        created += 1

    db.commit()
    logger.info(
        "Ingested batch: created=%s updated=%s skipped=%s total=%s",
        created,
        updated,
        skipped,
        len(raw_leads),
    )
    return {"created": created, "updated": updated, "skipped": skipped, "total_in_batch": len(raw_leads)}
