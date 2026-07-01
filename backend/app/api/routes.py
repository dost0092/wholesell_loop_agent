import logging
import math
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.deps import require_api_key
from app.config import get_settings
from app.core.exceptions import AppError
from app.db.models import ApprovalQueueItem, Lead, LeadStatus
from app.db.session import get_db
from app.schemas.api import (
    ApprovalItemOut,
    FetchSourceResult,
    FetchTxRequest,
    FetchTxResponse,
    HealthResponse,
    LeadOut,
    LeadStatsResponse,
    PaginatedResponse,
    SourceInfo,
)
from app.services.lead_ingestion import ingest_raw_leads
from app.sources.registry import get_source, list_sources

logger = logging.getLogger(__name__)

router = APIRouter()
DEFAULT_TX_SOURCES = ["tx.harris.tax_sale", "tx.dallas.trw", "tx.tarrant.tax_sale"]


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
        phase=1,
        database=db_status,
    )


@router.get("/sources", response_model=list[SourceInfo])
def sources():
    return list_sources()


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


@router.post("/sources/fetch-tx", response_model=FetchTxResponse)
def fetch_tx(
    body: FetchTxRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    """Run Phase 1 TX county connectors and optionally persist to Postgres."""
    keys = body.sources or DEFAULT_TX_SOURCES
    results: list[FetchSourceResult] = []

    for key in keys:
        try:
            source = get_source(key)
        except KeyError as exc:
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county="unknown",
                    leads_fetched=0,
                    error=str(exc),
                )
            )
            continue

        try:
            raw_leads = source.fetch()
            used_fixture = any((r.raw_data or {}).get("fixture_fallback") for r in raw_leads)
            ingest_stats = None
            if body.persist:
                ingest_stats = ingest_raw_leads(db, raw_leads)

            sample = [
                {
                    "address": r.property_address,
                    "parcel_id": r.parcel_id,
                    "city": r.city,
                    "distress_signals": r.distress_signals,
                }
                for r in raw_leads[:5]
            ]
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county=source.county,
                    leads_fetched=len(raw_leads),
                    ingest=ingest_stats,
                    sample=sample,
                    used_fixture_fallback=used_fixture,
                )
            )
        except Exception as exc:
            logger.exception("Fetch failed for source %s", key)
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county=source.county,
                    leads_fetched=0,
                    error=str(exc),
                )
            )

    total_in_db = db.query(Lead).count() if body.persist else None
    return FetchTxResponse(results=results, total_leads_in_db=total_in_db)


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


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise AppError("Lead not found", status_code=404, code="not_found")
    return lead


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
