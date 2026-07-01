import logging
import math
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.deps import require_api_key
from app.config import get_settings
from app.core.exceptions import AppError
from app.db.models import ApprovalQueueItem, ApprovalStatus, DncEntry, Lead, LeadStatus
from app.db.session import get_db
from app.schemas.api import (
    ApprovalDecisionRequest,
    ApprovalItemOut,
    DncEntryRequest,
    FetchFlRequest,
    FetchSourcesRequest,
    FetchSourcesResponse,
    FetchTxRequest,
    HealthResponse,
    LeadDetailOut,
    LeadOut,
    LeadStatsResponse,
    MessageOut,
    PaginatedResponse,
    PipelineResponse,
    SourceInfo,
)
from app.services import outreach as outreach_service
from app.services.contact_validation import validate_lead_contacts
from app.services.owner_discovery import trace_lead
from app.services.pipeline import run_pipeline
from app.services.scoring import score_lead
from app.services.source_fetch import run_source_fetch
from app.sources.registry import (
    DEFAULT_ALL_SOURCES,
    DEFAULT_FL_SOURCES,
    DEFAULT_TX_SOURCES,
    list_sources,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    db_status = "ok"
    try:
        db.execute(func.now())
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        db_status = "unavailable"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        require_human_approval=settings.require_human_approval,
        target_states=settings.target_state_list,
        tx_counties=settings.tx_county_list,
        fl_counties=settings.fl_county_list,
        phase=5,
        database=db_status,
    )


@router.get("/sources", response_model=list[SourceInfo])
def sources(state: str | None = None):
    return list_sources(state=state)


@router.get("/stats/leads", response_model=LeadStatsResponse)
def lead_stats(db: Session = Depends(get_db), _key: str = Depends(require_api_key)):
    total = db.query(Lead).count()
    by_county = dict(db.query(Lead.county, func.count()).group_by(Lead.county).all())
    by_status = dict(
        db.query(Lead.status, func.count()).group_by(Lead.status).all()
    )

    signal_counter: Counter[str] = Counter()
    for (signals,) in db.query(Lead.distress_signals).all():
        if signals:
            signal_counter.update(signals)

    return LeadStatsResponse(
        total=total,
        by_county=by_county,
        by_status={str(k): v for k, v in by_status.items()},
        by_signal=dict(signal_counter),
    )


def _fetch_response(
    keys: list[str],
    body: FetchSourcesRequest,
    db: Session,
) -> FetchSourcesResponse:
    results = run_source_fetch(keys, persist=body.persist, db=db)
    total_in_db = db.query(Lead).count() if body.persist else None
    return FetchSourcesResponse(results=results, total_leads_in_db=total_in_db)


@router.post("/sources/fetch-tx", response_model=FetchSourcesResponse)
def fetch_tx(
    body: FetchTxRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Run Phase 1 TX county connectors and optionally persist."""
    keys = body.sources or DEFAULT_TX_SOURCES
    return _fetch_response(keys, body, db)


@router.post("/sources/fetch-fl", response_model=FetchSourcesResponse)
def fetch_fl(
    body: FetchFlRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Run Phase 2 FL county connectors and optionally persist."""
    keys = body.sources or DEFAULT_FL_SOURCES
    return _fetch_response(keys, body, db)


@router.post("/sources/fetch-all", response_model=FetchSourcesResponse)
def fetch_all(
    body: FetchSourcesRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Run all TX + FL county connectors."""
    keys = body.sources or DEFAULT_ALL_SOURCES
    return _fetch_response(keys, body, db)


@router.get("/leads", response_model=PaginatedResponse[LeadOut])
def list_leads(
    state: str | None = None,
    county: str | None = None,
    status: LeadStatus | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    q = db.query(Lead)
    if state:
        q = q.filter(Lead.state == state.upper())
    if county:
        q = q.filter(Lead.county.ilike(county))
    if status:
        q = q.filter(Lead.status == status)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Lead.property_address.ilike(term),
                Lead.parcel_id.ilike(term),
                Lead.city.ilike(term),
            )
        )

    total = q.count()
    items = (
        q.order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, math.ceil(total / page_size)) if total else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/leads/{lead_id}", response_model=LeadDetailOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    return _get_lead_or_404(db, lead_id)


def _get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise AppError("Lead not found", status_code=404, code="not_found")
    return lead


# ---------------------------------------------------------------------------
# Phase 3-5 pipeline endpoints
# ---------------------------------------------------------------------------


@router.post("/leads/{lead_id}/score", response_model=LeadDetailOut)
def score_lead_endpoint(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Phase 3 — AI deal scoring for a single lead."""
    lead = _get_lead_or_404(db, lead_id)
    return score_lead(db, lead)


@router.post("/leads/{lead_id}/trace", response_model=LeadDetailOut)
def trace_lead_endpoint(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Phase 4 — owner discovery (entity resolution + skip trace)."""
    lead = _get_lead_or_404(db, lead_id)
    trace_lead(db, lead)
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/validate", response_model=LeadDetailOut)
def validate_lead_endpoint(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Phase 5 — validate the lead's contacts (email MX, phone type, DNC scrub)."""
    lead = _get_lead_or_404(db, lead_id)
    validate_lead_contacts(db, lead)
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/draft", response_model=ApprovalItemOut)
def draft_lead_endpoint(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Phase 5 — generate an outreach email draft into the approval queue."""
    lead = _get_lead_or_404(db, lead_id)
    return outreach_service.generate_drafts(db, lead)


@router.post("/leads/{lead_id}/pipeline", response_model=PipelineResponse)
def run_pipeline_endpoint(
    lead_id: int,
    draft: bool = Query(default=True),
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Run the full pipeline for a lead: score -> trace -> validate -> draft."""
    lead = _get_lead_or_404(db, lead_id)
    return run_pipeline(db, lead, draft=draft)


# ---------------------------------------------------------------------------
# Approval queue actions (human-in-the-loop)
# ---------------------------------------------------------------------------


def _get_item_or_404(db: Session, item_id: int) -> ApprovalQueueItem:
    item = db.query(ApprovalQueueItem).filter(ApprovalQueueItem.id == item_id).first()
    if not item:
        raise AppError("Approval item not found", status_code=404, code="not_found")
    return item


@router.post("/approval-queue/{item_id}/approve", response_model=MessageOut)
def approve_endpoint(
    item_id: int,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    item = _get_item_or_404(db, item_id)
    outreach_service.approve_item(
        db, item, reviewer=body.reviewer, edited_subject=body.subject, edited_body=body.body
    )
    if body.send_now:
        return outreach_service.send_item(db, item)
    return item.message


@router.post("/approval-queue/{item_id}/reject", response_model=ApprovalItemOut)
def reject_endpoint(
    item_id: int,
    body: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    item = _get_item_or_404(db, item_id)
    return outreach_service.reject_item(db, item, reviewer=body.reviewer, notes=body.notes)


@router.post("/approval-queue/{item_id}/send", response_model=MessageOut)
def send_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Send an already-approved message (compliance gate enforced)."""
    item = _get_item_or_404(db, item_id)
    if item.status not in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED):
        raise AppError("Item must be approved before sending", status_code=422, code="not_approved")
    return outreach_service.send_item(db, item)


# ---------------------------------------------------------------------------
# Do Not Contact list management
# ---------------------------------------------------------------------------


@router.post("/dnc")
def add_dnc(
    body: DncEntryRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    value = body.value.strip().lower()
    existing = db.query(DncEntry).filter(DncEntry.value == value).first()
    if existing:
        return {"value": value, "status": "already_present"}
    db.add(DncEntry(value=value, contact_type=body.contact_type, reason=body.reason))
    db.commit()
    return {"value": value, "status": "added"}


@router.get("/dnc")
def list_dnc(
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    entries = db.query(DncEntry).order_by(DncEntry.added_at.desc()).limit(500).all()
    return [
        {"value": e.value, "contact_type": e.contact_type, "reason": e.reason}
        for e in entries
    ]


@router.get("/approval-queue", response_model=PaginatedResponse[ApprovalItemOut])
def list_approval_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    q = db.query(ApprovalQueueItem)
    total = q.count()
    items = (
        q.order_by(ApprovalQueueItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
