"""Swappable adapter interfaces for data sources, skip trace, email, and SMS."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class RawLead:
    state: str
    county: str
    source_module: str
    property_address: str
    city: str | None = None
    zip_code: str | None = None
    parcel_id: str | None = None
    distress_signals: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.utcnow)


class LeadSource(ABC):
    """County-specific connector. One module per county/source."""

    name: str
    state: str
    county: str

    @abstractmethod
    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        """Pull new distressed-property records since the given date."""
        ...


@dataclass
class ScoreResult:
    """Output of the deal scoring engine (Phase 3)."""

    deal_score: int  # 0-100
    score_reasoning: str
    motivation_summary: str
    offer_strategy: str
    estimated_arv: float | None = None
    estimated_equity: float | None = None
    provider: str = "heuristic"


class DealScorer(ABC):
    """Ranks a distressed-property lead by deal potential and seller motivation."""

    name: str = "scorer"

    @abstractmethod
    def score(self, lead: dict) -> ScoreResult:
        ...


@dataclass
class ContactRecord:
    name: str | None = None
    mailing_address: str | None = None
    emails: list[dict] = field(default_factory=list)  # {value, source, confidence}
    phones: list[dict] = field(default_factory=list)  # {value, line_type, source, confidence}
    provider: str = ""
    raw_response: dict = field(default_factory=dict)


class SkipTraceProvider(ABC):
    name: str = "skip_trace"

    @abstractmethod
    def trace(self, owner_name: str, property_address: str, city: str, state: str) -> ContactRecord:
        ...


@dataclass
class EntityRecord:
    """Business-entity lookup result (Phase 4 — LLC / corp registries)."""

    is_entity: bool = False
    entity_name: str | None = None
    officers: list[dict] = field(default_factory=list)  # {name, role}
    registered_agent: str | None = None
    status: str | None = None
    provider: str = ""
    raw_response: dict = field(default_factory=dict)


class EntityLookupProvider(ABC):
    """Resolve an LLC / corporation to its officers and registered agent."""

    name: str = "entity_lookup"

    @abstractmethod
    def lookup(self, entity_name: str, state: str) -> EntityRecord:
        ...


@dataclass
class ContactValidationResult:
    """Validation outcome for a single email or phone (Phase 5)."""

    is_valid: bool
    line_type: str | None = None  # mobile | landline | voip | unknown (phones)
    confidence: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class OutboundEmail:
    to_email: str
    subject: str
    body_plain: str
    lead_id: int | None = None
    message_id: int | None = None


class EmailSender(ABC):
    """
    SMTP-based email sender. Default implementation uses user's own SMTP (Gmail App Password).
    Plain-text first — no HTML, images, or tracking pixels (deliverability).
    """

    @abstractmethod
    def send(self, email: OutboundEmail) -> bool:
        ...


@dataclass
class OutboundSms:
    to_phone: str
    body: str
    lead_id: int | None = None
    message_id: int | None = None


class SmsSender(ABC):
    @abstractmethod
    def send(self, sms: OutboundSms) -> bool:
        ...
