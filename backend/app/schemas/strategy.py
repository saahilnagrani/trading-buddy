import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, Field


class StrategyLegCreate(BaseModel):
    leg_number: int
    exchange: str = "NFO"
    tradingsymbol: str | None = None
    instrument_type: str | None = Field(None, pattern="^(CE|PE|FUT)$")
    strike: Decimal | None = None
    transaction_type: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., ge=1)
    order_type: str = Field("LIMIT", pattern="^(MARKET|LIMIT|SL|SL-M)$")
    price: Decimal | None = None
    sort_order: int = 0


class StrategyLegResponse(BaseModel):
    id: uuid.UUID
    leg_number: int
    exchange: str
    tradingsymbol: str | None
    instrument_type: str | None
    strike: Decimal | None
    transaction_type: str
    quantity: int
    order_type: str
    price: Decimal | None
    status: str
    fill_quantity: int
    fill_price: Decimal | None
    order_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    name: str = Field(..., max_length=100)
    strategy_type: str  # SPREAD, STRANGLE, STRADDLE, IRON_CONDOR, COVERED_CALL, CUSTOM
    underlying: str = Field(..., max_length=50)
    expiry_date: date | None = None
    partial_fill_timeout_secs: int = Field(60, ge=10, le=300)
    auto_cancel_unfilled: bool = True
    square_off_on_partial: bool = True
    legs: list[StrategyLegCreate]


class StrategyResponse(BaseModel):
    id: uuid.UUID
    name: str
    strategy_type: str
    underlying: str
    expiry_date: date | None
    status: str
    group_id: uuid.UUID | None
    partial_fill_timeout_secs: int
    auto_cancel_unfilled: bool
    square_off_on_partial: bool
    legs: list[StrategyLegResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyExecuteRequest(BaseModel):
    account_ids: list[str]
    mode: str = Field(..., pattern="^(uniform|custom)$")
    uniform_lots: int | None = Field(None, ge=1)
    custom_allocations: dict[str, int] | None = None


class PayoffPoint(BaseModel):
    underlying_price: float
    pnl: float


class PayoffResponse(BaseModel):
    points: list[PayoffPoint]
    max_profit: float | None
    max_loss: float | None
    breakevens: list[float]


# Strategy templates
STRATEGY_TEMPLATES = {
    "BULL_CALL_SPREAD": {
        "name": "Bull Call Spread",
        "type": "SPREAD",
        "legs": [
            {"leg_number": 1, "instrument_type": "CE", "transaction_type": "BUY", "strike_offset": 0, "description": "Buy ATM Call"},
            {"leg_number": 2, "instrument_type": "CE", "transaction_type": "SELL", "strike_offset": 200, "description": "Sell OTM Call"},
        ],
    },
    "BEAR_PUT_SPREAD": {
        "name": "Bear Put Spread",
        "type": "SPREAD",
        "legs": [
            {"leg_number": 1, "instrument_type": "PE", "transaction_type": "BUY", "strike_offset": 0, "description": "Buy ATM Put"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "SELL", "strike_offset": -200, "description": "Sell OTM Put"},
        ],
    },
    "LONG_STRADDLE": {
        "name": "Long Straddle",
        "type": "STRADDLE",
        "legs": [
            {"leg_number": 1, "instrument_type": "CE", "transaction_type": "BUY", "strike_offset": 0, "description": "Buy ATM Call"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "BUY", "strike_offset": 0, "description": "Buy ATM Put"},
        ],
    },
    "SHORT_STRADDLE": {
        "name": "Short Straddle",
        "type": "STRADDLE",
        "legs": [
            {"leg_number": 1, "instrument_type": "CE", "transaction_type": "SELL", "strike_offset": 0, "description": "Sell ATM Call"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "SELL", "strike_offset": 0, "description": "Sell ATM Put"},
        ],
    },
    "LONG_STRANGLE": {
        "name": "Long Strangle",
        "type": "STRANGLE",
        "legs": [
            {"leg_number": 1, "instrument_type": "CE", "transaction_type": "BUY", "strike_offset": 200, "description": "Buy OTM Call"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "BUY", "strike_offset": -200, "description": "Buy OTM Put"},
        ],
    },
    "SHORT_STRANGLE": {
        "name": "Short Strangle",
        "type": "STRANGLE",
        "legs": [
            {"leg_number": 1, "instrument_type": "CE", "transaction_type": "SELL", "strike_offset": 200, "description": "Sell OTM Call"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "SELL", "strike_offset": -200, "description": "Sell OTM Put"},
        ],
    },
    "IRON_CONDOR": {
        "name": "Iron Condor",
        "type": "IRON_CONDOR",
        "legs": [
            {"leg_number": 1, "instrument_type": "PE", "transaction_type": "BUY", "strike_offset": -400, "description": "Buy Far OTM Put (protection)"},
            {"leg_number": 2, "instrument_type": "PE", "transaction_type": "SELL", "strike_offset": -200, "description": "Sell OTM Put"},
            {"leg_number": 3, "instrument_type": "CE", "transaction_type": "SELL", "strike_offset": 200, "description": "Sell OTM Call"},
            {"leg_number": 4, "instrument_type": "CE", "transaction_type": "BUY", "strike_offset": 400, "description": "Buy Far OTM Call (protection)"},
        ],
    },
    "COVERED_CALL": {
        "name": "Covered Call",
        "type": "COVERED_CALL",
        "legs": [
            {"leg_number": 1, "instrument_type": "FUT", "transaction_type": "BUY", "strike_offset": 0, "description": "Buy Futures"},
            {"leg_number": 2, "instrument_type": "CE", "transaction_type": "SELL", "strike_offset": 200, "description": "Sell OTM Call"},
        ],
    },
}
