import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel


class PositionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str | None = None
    tradingsymbol: str
    exchange: str
    product: str
    quantity: int
    average_price: Decimal | None
    last_price: Decimal | None
    pnl: Decimal | None
    day_change: Decimal | None
    day_change_pct: Decimal | None
    value: Decimal | None
    instrument_type: str | None
    strike: Decimal | None
    expiry: date | None
    synced_at: datetime

    model_config = {"from_attributes": True}


class AccountSummary(BaseModel):
    account_id: uuid.UUID
    account_name: str
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    margin_used: float
    margin_available: float
    position_count: int


class PortfolioSummaryResponse(BaseModel):
    total_pnl: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_margin_used: float
    total_margin_available: float
    total_position_count: int
    accounts: list[AccountSummary]


class SnapshotResponse(BaseModel):
    snapshot_date: date
    total_pnl: float
    total_value: float
    margin_used: float
    position_count: int

    model_config = {"from_attributes": True}


class TradeHistoryResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str | None = None
    tradingsymbol: str
    exchange: str | None
    transaction_type: str | None
    quantity: int | None
    price: Decimal | None
    trade_date: datetime | None
    charges: Decimal | None
    pnl: Decimal | None

    model_config = {"from_attributes": True}
