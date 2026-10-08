"""Add manual settlement workflow, audit events, and in-app notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0003_manual_settlements"
down_revision = "0002_expenses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "settlement_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PAYMENT_CLAIMED", "CONFIRMED", "REJECTED", "CANCELLED", name="settlementstatus", native_enum=False), nullable=False),
        sa.Column("note", sa.String(240)),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_reference_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("claimed_paid_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount > 0", name="ck_settlement_positive_amount"),
    )
    op.create_index("ix_settlement_requests_status", "settlement_requests", ["status"])
    op.create_index("ix_settlement_group_status_created", "settlement_requests", ["group_id", "status", "created_at"])
    op.create_index("ix_settlement_payer_status", "settlement_requests", ["payer_id", "status"])
    op.create_index("ix_settlement_requester_created", "settlement_requests", ["requester_id", "created_at"])
    op.create_table(
        "settlement_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_request_id", sa.Integer(), sa.ForeignKey("settlement_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_settlement_events_settlement_request_id", "settlement_events", ["settlement_request_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("message", sa.String(300), nullable=False),
        sa.Column("related_entity_type", sa.String(40)),
        sa.Column("related_entity_id", sa.Integer()),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notification_user_read_created", "notifications", ["user_id", "is_read", "created_at"])


def downgrade():
    op.drop_index("ix_notification_user_read_created", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_settlement_events_settlement_request_id", table_name="settlement_events")
    op.drop_table("settlement_events")
    op.drop_index("ix_settlement_requester_created", table_name="settlement_requests")
    op.drop_index("ix_settlement_payer_status", table_name="settlement_requests")
    op.drop_index("ix_settlement_group_status_created", table_name="settlement_requests")
    op.drop_index("ix_settlement_requests_status", table_name="settlement_requests")
    op.drop_table("settlement_requests")
