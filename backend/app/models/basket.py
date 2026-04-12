import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["BasketItem"]] = relationship(
        back_populates="basket", cascade="all, delete-orphan", order_by="BasketItem.sort_order"
    )


class BasketItem(Base):
    __tablename__ = "basket_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("baskets.id", ondelete="CASCADE"), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    tradingsymbol: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)
    product: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # Per-lot quantity
    price_offset: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)  # Offset from LTP for limit orders
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    basket: Mapped["Basket"] = relationship(back_populates="items")
