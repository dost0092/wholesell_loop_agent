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
class ContactRecord:
    name: str | None = None
    mailing_address: str | None = None
    emails: list[dict] = field(default_factory=list)  # {value, source, confidence}
    phones: list[dict] = field(default_factory=list)  # {value, line_type, source, confidence}
    provider: str = ""
    raw_response: dict = field(default_factory=dict)


class SkipTraceProvider(ABC):
    @abstractmethod
    def trace(self, owner_name: str, property_address: str, city: str, state: str) -> ContactRecord:
        ...


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
