import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderParams(BaseModel):
    exchange: str = Field(..., pattern="^(NSE|NFO|BFO|BSE|MCX|CDS|BCD)$")
    tradingsymbol: str = Field(..., max_length=100)
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(..., pattern="^(MARKET|LIMIT|SL|SL-M)$")
    product: str = Field(..., pattern="^(NRML|MIS|CNC)$")
    variety: str = Field("regular", pattern="^(regular|amo|iceberg)$")
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    iceberg_legs: int | None = Field(None, ge=2, le=10)
    iceberg_quantity: int | None = Field(None, ge=1)


class PlaceOrderRequest(BaseModel):
    account_ids: list[str]  # UUIDs or ["all"]
    mode: str = Field(..., pattern="^(uniform|custom)$")
    order: OrderParams
    uniform_quantity: int | None = Field(None, ge=1)
    custom_allocations: dict[str, int] | None = None  # {account_id: quantity}


class OrderResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str | None = None
    group_id: uuid.UUID | None
    kite_order_id: str | None
    exchange: str
    tradingsymbol: str
    transaction_type: str
    order_type: str
    product: str
    variety: str
    quantity: int
    price: Decimal | None
    trigger_price: Decimal | None
    filled_quantity: int
    average_price: Decimal | None
    status: str
    status_message: str | None
    placed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaceOrderResult(BaseModel):
    account_id: str
    account_name: str
    order_id: str | None
    kite_order_id: str | None
    status: str  # PLACED, REJECTED, ERROR
    message: str | None = None


class PlaceOrderResponse(BaseModel):
    group_id: uuid.UUID
    results: list[PlaceOrderResult]
    total: int
    placed: int
    failed: int


class ModifyOrderRequest(BaseModel):
    price: Decimal | None = None
    quantity: int | None = Field(None, ge=1)
    trigger_price: Decimal | None = None
    order_type: str | None = Field(None, pattern="^(MARKET|LIMIT|SL|SL-M)$")


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class InstrumentSearchResult(BaseModel):
    tradingsymbol: str
    exchange: str
    instrument_type: str
    name: str
    lot_size: int
    expiry: str | None = None
    strike: float | None = None
    tick_size: float
