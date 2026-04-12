import uuid
from datetime import datetime, timedelta, timezone, time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import redis.asyncio as aioredis

from app.config import settings
from app.database import get_db
from app.models.account import Account, AccountToken
from app.redis import get_redis
from app.schemas.account import AuthStatusResponse, LoginUrlResponse
from app.services.kite_service import get_kite_client
from app.services.token_manager import encrypt_token

router = APIRouter()

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))


def _next_expiry() -> datetime:
    """Token expires at 6:00 AM IST the next day."""
    now = datetime.now(IST)
    tomorrow_6am = datetime.combine(now.date() + timedelta(days=1), time(6, 0), tzinfo=IST)
    return tomorrow_6am


@router.get("/login-url/{account_id}", response_model=LoginUrlResponse)
async def get_login_url(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id, Account.is_active.is_(True)))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Store pending login account_id in Redis (10 min TTL)
    # Kite doesn't forward custom state params, so we track the most recent login request
    r = get_redis()
    await r.set("oauth_pending_account", str(account_id), ex=600)
    await r.aclose()

    kite = get_kite_client()
    login_url = kite.login_url()

    return LoginUrlResponse(login_url=login_url, account_id=account_id)


@router.get("/callback")
async def oauth_callback(
    request_token: str = Query(...),
    status: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    if status != "success":
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=auth_failed")

    # Look up the pending account from the most recent login request
    r = get_redis()
    account_id_str = await r.get("oauth_pending_account")
    await r.delete("oauth_pending_account")
    await r.aclose()

    if not account_id_str:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=no_pending_login")

    account_id = uuid.UUID(account_id_str)

    # Verify account exists
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=account_not_found")

    # Exchange request token for access token
    try:
        kite = get_kite_client()
        session_data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
        access_token = session_data["access_token"]
    except Exception as e:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=token_exchange_failed")

    # Store encrypted token
    now = datetime.now(IST)
    token = AccountToken(
        account_id=account_id,
        access_token=encrypt_token(access_token),
        token_date=now.date(),
        is_valid=True,
        login_time=now,
        expires_at=_next_expiry(),
    )

    # Invalidate any existing token for today
    existing = await db.execute(
        select(AccountToken).where(
            AccountToken.account_id == account_id,
            AccountToken.token_date == now.date(),
        )
    )
    for old_token in existing.scalars().all():
        old_token.is_valid = False

    db.add(token)
    await db.commit()

    # Initialize KiteConnect instance for this account
    get_kite_client(account_id=account_id, access_token_encrypted=token.access_token)

    return RedirectResponse(url=f"{settings.frontend_url}/login?success={account_id}")


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
        .order_by(Account.name)
    )
    accounts = result.scalars().all()

    statuses = []
    for account in accounts:
        valid_token = next(
            (t for t in account.tokens if t.is_valid and t.expires_at > now),
            None,
        )
        statuses.append({
            "account_id": str(account.id),
            "name": account.name,
            "is_logged_in": valid_token is not None,
            "login_time": valid_token.login_time.isoformat() if valid_token else None,
            "expires_at": valid_token.expires_at.isoformat() if valid_token else None,
        })

    return AuthStatusResponse(accounts=statuses)
