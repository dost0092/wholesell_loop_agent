"""End-to-end lead pipeline: score -> trace -> validate -> draft outreach.

Each stage is independently callable via the API; this orchestrator runs them in
order for a single lead and reports what happened at each step.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models import Lead
from app.services.contact_validation import validate_lead_contacts
from app.services.owner_discovery import trace_lead
from app.services.scoring import score_lead

logger = logging.getLogger(__name__)


def run_pipeline(db: Session, lead: Lead, draft: bool = True) -> dict:
    steps: dict = {}

    score_lead(db, lead)
    steps["score"] = {"deal_score": lead.deal_score}

    owner = trace_lead(db, lead)
    steps["trace"] = {"owner_id": owner.id, "contacts": len(owner.contacts)}

    validation = validate_lead_contacts(db, lead)
    steps["validate"] = validation

    if draft:
        # Import lazily to avoid a circular import at module load.
        from app.services.outreach import generate_drafts

        try:
            item = generate_drafts(db, lead)
            steps["draft"] = {"approval_item_id": item.id, "status": item.status.value}
        except AppError as exc:
            steps["draft"] = {"skipped": exc.message}

    db.refresh(lead)
    return {"lead_id": lead.id, "status": lead.status.value, "steps": steps}
