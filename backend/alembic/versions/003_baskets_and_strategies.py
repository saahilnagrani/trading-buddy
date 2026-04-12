"""baskets and strategies

Revision ID: 003
Revises: 002
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "baskets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "basket_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("basket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("baskets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("tradingsymbol", sa.String(100), nullable=False),
        sa.Column("transaction_type", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("product", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_offset", sa.Numeric(12, 2), server_default="0"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("underlying", sa.String(50), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="DRAFT"),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partial_fill_timeout_secs", sa.Integer(), server_default="60"),
        sa.Column("auto_cancel_unfilled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("square_off_on_partial", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "strategy_legs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leg_number", sa.Integer(), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("tradingsymbol", sa.String(100), nullable=True),
        sa.Column("instrument_type", sa.String(4), nullable=True),
        sa.Column("strike", sa.Numeric(12, 2), nullable=True),
        sa.Column("transaction_type", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("order_type", sa.String(10), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("fill_quantity", sa.Integer(), server_default="0"),
        sa.Column("fill_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("strategy_legs")
    op.drop_table("strategies")
    op.drop_table("basket_items")
    op.drop_table("baskets")
