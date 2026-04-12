"""portfolio positions, snapshots, and trade history

Revision ID: 004
Revises: 003
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False, index=True),
        sa.Column("tradingsymbol", sa.String(100), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("product", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("average_price", sa.Numeric(12, 2)),
        sa.Column("last_price", sa.Numeric(12, 2)),
        sa.Column("pnl", sa.Numeric(14, 2)),
        sa.Column("day_change", sa.Numeric(14, 2)),
        sa.Column("day_change_pct", sa.Numeric(8, 4)),
        sa.Column("value", sa.Numeric(14, 2)),
        sa.Column("instrument_type", sa.String(10)),
        sa.Column("strike", sa.Numeric(12, 2)),
        sa.Column("expiry", sa.Date()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_pnl", sa.Numeric(14, 2)),
        sa.Column("realized_pnl", sa.Numeric(14, 2)),
        sa.Column("unrealized_pnl", sa.Numeric(14, 2)),
        sa.Column("margin_used", sa.Numeric(14, 2)),
        sa.Column("margin_available", sa.Numeric(14, 2)),
        sa.Column("total_value", sa.Numeric(14, 2)),
        sa.Column("position_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "snapshot_date", name="uq_snapshot_account_date"),
    )

    op.create_table(
        "trade_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False, index=True),
        sa.Column("kite_order_id", sa.String(50)),
        sa.Column("tradingsymbol", sa.String(100), nullable=False),
        sa.Column("exchange", sa.String(10)),
        sa.Column("transaction_type", sa.String(4)),
        sa.Column("quantity", sa.Integer()),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("trade_date", sa.DateTime(timezone=True)),
        sa.Column("order_execution_time", sa.DateTime(timezone=True)),
        sa.Column("charges", sa.Numeric(10, 2)),
        sa.Column("pnl", sa.Numeric(14, 2)),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_trade_history_trade_date", "trade_history", ["trade_date"])


def downgrade() -> None:
    op.drop_table("trade_history")
    op.drop_table("portfolio_snapshots")
    op.drop_table("positions")
