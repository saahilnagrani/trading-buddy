"""APScheduler setup for background tasks."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.tasks.token_cleanup import cleanup_expired_tokens
from app.tasks.order_monitor import sync_order_statuses
from app.tasks.position_sync import sync_positions_task, daily_snapshot_task

scheduler = AsyncIOScheduler()


def start_scheduler():
    # Token cleanup at 6:05 AM IST (00:35 UTC)
    scheduler.add_job(
        cleanup_expired_tokens,
        CronTrigger(hour=0, minute=35),
        id="token_cleanup",
        replace_existing=True,
    )

    # Order status sync every 30 seconds (only runs during market hours)
    scheduler.add_job(
        sync_order_statuses,
        IntervalTrigger(seconds=30),
        id="order_monitor",
        replace_existing=True,
    )

    # Position sync every 60 seconds (only runs during market hours)
    scheduler.add_job(
        sync_positions_task,
        IntervalTrigger(seconds=60),
        id="position_sync",
        replace_existing=True,
    )

    # Daily snapshot at 3:35 PM IST (10:05 UTC)
    scheduler.add_job(
        daily_snapshot_task,
        CronTrigger(hour=10, minute=5),
        id="daily_snapshot",
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
