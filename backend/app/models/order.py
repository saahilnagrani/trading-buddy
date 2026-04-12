import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    basket_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    # Kite order details
    kite_order_id: Mapped[str | None] = mapped_column(String(50))
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    tradingsymbol: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY, SELL
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)  # MARKET, LIMIT, SL, SL-M
    product: Mapped[str] = mapped_column(String(10), nullable=False)  # NRML, MIS, CNC
    variety: Mapped[str] = mapped_column(String(10), nullable=False, default="regular")

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    trigger_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Fill details
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0)
    average_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    status_message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    account = relationship("Account", lazy="selectin")
