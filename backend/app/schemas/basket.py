import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BasketItemCreate(BaseModel):
    exchange: str
    tradingsymbol: str
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(..., pattern="^(MARKET|LIMIT|SL|SL-M)$")
    product: str = Field(..., pattern="^(NRML|MIS|CNC)$")
    quantity: int = Field(..., ge=1)
    price_offset: Decimal = Field(default=0)
    sort_order: int = 0


class BasketItemResponse(BaseModel):
    id: uuid.UUID
    exchange: str
    tradingsymbol: str
    transaction_type: str
    order_type: str
    product: str
    quantity: int
    price_offset: Decimal
    sort_order: int

    model_config = {"from_attributes": True}


class BasketCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    items: list[BasketItemCreate] = []


class BasketUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None


class BasketResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    items: list[BasketItemResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class BasketExecuteRequest(BaseModel):
    account_ids: list[str]
    mode: str = Field(..., pattern="^(uniform|custom)$")
    uniform_lots: int | None = Field(None, ge=1)
    custom_allocations: dict[str, int] | None = None  # {account_id: lots}
