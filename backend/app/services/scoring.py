"""Phase 3 — apply the deal scorer to leads and persist the result."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agents.scorer import get_scorer
from app.db.models import Lead, LeadStatus

logger = logging.getLogger(__name__)


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "state": lead.state,
        "county": lead.county,
        "property_address": lead.property_address,
        "city": lead.city,
        "zip_code": lead.zip_code,
        "distress_signals": lead.distress_signals or [],
        "raw_data": lead.raw_data or {},
    }


def score_lead(db: Session, lead: Lead) -> Lead:
    scorer = get_scorer()
    result = scorer.score(_lead_to_dict(lead))

    lead.deal_score = result.deal_score
    lead.score_reasoning = result.score_reasoning
    lead.motivation_summary = result.motivation_summary
    lead.offer_strategy = result.offer_strategy
    if result.estimated_arv is not None:
        lead.estimated_arv = result.estimated_arv
    if result.estimated_equity is not None:
        lead.estimated_equity = result.estimated_equity

    # Only advance status forward; never regress a lead already deeper in the pipeline.
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.SCORED

    db.commit()
    db.refresh(lead)
    logger.info("Scored lead %s: %s (%s)", lead.id, result.deal_score, result.provider)
    return lead


def score_unscored(db: Session, limit: int = 100) -> dict:
    leads = (
        db.query(Lead)
        .filter(Lead.deal_score.is_(None))
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .all()
    )
    for lead in leads:
        score_lead(db, lead)
    return {"scored": len(leads)}
