"""Add email_logs and oauth_tokens tables for Gmail send pipeline.

Revision ID: 003
Revises: 002
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

delivery_status = sa.Enum(
    "scheduled",
    "sending",
    "sent",
    "failed",
    "skipped",
    "retry_pending",
    "bounced",
    name="delivery_status",
)


def upgrade() -> None:
    delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="SET NULL")),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_time", sa.DateTime(timezone=True)),
        sa.Column("delivery_status", delivery_status, nullable=False, server_default="scheduled"),
        sa.Column("error_message", sa.Text()),
        sa.Column("skip_reason", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmail_message_id", sa.String(200)),
        sa.Column("send_duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_logs_lead_id", "email_logs", ["lead_id"])
    op.create_index("ix_email_logs_message_id", "email_logs", ["message_id"])
    op.create_index("ix_email_logs_recipient_email", "email_logs", ["recipient_email"])
    op.create_index("ix_email_logs_body_hash", "email_logs", ["body_hash"])
    op.create_index("ix_email_logs_scheduled_time", "email_logs", ["scheduled_time"])
    op.create_index("ix_email_logs_delivery_status", "email_logs", ["delivery_status"])

    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False, unique=True),
        sa.Column("access_token", sa.Text()),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expiry", sa.DateTime(timezone=True)),
        sa.Column("scopes", sa.String(500)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_oauth_tokens_provider", "oauth_tokens", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_oauth_tokens_provider", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
    op.drop_index("ix_email_logs_delivery_status", table_name="email_logs")
    op.drop_index("ix_email_logs_scheduled_time", table_name="email_logs")
    op.drop_index("ix_email_logs_body_hash", table_name="email_logs")
    op.drop_index("ix_email_logs_recipient_email", table_name="email_logs")
    op.drop_index("ix_email_logs_message_id", table_name="email_logs")
    op.drop_index("ix_email_logs_lead_id", table_name="email_logs")
    op.drop_table("email_logs")
    delivery_status.drop(op.get_bind(), checkfirst=True)
