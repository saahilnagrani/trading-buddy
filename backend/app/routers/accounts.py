import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.account import Account, AccountToken
from app.schemas.account import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
    TokenStatus,
)
from app.services.token_manager import encrypt_token

router = APIRouter()


def _build_token_status(account: Account) -> TokenStatus:
    now = datetime.now(timezone.utc)
    valid_token = next(
        (t for t in account.tokens if t.is_valid and t.expires_at > now),
        None,
    )
    if valid_token:
        return TokenStatus(
            is_logged_in=True,
            login_time=valid_token.login_time,
            expires_at=valid_token.expires_at,
        )
    return TokenStatus(is_logged_in=False)


def _account_to_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        name=account.name,
        owner_name=account.owner_name,
        has_kite_credentials=bool(account.kite_api_key and account.kite_api_secret),
        is_active=account.is_active,
        max_lots=account.max_lots,
        token_status=_build_token_status(account),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("", response_model=AccountListResponse)
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
        .order_by(Account.name)
    )
    accounts = result.scalars().all()
    return AccountListResponse(accounts=[_account_to_response(a) for a in accounts])


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Account).options(selectinload(Account.tokens)).where(Account.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return _account_to_response(account)


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(
        name=data.name,
        owner_name=data.owner_name,
        kite_api_key=data.kite_api_key,
        kite_api_secret=encrypt_token(data.kite_api_secret) if data.kite_api_secret else None,
        max_lots=data.max_lots,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account, attribute_names=["tokens"])
    return _account_to_response(account)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: uuid.UUID, data: AccountUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Account).options(selectinload(Account.tokens)).where(Account.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = data.model_dump(exclude_unset=True)
    # Don't overwrite credentials with empty strings
    if "kite_api_key" in update_data and not update_data["kite_api_key"]:
        del update_data["kite_api_key"]
    if "kite_api_secret" in update_data:
        if update_data["kite_api_secret"]:
            update_data["kite_api_secret"] = encrypt_token(update_data["kite_api_secret"])
        else:
            del update_data["kite_api_secret"]
    for key, value in update_data.items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account, attribute_names=["tokens"])
    return _account_to_response(account)


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_active = False
    await db.commit()
