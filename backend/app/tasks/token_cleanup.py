"""Daily task to invalidate expired Kite tokens at 6:05 AM IST."""

from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import async_session
from app.models.account import AccountToken
from app.services.kite_service import clear_all_clients


async def cleanup_expired_tokens():
    """Mark all expired tokens as invalid and clear cached KiteConnect instances."""
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        await session.execute(
            update(AccountToken)
            .where(AccountToken.expires_at <= now, AccountToken.is_valid.is_(True))
            .values(is_valid=False)
        )
        await session.commit()

    clear_all_clients()
