"""orders table

Revision ID: 002
Revises: 001
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("basket_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("kite_order_id", sa.String(50), nullable=True),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("tradingsymbol", sa.String(100), nullable=False),
        sa.Column("transaction_type", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("product", sa.String(10), nullable=False),
        sa.Column("variety", sa.String(10), nullable=False, server_default="regular"),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("trigger_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("filled_quantity", sa.Integer(), server_default="0"),
        sa.Column("average_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_account_id", "orders", ["account_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])


def downgrade() -> None:
    op.drop_table("orders")
