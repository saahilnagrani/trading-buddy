import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str = Field(..., max_length=100)
    owner_name: str | None = Field(None, max_length=100)
    kite_api_key: str | None = Field(None, max_length=100)
    kite_api_secret: str | None = Field(None, max_length=200)
    kite_user_id: str | None = Field(None, max_length=20)
    max_lots: int = Field(1, ge=1)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    owner_name: str | None = Field(None, max_length=100)
    kite_api_key: str | None = Field(None, max_length=100)
    kite_api_secret: str | None = Field(None, max_length=200)
    kite_user_id: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    max_lots: int | None = Field(None, ge=1)
    max_order_value: float | None = None
    max_daily_orders: int | None = Field(None, ge=1)
    max_open_positions: int | None = Field(None, ge=1)
    allowed_exchanges: list[str] | None = None
    allowed_products: list[str] | None = None


class TokenStatus(BaseModel):
    is_logged_in: bool
    login_time: datetime | None = None
    expires_at: datetime | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_name: str | None
    has_kite_credentials: bool = False
    kite_user_id: str | None = None
    is_active: bool
    max_lots: int
    max_order_value: float | None = None
    max_daily_orders: int = 50
    max_open_positions: int = 20
    allowed_exchanges: list[str] | None = None
    allowed_products: list[str] | None = None
    token_status: TokenStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    accounts: list[AccountResponse]


class AuthStatusResponse(BaseModel):
    accounts: list[dict]  # [{account_id, name, is_logged_in, login_time, expires_at}]


class LoginUrlResponse(BaseModel):
    login_url: str
    account_id: uuid.UUID
