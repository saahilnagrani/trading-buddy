import uuid
from datetime import datetime

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_lots: Mapped[int] = mapped_column(Integer, default=1)
    max_order_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    max_daily_orders: Mapped[int] = mapped_column(Integer, default=50)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=20)
    allowed_exchanges: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=["NFO", "NSE"])
    allowed_products: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=["NRML", "MIS", "CNC"])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tokens: Mapped[list["AccountToken"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class AccountToken(Base):
    __tablename__ = "account_tokens"
    __table_args__ = (UniqueConstraint("account_id", "token_date", name="uq_account_token_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    access_token: Mapped[str] = mapped_column(String(512), nullable=False)  # Encrypted
    token_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    login_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="tokens")
