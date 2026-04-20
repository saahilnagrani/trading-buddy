import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone, time

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.account import Account, AccountToken
from app.models.user import User
from app.redis import get_redis
from app.schemas.account import AuthStatusResponse, LoginUrlResponse
from app.services.kite_service import get_kite_client, remove_kite_client
from app.services.token_manager import encrypt_token, decrypt_token
from app.routers.users import get_current_user

router = APIRouter()

# IST offset
IST = timezone(timedelta(hours=5, minutes=30))


def _next_expiry() -> datetime:
    """Token expires at 6:00 AM IST the next day (or today if logged in before 6 AM)."""
    now = datetime.now(IST)
    today_6am = datetime.combine(now.date(), time(6, 0), tzinfo=IST)
    if now < today_6am:
        # Logged in before 6 AM: token should expire at 6 AM today
        return today_6am.astimezone(timezone.utc)
    # Logged in after 6 AM: token expires at 6 AM tomorrow
    tomorrow_6am = datetime.combine(now.date() + timedelta(days=1), time(6, 0), tzinfo=IST)
    return tomorrow_6am.astimezone(timezone.utc)


@router.get("/login-url/{account_id}", response_model=LoginUrlResponse)
async def get_login_url(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.is_active.is_(True),
            Account.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.kite_api_key or not account.kite_api_secret:
        raise HTTPException(status_code=400, detail="Account missing Kite API credentials. Add them in Accounts settings.")

    # Store pending login account_id in Redis (10 min TTL)
    r = get_redis()
    await r.set("oauth_pending_account", str(account_id), ex=600)

    kite = get_kite_client(account_id=account_id, api_key=account.kite_api_key)
    login_url = kite.login_url()

    return LoginUrlResponse(login_url=login_url, account_id=account_id)


@router.get("/callback")
async def oauth_callback(
    request_token: str = Query(...),
    status: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    if status != "success":
        return RedirectResponse(url=f"{settings.frontend_url}/accounts?error=auth_failed")

    # Look up the pending account from the most recent login request
    r = get_redis()
    account_id_str = await r.get("oauth_pending_account")
    await r.delete("oauth_pending_account")

    if not account_id_str:
        return RedirectResponse(url=f"{settings.frontend_url}/accounts?error=no_pending_login")

    account_id = uuid.UUID(account_id_str)

    # Verify account exists and has credentials
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return RedirectResponse(url=f"{settings.frontend_url}/accounts?error=account_not_found")

    if not account.kite_api_key or not account.kite_api_secret:
        return RedirectResponse(url=f"{settings.frontend_url}/accounts?error=missing_credentials")

    # Exchange request token for access token using per-account credentials
    try:
        kite = get_kite_client(account_id=account_id, api_key=account.kite_api_key)
        api_secret = decrypt_token(account.kite_api_secret)
        session_data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = session_data["access_token"]
        kite_user_id = session_data.get("user_id")
    except Exception as e:
        logger.error(f"Token exchange failed for account {account.name} ({account_id}): {e}")
        return RedirectResponse(url=f"{settings.frontend_url}/accounts?error=token_exchange_failed")

    # Kite User ID binding:
    # - If the account has a manually-configured kite_user_id, the incoming token's user_id MUST match.
    #   Otherwise reject the login to prevent storing the wrong Kite user's token on this internal account.
    # - If the account's kite_user_id is unset, auto-fill it from Kite's response (trust on first login).
    if kite_user_id and account.kite_user_id and account.kite_user_id != kite_user_id:
        logger.warning(
            f"Kite User ID mismatch for account {account.name} ({account_id}): "
            f"expected {account.kite_user_id}, got {kite_user_id}"
        )
        return RedirectResponse(
            url=(
                f"{settings.frontend_url}/accounts"
                f"?error=user_id_mismatch"
                f"&expected={account.kite_user_id}"
                f"&actual={kite_user_id}"
            )
        )
    if kite_user_id and not account.kite_user_id:
        account.kite_user_id = kite_user_id

    # Store encrypted token
    now_ist = datetime.now(IST)
    now_utc = now_ist.astimezone(timezone.utc)
    token = AccountToken(
        account_id=account_id,
        access_token=encrypt_token(access_token),
        token_date=now_ist.date(),
        is_valid=True,
        login_time=now_utc,
        expires_at=_next_expiry(),
    )

    # Delete any existing token for today (unique constraint on account_id + token_date)
    existing = await db.execute(
        select(AccountToken).where(
            AccountToken.account_id == account_id,
            AccountToken.token_date == now_ist.date(),
        )
    )
    for old_token in existing.scalars().all():
        await db.delete(old_token)
    await db.flush()

    db.add(token)
    await db.commit()

    # Initialize KiteConnect instance for this account
    get_kite_client(account_id=account_id, api_key=account.kite_api_key, access_token_encrypted=token.access_token)

    return RedirectResponse(url=f"{settings.frontend_url}/accounts?success={account_id}")


@router.post("/logout/{account_id}")
async def logout_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """End the current Kite session for this account and invalidate the stored token."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.id == account_id, Account.is_active.is_(True), Account.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    valid_token = next(
        (t for t in account.tokens if t.is_valid and t.expires_at > now), None
    )
    if not valid_token:
        # Already logged out; nothing to do on Kite's side but clean up any stale flags
        for t in account.tokens:
            if t.is_valid:
                t.is_valid = False
        await db.commit()
        remove_kite_client(account_id)
        return {"status": "logged_out", "message": "No active session to end"}

    # Best-effort: tell Kite to invalidate this access token
    try:
        if account.kite_api_key:
            access_token = decrypt_token(valid_token.access_token)
            bare_kite = get_kite_client(account_id=account_id, api_key=account.kite_api_key)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: bare_kite.invalidate_access_token(access_token=access_token)
            )
    except Exception as e:
        # If Kite rejects the invalidation (already expired, network, etc.), log and continue.
        logger.warning(f"Kite invalidate_access_token failed for {account.name}: {e}")

    # Always drop local state regardless of what Kite said
    valid_token.is_valid = False
    await db.commit()
    remove_kite_client(account_id)

    return {"status": "logged_out", "message": f"Session ended for {account.name}"}


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True), Account.user_id == current_user.id)
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
