"""Add Kite user ID to accounts

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"


def upgrade() -> None:
    op.add_column("accounts", sa.Column("kite_user_id", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "kite_user_id")
