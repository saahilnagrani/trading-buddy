"""Background task to monitor order status during market hours.

Polls kite.orders() for each logged-in account every 30 seconds,
updates the orders table, and publishes changes to Redis pub/sub.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.account import Account, AccountToken
from app.models.order import Order
from app.redis import get_redis
from app.services.kite_service import get_kite_client
from app.services.token_manager import decrypt_token

logger = logging.getLogger(__name__)

PUBSUB_CHANNEL = "order_updates"


def _is_market_hours() -> bool:
    """Check if current time is within market hours (9:15 AM - 3:30 PM IST)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    day = now.weekday()  # 0=Monday
    if day >= 5:  # Saturday, Sunday
        return False
    minutes = now.hour * 60 + now.minute
    return 555 <= minutes <= 930  # 9:15 AM to 3:30 PM


async def sync_order_statuses():
    """Fetch latest order status from Kite for all accounts with open orders."""
    if not _is_market_hours():
        return

    now = datetime.now(timezone.utc)

    async with async_session() as db:
        # Find accounts that have open orders today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        open_orders_result = await db.execute(
            select(Order.account_id)
            .where(
                Order.status.in_(["PLACED", "OPEN", "PENDING"]),
                Order.created_at >= today_start,
            )
            .distinct()
        )
        account_ids_with_open_orders = [row[0] for row in open_orders_result.all()]

        if not account_ids_with_open_orders:
            return

        # Load accounts with valid tokens
        result = await db.execute(
            select(Account)
            .options(selectinload(Account.tokens))
            .where(Account.id.in_(account_ids_with_open_orders), Account.is_active.is_(True))
        )
        accounts = result.scalars().all()

        r = get_redis()

        for account in accounts:
            valid_token = next(
                (t for t in account.tokens if t.is_valid and t.expires_at > now),
                None,
            )
            if not valid_token:
                continue

            try:
                kite = get_kite_client(account_id=account.id, access_token_encrypted=valid_token.access_token)

                loop = asyncio.get_event_loop()
                kite_orders = await loop.run_in_executor(None, kite.orders)

                # Build lookup by kite_order_id
                kite_map = {str(o["order_id"]): o for o in kite_orders}

                # Get our open orders for this account
                db_orders_result = await db.execute(
                    select(Order).where(
                        Order.account_id == account.id,
                        Order.status.in_(["PLACED", "OPEN", "PENDING"]),
                        Order.kite_order_id.isnot(None),
                    )
                )
                db_orders = db_orders_result.scalars().all()

                for order in db_orders:
                    kite_order = kite_map.get(order.kite_order_id)
                    if not kite_order:
                        continue

                    new_status = kite_order["status"].upper()
                    old_status = order.status

                    if new_status != old_status:
                        order.status = new_status
                        order.filled_quantity = kite_order.get("filled_quantity", 0)
                        order.average_price = kite_order.get("average_price")
                        order.status_message = kite_order.get("status_message", "")

                        # Publish update to Redis
                        update_msg = json.dumps({
                            "order_id": str(order.id),
                            "account_id": str(order.account_id),
                            "account_name": account.name,
                            "kite_order_id": order.kite_order_id,
                            "tradingsymbol": order.tradingsymbol,
                            "old_status": old_status,
                            "new_status": new_status,
                            "filled_quantity": order.filled_quantity,
                            "average_price": float(order.average_price) if order.average_price else None,
                        })
                        await r.publish(PUBSUB_CHANNEL, update_msg)

                        logger.info(
                            f"Order {order.kite_order_id} ({account.name}): "
                            f"{old_status} -> {new_status}"
                        )

                await db.commit()

            except Exception as e:
                logger.error(f"Failed to sync orders for {account.name}: {e}")

        await r.aclose()
