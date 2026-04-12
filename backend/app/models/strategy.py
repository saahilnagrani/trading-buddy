import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SPREAD, STRANGLE, STRADDLE, IRON_CONDOR, COVERED_CALL, CUSTOM
    underlying: Mapped[str] = mapped_column(String(50), nullable=False)  # NIFTY, BANKNIFTY, etc.
    expiry_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT, ACTIVE, PARTIALLY_FILLED, FILLED, CLOSED, CANCELLED
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # Links to order group

    # Partial fill settings
    partial_fill_timeout_secs: Mapped[int] = mapped_column(Integer, default=60)
    auto_cancel_unfilled: Mapped[bool] = mapped_column(Boolean, default=True)
    square_off_on_partial: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    legs: Mapped[list["StrategyLeg"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan", order_by="StrategyLeg.leg_number"
    )


class StrategyLeg(Base):
    __tablename__ = "strategy_legs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    leg_number: Mapped[int] = mapped_column(Integer, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    tradingsymbol: Mapped[str | None] = mapped_column(String(100))  # Can be null if dynamically computed
    instrument_type: Mapped[str | None] = mapped_column(String(4))  # CE, PE, FUT
    strike: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    transaction_type: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY, SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, PLACED, COMPLETE, CANCELLED
    fill_quantity: Mapped[int] = mapped_column(Integer, default=0)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    strategy: Mapped["Strategy"] = relationship(back_populates="legs")
