"""risk controls and notifications

Revision ID: 005
Revises: 004
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add risk control columns to accounts
    op.add_column("accounts", sa.Column("max_order_value", sa.Numeric(14, 2), nullable=True))
    op.add_column("accounts", sa.Column("max_daily_orders", sa.Integer(), server_default="50"))
    op.add_column("accounts", sa.Column("max_open_positions", sa.Integer(), server_default="20"))
    op.add_column("accounts", sa.Column("allowed_exchanges", postgresql.ARRAY(sa.String()), server_default="{NFO,NSE}"))
    op.add_column("accounts", sa.Column("allowed_products", postgresql.ARRAY(sa.String()), server_default="{NRML,MIS,CNC}"))

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh_key", sa.Text(), nullable=False),
        sa.Column("auth_key", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("push_subscriptions")
    op.drop_table("notifications")
    op.drop_column("accounts", "allowed_products")
    op.drop_column("accounts", "allowed_exchanges")
    op.drop_column("accounts", "max_open_positions")
    op.drop_column("accounts", "max_daily_orders")
    op.drop_column("accounts", "max_order_value")
