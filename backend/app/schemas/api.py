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
    phase: int = 5
    database: str = "unknown"
    version: str = "0.5.0"


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


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_type: str
    value: str
    line_type: str | None
    validated: bool
    confidence_score: float
    source: str | None
    validation_details: dict | None


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    mailing_address: str | None
    is_llc: bool
    entity_name: str | None
    confidence_score: float
    source_list: list | None
    contacts: list[ContactOut] = Field(default_factory=list)


class LeadDetailOut(LeadOut):
    score_reasoning: str | None = None
    motivation_summary: str | None = None
    offer_strategy: str | None = None
    estimated_arv: float | None = None
    estimated_equity: float | None = None
    owners: list[OwnerOut] = Field(default_factory=list)


class PipelineResponse(BaseModel):
    lead_id: int
    status: str
    steps: dict


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    contact_id: int | None
    channel: MessageChannel
    subject: str | None
    body: str
    status: MessageStatus
    sent_at: datetime | None
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    reviewer: str = Field(default="operator", description="Who reviewed the draft")
    subject: str | None = Field(default=None, description="Edited subject (optional)")
    body: str | None = Field(default=None, description="Edited body (optional)")
    notes: str | None = None
    send_now: bool = Field(default=False, description="Send immediately after approving")


class DncEntryRequest(BaseModel):
    value: str
    contact_type: str = Field(default="email", description="email | phone")
    reason: str | None = None


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


class FetchSourceResult(BaseModel):
    source_key: str
    county: str
    leads_fetched: int
    ingest: dict | None = None
    sample: list[dict] = Field(default_factory=list)
    used_fixture_fallback: bool = False
    error: str | None = None


class FetchSourcesRequest(BaseModel):
    sources: list[str] | None = Field(
        default=None,
        description="Source keys. Default depends on endpoint.",
    )
    persist: bool = Field(default=True, description="Save leads to database")


class FetchTxRequest(FetchSourcesRequest):
    sources: list[str] | None = Field(
        default=None,
        description="TX source keys, e.g. tx.harris.tax_sale. Default: all TX sources.",
    )


class FetchFlRequest(FetchSourcesRequest):
    sources: list[str] | None = Field(
        default=None,
        description="FL source keys, e.g. fl.miami_dade.delinquent. Default: all FL sources.",
    )


class FetchSourcesResponse(BaseModel):
    results: list[FetchSourceResult]
    total_leads_in_db: int | None = None


FetchTxResponse = FetchSourcesResponse


class EmailStatsResponse(BaseModel):
    total_scheduled: int
    total_sent: int
    total_failed: int
    total_skipped: int
    total_retry_pending: int
    next_scheduled_email: datetime | None
    average_send_duration_ms: float | None
    retry_total: int
    retry_average: float
    email_provider: str
    scheduler_enabled: bool
