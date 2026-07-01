import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(str, enum.Enum):
    NEW = "new"
    SCORED = "scored"
    TRACED = "traced"
    VALIDATED = "validated"
    SEND_READY = "send_ready"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NEGOTIATING = "negotiating"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    REJECTED = "rejected"
    DNC = "dnc"


class MessageChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class MessageDirection(str, enum.Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class MessageStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FAILED = "failed"
    RECEIVED = "received"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    county: Mapped[str] = mapped_column(String(100), index=True)
    source_module: Mapped[str] = mapped_column(String(200))
    parcel_id: Mapped[str | None] = mapped_column(String(100), index=True)
    property_address: Mapped[str] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(200))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    distress_signals: Mapped[list | None] = mapped_column(JSONB, default=list)
    estimated_arv: Mapped[float | None] = mapped_column(Float)
    estimated_equity: Mapped[float | None] = mapped_column(Float)
    mortgage_balance: Mapped[float | None] = mapped_column(Float)
    years_owned: Mapped[float | None] = mapped_column(Float)
    is_vacant: Mapped[bool] = mapped_column(Boolean, default=False)
    deal_score: Mapped[int | None] = mapped_column(Integer)
    score_reasoning: Mapped[str | None] = mapped_column(Text)
    motivation_summary: Mapped[str | None] = mapped_column(Text)
    offer_strategy: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"), default=LeadStatus.NEW, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owners: Mapped[list["Owner"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    approval_items: Mapped[list["ApprovalQueueItem"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column(String(300))
    mailing_address: Mapped[str | None] = mapped_column(String(500))
    is_llc: Mapped[bool] = mapped_column(Boolean, default=False)
    entity_name: Mapped[str | None] = mapped_column(String(300))
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_list: Mapped[list | None] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="owners")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id", ondelete="CASCADE"), index=True)
    contact_type: Mapped[str] = mapped_column(String(20))  # email | phone
    value: Mapped[str] = mapped_column(String(300), index=True)
    line_type: Mapped[str | None] = mapped_column(String(50))  # mobile | landline | unknown
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_details: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["Owner"] = relationship(back_populates="contacts")
    messages: Mapped[list["Message"]] = relationship(back_populates="contact")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"))
    channel: Mapped[MessageChannel] = mapped_column(Enum(MessageChannel, name="message_channel"))
    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection, name="message_direction"))
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status"), default=MessageStatus.DRAFT, index=True
    )
    compliance_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_notes: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="messages")
    contact: Mapped["Contact | None"] = relationship(back_populates="messages")
    approval_item: Mapped["ApprovalQueueItem | None"] = relationship(
        back_populates="message", uselist=False
    )


class DncEntry(Base):
    __tablename__ = "dnc_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    contact_type: Mapped[str] = mapped_column(String(20))  # email | phone
    reason: Mapped[str | None] = mapped_column(String(500))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(50), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeliveryStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY_PENDING = "retry_pending"
    BOUNCED = "bounced"


class EmailLog(Base):
    """Persistent log of every email send attempt — survives restarts."""

    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(500))
    body_hash: Mapped[str] = mapped_column(String(64), index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sent_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status"),
        default=DeliveryStatus.SCHEDULED,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    skip_reason: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    gmail_message_id: Mapped[str | None] = mapped_column(String(200))
    send_duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship()
    message: Mapped["Message | None"] = relationship()


class OAuthToken(Base):
    """Persisted OAuth tokens for Gmail API — access token refreshed automatically."""

    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ApprovalQueueItem(Base):
    __tablename__ = "approval_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), unique=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    channel: Mapped[MessageChannel] = mapped_column(Enum(MessageChannel, name="approval_channel"))
    draft_subject: Mapped[str | None] = mapped_column(String(500))
    draft_body: Mapped[str] = mapped_column(Text)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"), default=ApprovalStatus.PENDING, index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(320))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="approval_items")
    message: Mapped["Message"] = relationship(back_populates="approval_item")
