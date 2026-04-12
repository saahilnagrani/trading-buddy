"""Basket order execution service.

Executes all items in a basket across selected accounts, respecting sort_order.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.basket import Basket
from app.services.order_engine import place_multi_account_order

logger = logging.getLogger(__name__)


async def execute_basket(
    basket_id: uuid.UUID,
    account_ids: list[uuid.UUID],
    mode: str,
    uniform_lots: int | None,
    custom_allocations: dict[str, int] | None,
    db: AsyncSession,
) -> dict:
    """Execute all items in a basket across accounts.

    For uniform mode, quantity = item.quantity * uniform_lots.
    For custom mode, quantity = item.quantity * lots_for_account.

    Items are executed in sort_order sequence (e.g., sell hedge first).
    """
    result = await db.execute(
        select(Basket).options(selectinload(Basket.items)).where(Basket.id == basket_id)
    )
    basket = result.scalar_one_or_none()
    if not basket:
        raise ValueError("Basket not found")

    if not basket.items:
        raise ValueError("Basket has no items")

    all_results = []
    group_ids = []

    # Execute items in sort_order
    sorted_items = sorted(basket.items, key=lambda x: x.sort_order)

    for item in sorted_items:
        order_params = {
            "exchange": item.exchange,
            "tradingsymbol": item.tradingsymbol,
            "transaction_type": item.transaction_type,
            "order_type": item.order_type,
            "product": item.product,
        }
        if item.price_offset and item.order_type == "LIMIT":
            order_params["price"] = float(item.price_offset)  # TODO: add LTP + offset

        # Calculate quantities
        if mode == "uniform":
            qty = item.quantity * (uniform_lots or 1)
            item_result = await place_multi_account_order(
                account_ids=account_ids,
                mode="uniform",
                order_params=order_params,
                uniform_quantity=qty,
                custom_allocations=None,
                db=db,
            )
        else:
            custom_qtys = {}
            for aid_str, lots in (custom_allocations or {}).items():
                custom_qtys[aid_str] = item.quantity * lots
            item_result = await place_multi_account_order(
                account_ids=account_ids,
                mode="custom",
                order_params=order_params,
                uniform_quantity=None,
                custom_allocations=custom_qtys,
                db=db,
            )

        group_ids.append(item_result["group_id"])
        all_results.extend(item_result["results"])

    placed = sum(1 for r in all_results if r["status"] == "PLACED")
    return {
        "basket_id": str(basket_id),
        "basket_name": basket.name,
        "group_ids": group_ids,
        "results": all_results,
        "total": len(all_results),
        "placed": placed,
        "failed": len(all_results) - placed,
    }
