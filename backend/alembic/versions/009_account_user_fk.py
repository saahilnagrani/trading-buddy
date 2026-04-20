"""Add user_id FK to accounts for per-user isolation

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_column("accounts", "user_id")
