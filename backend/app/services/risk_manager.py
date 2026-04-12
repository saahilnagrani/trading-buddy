"""Per-account risk validation.

Called before every order placement to enforce lot limits,
order value caps, daily order count, exchange/product allow-lists,
and open position limits.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.order import Order
from app.models.portfolio import Position

logger = logging.getLogger(__name__)


async def validate_order(
    account: Account,
    exchange: str,
    product: str,
    quantity: int,
    price: Decimal | None,
    lot_size: int,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """Validate an order against account risk controls.

    Returns (is_valid, rejection_reason).
    """
    # 1. Exchange allow-list
    if account.allowed_exchanges and exchange not in account.allowed_exchanges:
        return False, f"Exchange {exchange} not allowed for this account (allowed: {', '.join(account.allowed_exchanges)})"

    # 2. Product allow-list
    if account.allowed_products and product not in account.allowed_products:
        return False, f"Product {product} not allowed for this account (allowed: {', '.join(account.allowed_products)})"

    # 3. Lot limit
    if lot_size > 0 and account.max_lots:
        lots_requested = quantity / lot_size
        if lots_requested > account.max_lots:
            return False, f"Exceeds max lots: requested {lots_requested:.0f}, limit {account.max_lots}"

    # 4. Order value cap
    if account.max_order_value and price:
        order_value = quantity * price
        if order_value > account.max_order_value:
            return False, f"Order value {float(order_value):.0f} exceeds limit {float(account.max_order_value):.0f}"

    # 5. Daily order count
    if account.max_daily_orders:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count_result = await db.execute(
            select(func.count(Order.id)).where(
                Order.account_id == account.id,
                Order.created_at >= today_start,
                Order.status != "REJECTED",
            )
        )
        today_count = count_result.scalar() or 0
        if today_count >= account.max_daily_orders:
            return False, f"Daily order limit reached ({account.max_daily_orders})"

    # 6. Open position count
    if account.max_open_positions:
        pos_result = await db.execute(
            select(func.count(Position.id)).where(
                Position.account_id == account.id,
                Position.quantity != 0,
            )
        )
        open_positions = pos_result.scalar() or 0
        if open_positions >= account.max_open_positions:
            return False, f"Max open positions reached ({account.max_open_positions})"

    return True, None
