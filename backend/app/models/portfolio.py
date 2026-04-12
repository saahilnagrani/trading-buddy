import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    tradingsymbol: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    product: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    day_change: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    day_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    instrument_type: Mapped[str | None] = mapped_column(String(10))  # EQ, CE, PE, FUT
    strike: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expiry: Mapped[date | None] = mapped_column(Date)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", lazy="selectin")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (UniqueConstraint("account_id", "snapshot_date", name="uq_snapshot_account_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margin_used: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margin_available: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    position_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradeHistory(Base):
    __tablename__ = "trade_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    kite_order_id: Mapped[str | None] = mapped_column(String(50))
    tradingsymbol: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(10))
    transaction_type: Mapped[str | None] = mapped_column(String(4))
    quantity: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    trade_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order_execution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    charges: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account = relationship("Account", lazy="selectin")
