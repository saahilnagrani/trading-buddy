"""Add per-account Kite API credentials

Revision ID: 006
Revises: 005
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"


def upgrade() -> None:
    op.add_column("accounts", sa.Column("kite_api_key", sa.String(100), nullable=True))
    op.add_column("accounts", sa.Column("kite_api_secret", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "kite_api_secret")
    op.drop_column("accounts", "kite_api_key")
