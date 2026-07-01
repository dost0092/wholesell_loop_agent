from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ApprovalStatus, LeadStatus, MessageChannel, MessageStatus

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class HealthResponse(BaseModel):
    status: str
    require_human_approval: bool
    target_states: list[str]
    tx_counties: list[str]
    fl_counties: list[str]
    phase: int = 1
    database: str = "unknown"
    version: str = "0.2.0"


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    state: str
    county: str
    source_module: str
    property_address: str
    city: str | None
    zip_code: str | None
    parcel_id: str | None
    distress_signals: list | None
    deal_score: int | None
    status: LeadStatus
    raw_data: dict | None
    created_at: datetime


class LeadStatsResponse(BaseModel):
    total: int
    by_county: dict[str, int]
    by_status: dict[str, int]
    by_signal: dict[str, int]


class ApprovalItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    channel: MessageChannel
    draft_subject: str | None
    draft_body: str
    status: ApprovalStatus
    created_at: datetime


class SourceInfo(BaseModel):
    key: str
    name: str
    state: str
    county: str
    description: str


class FetchTxRequest(BaseModel):
    sources: list[str] | None = Field(
        default=None,
        description="Source keys, e.g. tx.harris.tax_sale. Default: all TX Phase 1 sources.",
    )
    persist: bool = Field(default=True, description="Save leads to Postgres")


class FetchSourceResult(BaseModel):
    source_key: str
    county: str
    leads_fetched: int
    ingest: dict | None = None
    sample: list[dict] = Field(default_factory=list)
    used_fixture_fallback: bool = False
    error: str | None = None


class FetchTxResponse(BaseModel):
    results: list[FetchSourceResult]
    total_leads_in_db: int | None = None
