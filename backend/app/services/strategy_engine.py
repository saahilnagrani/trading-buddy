"""Multi-leg strategy execution engine.

Handles execution ordering (sell legs first for credit strategies),
partial fill monitoring, and auto-cancellation.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.strategy import Strategy, StrategyLeg
from app.models.order import Order
from app.services.order_engine import place_multi_account_order, cancel_order

logger = logging.getLogger(__name__)


def _is_credit_strategy(legs: list[StrategyLeg]) -> bool:
    """A credit strategy has net sell legs (receives premium)."""
    sell_count = sum(1 for l in legs if l.transaction_type == "SELL")
    buy_count = sum(1 for l in legs if l.transaction_type == "BUY")
    return sell_count >= buy_count


async def execute_strategy(
    strategy_id: uuid.UUID,
    account_ids: list[uuid.UUID],
    mode: str,
    uniform_lots: int | None,
    custom_allocations: dict[str, int] | None,
    db: AsyncSession,
) -> dict:
    """Execute a multi-leg strategy across accounts.

    Execution order:
    - Credit strategies: sell legs first (to collect margin), then buy legs
    - Debit strategies: buy legs first, then sell legs

    After all legs are placed, starts monitoring for partial fills.
    """
    result = await db.execute(
        select(Strategy).options(selectinload(Strategy.legs)).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise ValueError("Strategy not found")

    if strategy.status not in ("DRAFT",):
        raise ValueError(f"Strategy cannot be executed in status {strategy.status}")

    if not strategy.legs:
        raise ValueError("Strategy has no legs")

    legs = sorted(strategy.legs, key=lambda l: l.leg_number)
    is_credit = _is_credit_strategy(legs)

    # Order legs: for credit strategies, sell first; for debit, buy first
    if is_credit:
        ordered_legs = sorted(legs, key=lambda l: (0 if l.transaction_type == "SELL" else 1, l.leg_number))
    else:
        ordered_legs = sorted(legs, key=lambda l: (0 if l.transaction_type == "BUY" else 1, l.leg_number))

    strategy.status = "ACTIVE"
    all_results = []
    group_ids = []

    for leg in ordered_legs:
        if not leg.tradingsymbol:
            leg.status = "CANCELLED"
            all_results.append({
                "leg_number": leg.leg_number,
                "status": "ERROR",
                "message": "No tradingsymbol set for this leg",
            })
            continue

        order_params = {
            "exchange": leg.exchange,
            "tradingsymbol": leg.tradingsymbol,
            "transaction_type": leg.transaction_type,
            "order_type": leg.order_type,
            "product": "NRML",
        }
        if leg.price:
            order_params["price"] = float(leg.price)

        if mode == "uniform":
            qty = leg.quantity * (uniform_lots or 1)
            order_result = await place_multi_account_order(
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
                custom_qtys[aid_str] = leg.quantity * lots
            order_result = await place_multi_account_order(
                account_ids=account_ids,
                mode="custom",
                order_params=order_params,
                uniform_quantity=None,
                custom_allocations=custom_qtys,
                db=db,
            )

        group_ids.append(order_result["group_id"])

        # Update leg status based on results
        placed_count = order_result["placed"]
        if placed_count == order_result["total"]:
            leg.status = "PLACED"
        elif placed_count > 0:
            leg.status = "PLACED"  # At least some went through
        else:
            leg.status = "CANCELLED"

        all_results.append({
            "leg_number": leg.leg_number,
            "tradingsymbol": leg.tradingsymbol,
            "transaction_type": leg.transaction_type,
            "group_id": order_result["group_id"],
            "placed": placed_count,
            "failed": order_result["failed"],
            "results": order_result["results"],
        })

    strategy.group_id = uuid.UUID(group_ids[0]) if group_ids else None
    await db.commit()

    # Start partial fill monitoring in background
    asyncio.create_task(
        _monitor_partial_fills(strategy.id, strategy.partial_fill_timeout_secs, db)
    )

    placed = sum(r.get("placed", 0) for r in all_results)
    failed = sum(r.get("failed", 0) for r in all_results)

    return {
        "strategy_id": str(strategy.id),
        "strategy_name": strategy.name,
        "status": strategy.status,
        "leg_results": all_results,
        "total_placed": placed,
        "total_failed": failed,
    }


async def _monitor_partial_fills(strategy_id: uuid.UUID, timeout_secs: int, db: AsyncSession):
    """Monitor strategy legs for partial fills after execution.

    Waits for timeout, then checks if all legs are filled. If not,
    cancels unfilled legs and optionally squares off filled legs.
    """
    await asyncio.sleep(timeout_secs)

    try:
        from app.database import async_session
        async with async_session() as session:
            result = await session.execute(
                select(Strategy).options(selectinload(Strategy.legs)).where(Strategy.id == strategy_id)
            )
            strategy = result.scalar_one_or_none()
            if not strategy or strategy.status not in ("ACTIVE", "PARTIALLY_FILLED"):
                return

            all_complete = all(l.status == "COMPLETE" for l in strategy.legs)
            if all_complete:
                strategy.status = "FILLED"
                await session.commit()
                logger.info(f"Strategy {strategy.name}: all legs filled")
                return

            has_fills = any(l.status == "COMPLETE" for l in strategy.legs)
            has_pending = any(l.status in ("PLACED", "OPEN", "PENDING") for l in strategy.legs)

            if has_fills and has_pending:
                strategy.status = "PARTIALLY_FILLED"
                logger.warning(f"Strategy {strategy.name}: partial fill detected after {timeout_secs}s timeout")

                if strategy.auto_cancel_unfilled:
                    for leg in strategy.legs:
                        if leg.status in ("PLACED", "OPEN") and leg.order_id:
                            try:
                                await cancel_order(leg.order_id, session)
                                leg.status = "CANCELLED"
                                logger.info(f"  Cancelled unfilled leg {leg.leg_number}")
                            except Exception as e:
                                logger.error(f"  Failed to cancel leg {leg.leg_number}: {e}")

                if strategy.square_off_on_partial:
                    for leg in strategy.legs:
                        if leg.status == "COMPLETE" and leg.tradingsymbol:
                            # Place reverse order to square off
                            reverse_type = "SELL" if leg.transaction_type == "BUY" else "BUY"
                            logger.info(
                                f"  Square off: {reverse_type} {leg.tradingsymbol} "
                                f"qty={leg.fill_quantity}"
                            )
                            # TODO: Place actual square-off order via order engine

                strategy.status = "CANCELLED"
                await session.commit()

            elif not has_fills and has_pending:
                # Nothing filled, just cancel remaining
                if strategy.auto_cancel_unfilled:
                    for leg in strategy.legs:
                        if leg.status in ("PLACED", "OPEN") and leg.order_id:
                            try:
                                await cancel_order(leg.order_id, session)
                                leg.status = "CANCELLED"
                            except Exception:
                                pass
                strategy.status = "CANCELLED"
                await session.commit()

    except Exception as e:
        logger.error(f"Partial fill monitor error for strategy {strategy_id}: {e}")
