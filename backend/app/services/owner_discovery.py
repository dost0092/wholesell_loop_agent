"""Phase 4 — owner discovery: entity resolution + skip trace -> owners & contacts."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.adapters.entity_lookup import get_entity_lookup, is_entity_name
from app.adapters.skip_trace import get_skip_trace_provider
from app.db.models import Contact, Lead, LeadStatus, Owner

logger = logging.getLogger(__name__)


def _owner_name_from_lead(lead: Lead) -> str:
    raw = lead.raw_data or {}
    for key in ("owner_of_record", "owner", "owner_name", "defendant"):
        val = raw.get(key)
        if val:
            return str(val).strip()
    return "Unknown Owner"


def trace_lead(db: Session, lead: Lead) -> Owner:
    owner_name = _owner_name_from_lead(lead)
    entity_provider = get_entity_lookup()
    skip_provider = get_skip_trace_provider()

    entity = entity_provider.lookup(owner_name, lead.state)

    # If the record owner is an entity, prefer tracing the resolved officer.
    trace_target = owner_name
    if entity.is_entity and entity.officers:
        trace_target = entity.officers[0].get("name") or owner_name

    contact_record = skip_provider.trace(
        owner_name=trace_target,
        property_address=lead.property_address,
        city=lead.city or "",
        state=lead.state,
    )

    sources = sorted({skip_provider.name, entity_provider.name})
    owner = Owner(
        lead_id=lead.id,
        name=owner_name,
        mailing_address=contact_record.mailing_address or lead.property_address,
        is_llc=is_entity_name(owner_name) or entity.is_entity,
        entity_name=entity.entity_name if entity.is_entity else None,
        confidence_score=0.8 if skip_provider.name != "mock" else 0.5,
        source_list=sources,
    )
    db.add(owner)
    db.flush()  # assign owner.id for contacts

    for em in contact_record.emails:
        if em.get("value"):
            db.add(
                Contact(
                    owner_id=owner.id,
                    contact_type="email",
                    value=em["value"].strip().lower(),
                    confidence_score=em.get("confidence", 0.5),
                    source=em.get("source", skip_provider.name),
                )
            )
    for ph in contact_record.phones:
        if ph.get("value"):
            db.add(
                Contact(
                    owner_id=owner.id,
                    contact_type="phone",
                    value=ph["value"].strip(),
                    line_type=ph.get("line_type", "unknown"),
                    confidence_score=ph.get("confidence", 0.5),
                    source=ph.get("source", skip_provider.name),
                )
            )

    if lead.status in (LeadStatus.NEW, LeadStatus.SCORED):
        lead.status = LeadStatus.TRACED

    db.commit()
    db.refresh(owner)
    logger.info(
        "Traced lead %s -> owner %s (%s emails, %s phones)",
        lead.id,
        owner.id,
        len(contact_record.emails),
        len(contact_record.phones),
    )
    return owner
