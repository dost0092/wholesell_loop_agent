"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

lead_status = postgresql.ENUM(
    "new", "scored", "traced", "validated", "send_ready", "outreach_pending",
    "contacted", "interested", "negotiating", "under_contract", "closed", "rejected", "dnc",
    name="lead_status", create_type=False,
)
message_channel = postgresql.ENUM("email", "sms", name="message_channel", create_type=False)
message_direction = postgresql.ENUM("outbound", "inbound", name="message_direction", create_type=False)
message_status = postgresql.ENUM(
    "draft", "pending_approval", "approved", "rejected", "sent", "failed", "received",
    name="message_status", create_type=False,
)
approval_status = postgresql.ENUM("pending", "approved", "rejected", "edited", name="approval_status", create_type=False)
approval_channel = postgresql.ENUM("email", "sms", name="approval_channel", create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    lead_status.create(op.get_bind(), checkfirst=True)
    message_channel.create(op.get_bind(), checkfirst=True)
    message_direction.create(op.get_bind(), checkfirst=True)
    message_status.create(op.get_bind(), checkfirst=True)
    approval_status.create(op.get_bind(), checkfirst=True)
    approval_channel.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("county", sa.String(100), nullable=False),
        sa.Column("source_module", sa.String(200), nullable=False),
        sa.Column("parcel_id", sa.String(100)),
        sa.Column("property_address", sa.String(500), nullable=False),
        sa.Column("city", sa.String(200)),
        sa.Column("zip_code", sa.String(20)),
        sa.Column("raw_data", postgresql.JSONB()),
        sa.Column("distress_signals", postgresql.JSONB()),
        sa.Column("estimated_arv", sa.Float()),
        sa.Column("estimated_equity", sa.Float()),
        sa.Column("mortgage_balance", sa.Float()),
        sa.Column("years_owned", sa.Float()),
        sa.Column("is_vacant", sa.Boolean(), server_default="false"),
        sa.Column("deal_score", sa.Integer()),
        sa.Column("score_reasoning", sa.Text()),
        sa.Column("motivation_summary", sa.Text()),
        sa.Column("offer_strategy", sa.Text()),
        sa.Column("status", lead_status, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_leads_state", "leads", ["state"])
    op.create_index("ix_leads_county", "leads", ["county"])
    op.create_index("ix_leads_status", "leads", ["status"])

    op.create_table(
        "owners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300)),
        sa.Column("mailing_address", sa.String(500)),
        sa.Column("is_llc", sa.Boolean(), server_default="false"),
        sa.Column("entity_name", sa.String(300)),
        sa.Column("confidence_score", sa.Float(), server_default="0"),
        sa.Column("source_list", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("owners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_type", sa.String(20), nullable=False),
        sa.Column("value", sa.String(300), nullable=False),
        sa.Column("line_type", sa.String(50)),
        sa.Column("validated", sa.Boolean(), server_default="false"),
        sa.Column("validation_details", postgresql.JSONB()),
        sa.Column("confidence_score", sa.Float(), server_default="0"),
        sa.Column("source", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("channel", message_channel, nullable=False),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("subject", sa.String(500)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", message_status, server_default="draft"),
        sa.Column("compliance_checked", sa.Boolean(), server_default="false"),
        sa.Column("compliance_notes", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "dnc_list",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("value", sa.String(300), nullable=False, unique=True),
        sa.Column("contact_type", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(500), nullable=False),
        sa.Column("role", sa.String(50), server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "approval_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), unique=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", approval_channel, nullable=False),
        sa.Column("draft_subject", sa.String(500)),
        sa.Column("draft_body", sa.Text(), nullable=False),
        sa.Column("status", approval_status, server_default="pending"),
        sa.Column("reviewed_by", sa.String(320)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("approval_queue")
    op.drop_table("users")
    op.drop_table("dnc_list")
    op.drop_table("messages")
    op.drop_table("contacts")
    op.drop_table("owners")
    op.drop_table("leads")
    for enum_name in ("approval_channel", "approval_status", "message_status", "message_direction", "message_channel", "lead_status"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
