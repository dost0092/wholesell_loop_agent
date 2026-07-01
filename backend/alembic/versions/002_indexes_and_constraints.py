"""Add missing indexes and deduplication constraints.

Revision ID: 002
Revises: 001
Create Date: 2026-07-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_leads_parcel_id", "leads", ["parcel_id"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index(
        "uq_leads_state_county_parcel",
        "leads",
        ["state", "county", "parcel_id"],
        unique=True,
        postgresql_where=sa.text("parcel_id IS NOT NULL"),
    )

    op.create_index("ix_owners_lead_id", "owners", ["lead_id"])
    op.create_index("ix_contacts_owner_id", "contacts", ["owner_id"])
    op.create_index("ix_contacts_value", "contacts", ["value"])
    op.create_index("ix_messages_lead_id", "messages", ["lead_id"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_approval_queue_lead_id", "approval_queue", ["lead_id"])
    op.create_index("ix_approval_queue_status", "approval_queue", ["status"])


def downgrade() -> None:
    op.drop_index("ix_approval_queue_status", table_name="approval_queue")
    op.drop_index("ix_approval_queue_lead_id", table_name="approval_queue")
    op.drop_index("ix_messages_status", table_name="messages")
    op.drop_index("ix_messages_lead_id", table_name="messages")
    op.drop_index("ix_contacts_value", table_name="contacts")
    op.drop_index("ix_contacts_owner_id", table_name="contacts")
    op.drop_index("ix_owners_lead_id", table_name="owners")
    op.drop_index("uq_leads_state_county_parcel", table_name="leads")
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_parcel_id", table_name="leads")
