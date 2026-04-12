"""Background tasks for position syncing and daily snapshots."""

from datetime import datetime, timezone, timedelta

from app.database import async_session
from app.services.history_sync import sync_positions, capture_daily_snapshot, sync_trade_history


def _is_market_hours() -> bool:
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 555 <= minutes <= 930


async def sync_positions_task():
    """Sync positions every minute during market hours."""
    if not _is_market_hours():
        return
    async with async_session() as db:
        await sync_positions(db)


async def daily_snapshot_task():
    """Capture daily snapshot and sync trades at 3:35 PM IST."""
    async with async_session() as db:
        await capture_daily_snapshot(db)
        await sync_trade_history(db)
