"""Add expenses and participant allocations."""

import sqlalchemy as sa
from alembic import op

revision = "0002_expenses"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "paid_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "split_type",
            sa.Enum("EQUAL", "EXACT", "PERCENTAGE", "SHARES", name="splittype", native_enum=False),
            nullable=False,
        ),
        sa.Column("expense_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("total_amount > 0", name="ck_expense_positive_total"),
    )
    op.create_index("ix_expenses_group_id", "expenses", ["group_id"])
    op.create_index("ix_expenses_paid_by_user_id", "expenses", ["paid_by_user_id"])
    op.create_table(
        "expense_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "expense_id",
            sa.Integer(),
            sa.ForeignKey("expenses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("amount_owed", sa.Numeric(12, 2), nullable=False),
        sa.Column("percentage", sa.Numeric(9, 4), nullable=True),
        sa.Column("shares", sa.Numeric(12, 4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("expense_id", "user_id", name="uq_expense_participant"),
        sa.CheckConstraint("amount_owed >= 0", name="ck_expense_participant_nonnegative_share"),
    )
    op.create_index("ix_expense_participants_expense_id", "expense_participants", ["expense_id"])
    op.create_index("ix_expense_participants_user_id", "expense_participants", ["user_id"])


def downgrade():
    op.drop_index("ix_expense_participants_user_id", table_name="expense_participants")
    op.drop_index("ix_expense_participants_expense_id", table_name="expense_participants")
    op.drop_table("expense_participants")
    op.drop_index("ix_expenses_paid_by_user_id", table_name="expenses")
    op.drop_index("ix_expenses_group_id", table_name="expenses")
    op.drop_table("expenses")
