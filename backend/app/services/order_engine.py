"""Multi-account order execution engine.

Handles placing orders across multiple accounts simultaneously with
rate limiting (shared API key) and per-account validation.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.account import Account, AccountToken
from app.models.order import Order
from app.services.kite_service import get_kite_client
from app.services.token_manager import decrypt_token

logger = logging.getLogger(__name__)

# Rate limiter: max 3 concurrent Kite API calls (shared API key, ~10 req/s limit)
_api_semaphore = asyncio.Semaphore(3)


async def _load_kite_clients(account_ids: list[uuid.UUID], db: AsyncSession) -> dict[uuid.UUID, dict]:
    """Load valid Kite clients for the given accounts. Returns {account_id: {client, account}}."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.id.in_(account_ids), Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

    clients = {}
    for account in accounts:
        valid_token = next(
            (t for t in account.tokens if t.is_valid and t.expires_at > now),
            None,
        )
        if not valid_token:
            continue
        if not account.kite_api_key:
            continue
        try:
            kite = get_kite_client(account_id=account.id, api_key=account.kite_api_key, access_token_encrypted=valid_token.access_token)
            clients[account.id] = {"client": kite, "account": account}
        except Exception as e:
            logger.error(f"Failed to load Kite client for {account.name}: {e}")
    return clients


async def _place_single_order(
    account_id: uuid.UUID,
    account_name: str,
    kite,
    order_params: dict,
    quantity: int,
    group_id: uuid.UUID,
) -> dict:
    """Place a single order on one account via Kite API.

    Uses its own DB session to avoid concurrency issues with asyncio.gather().
    """
    async with async_session() as db:
        order_record = Order(
            account_id=account_id,
            group_id=group_id,
            exchange=order_params["exchange"],
            tradingsymbol=order_params["tradingsymbol"],
            transaction_type=order_params["transaction_type"],
            order_type=order_params["order_type"],
            product=order_params["product"],
            variety=order_params.get("variety", "regular"),
            quantity=quantity,
            price=order_params.get("price"),
            trigger_price=order_params.get("trigger_price"),
            status="PENDING",
        )
        db.add(order_record)
        await db.flush()

        try:
            async with _api_semaphore:
                kite_params = {
                    "variety": order_params.get("variety", "regular"),
                    "exchange": order_params["exchange"],
                    "tradingsymbol": order_params["tradingsymbol"],
                    "transaction_type": order_params["transaction_type"],
                    "order_type": order_params["order_type"],
                    "product": order_params["product"],
                    "quantity": quantity,
                }
                if order_params.get("price"):
                    kite_params["price"] = float(order_params["price"])
                if order_params.get("trigger_price"):
                    kite_params["trigger_price"] = float(order_params["trigger_price"])
                if order_params.get("variety") == "iceberg":
                    if order_params.get("iceberg_legs"):
                        kite_params["iceberg_legs"] = int(order_params["iceberg_legs"])
                    if order_params.get("iceberg_quantity"):
                        kite_params["iceberg_quantity"] = int(order_params["iceberg_quantity"])

                loop = asyncio.get_event_loop()
                kite_order_id = await loop.run_in_executor(
                    None,
                    lambda: kite.place_order(**kite_params),
                )

            order_record.kite_order_id = str(kite_order_id)
            order_record.status = "PLACED"
            order_record.placed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Order placed: {account_name} | {order_params['tradingsymbol']} | qty={quantity} | kite_id={kite_order_id}")

            return {
                "account_id": str(account_id),
                "account_name": account_name,
                "order_id": str(order_record.id),
                "kite_order_id": str(kite_order_id),
                "status": "PLACED",
                "message": None,
            }

        except Exception as e:
            error_msg = str(e)
            order_record.status = "REJECTED"
            order_record.status_message = error_msg
            await db.commit()

            logger.error(f"Order failed: {account_name} | {order_params['tradingsymbol']} | {error_msg}")

            return {
                "account_id": str(account_id),
                "account_name": account_name,
                "order_id": str(order_record.id),
                "kite_order_id": None,
                "status": "ERROR",
                "message": error_msg,
            }


async def place_multi_account_order(
    account_ids: list[uuid.UUID],
    mode: str,
    order_params: dict,
    uniform_quantity: int | None,
    custom_allocations: dict[str, int] | None,
    db: AsyncSession,
) -> dict:
    """Place orders across multiple accounts.

    Args:
        account_ids: List of account UUIDs to trade on.
        mode: "uniform" (same qty all) or "custom" (per-account qty).
        order_params: Order details (exchange, tradingsymbol, etc.).
        uniform_quantity: Quantity for each account (uniform mode).
        custom_allocations: {account_id_str: quantity} (custom mode).
        db: Database session.

    Returns:
        {group_id, results, total, placed, failed}
    """
    group_id = uuid.uuid4()

    # Load Kite clients for all target accounts
    clients = await _load_kite_clients(account_ids, db)

    # Check which accounts are missing
    missing = set(account_ids) - set(clients.keys())
    results = []
    for mid in missing:
        results.append({
            "account_id": str(mid),
            "account_name": "Unknown",
            "order_id": None,
            "kite_order_id": None,
            "status": "ERROR",
            "message": "Account not found or not logged in",
        })

    # Determine quantity per account
    quantities: dict[uuid.UUID, int] = {}
    for aid, info in clients.items():
        account = info["account"]
        if mode == "uniform":
            qty = uniform_quantity or 0
        else:
            qty = (custom_allocations or {}).get(str(aid), 0)

        if qty <= 0:
            results.append({
                "account_id": str(aid),
                "account_name": account.name,
                "order_id": None,
                "kite_order_id": None,
                "status": "ERROR",
                "message": "Quantity must be > 0",
            })
            continue

        # Risk validation
        from app.services.risk_manager import validate_order
        lot_size = _get_lot_size(order_params.get("exchange", ""), order_params.get("tradingsymbol", ""))
        price = Decimal(str(order_params["price"])) if order_params.get("price") else None
        is_valid, rejection_reason = await validate_order(
            account=account,
            exchange=order_params.get("exchange", ""),
            product=order_params.get("product", ""),
            quantity=qty,
            price=price,
            lot_size=lot_size,
            db=db,
        )
        if not is_valid:
            results.append({
                "account_id": str(aid),
                "account_name": account.name,
                "order_id": None,
                "kite_order_id": None,
                "status": "REJECTED",
                "message": rejection_reason,
            })
            continue

        quantities[aid] = qty

    # Place orders concurrently (each gets its own DB session)
    tasks = []
    for aid, qty in quantities.items():
        info = clients[aid]
        tasks.append(
            _place_single_order(
                account_id=aid,
                account_name=info["account"].name,
                kite=info["client"],
                order_params=order_params,
                quantity=qty,
                group_id=group_id,
            )
        )

    if tasks:
        order_results = await asyncio.gather(*tasks)
        results.extend(order_results)

    placed = sum(1 for r in results if r["status"] == "PLACED")
    failed = len(results) - placed

    return {
        "group_id": str(group_id),
        "results": results,
        "total": len(results),
        "placed": placed,
        "failed": failed,
    }


def _get_lot_size(exchange: str, tradingsymbol: str) -> int:
    """Get lot size for an instrument. Returns 0 for equity (no lot constraint)."""
    if exchange not in ("NFO", "BFO", "MCX"):
        return 0  # Equity, no lot size constraint

    # Common lot sizes (will be replaced by instrument cache lookup in production)
    symbol_upper = tradingsymbol.upper()
    if "NIFTY" in symbol_upper and "BANKNIFTY" not in symbol_upper and "FINNIFTY" not in symbol_upper:
        return 25
    if "BANKNIFTY" in symbol_upper:
        return 15
    if "FINNIFTY" in symbol_upper:
        return 25
    if "SENSEX" in symbol_upper:
        return 10

    return 1  # Default for stock options, will be refined with instrument cache


async def cancel_order(order_id: uuid.UUID, db: AsyncSession) -> dict:
    """Cancel an open order."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")

    if order.status not in ("PLACED", "OPEN", "PENDING"):
        raise ValueError(f"Cannot cancel order with status {order.status}")

    if not order.kite_order_id:
        order.status = "CANCELLED"
        await db.commit()
        return {"status": "CANCELLED", "message": "Order was not placed on exchange"}

    # Load Kite client and cancel
    clients = await _load_kite_clients([order.account_id], db)
    if order.account_id not in clients:
        raise ValueError("Account not logged in")

    kite = clients[order.account_id]["client"]
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: kite.cancel_order(variety=order.variety, order_id=order.kite_order_id),
        )
        order.status = "CANCELLED"
        await db.commit()
        return {"status": "CANCELLED", "message": "Order cancelled successfully"}
    except Exception as e:
        raise ValueError(f"Failed to cancel: {e}")


async def modify_order(
    order_id: uuid.UUID,
    price: Decimal | None,
    quantity: int | None,
    trigger_price: Decimal | None,
    order_type: str | None,
    db: AsyncSession,
) -> dict:
    """Modify an open order."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")

    if order.status not in ("PLACED", "OPEN"):
        raise ValueError(f"Cannot modify order with status {order.status}")

    if not order.kite_order_id:
        raise ValueError("Order has no Kite order ID")

    clients = await _load_kite_clients([order.account_id], db)
    if order.account_id not in clients:
        raise ValueError("Account not logged in")

    kite = clients[order.account_id]["client"]
    modify_params = {"variety": order.variety, "order_id": order.kite_order_id}
    if price is not None:
        modify_params["price"] = float(price)
        order.price = price
    if quantity is not None:
        modify_params["quantity"] = quantity
        order.quantity = quantity
    if trigger_price is not None:
        modify_params["trigger_price"] = float(trigger_price)
        order.trigger_price = trigger_price
    if order_type is not None:
        modify_params["order_type"] = order_type
        order.order_type = order_type

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: kite.modify_order(**modify_params),
        )
        await db.commit()
        return {"status": "MODIFIED", "message": "Order modified successfully"}
    except Exception as e:
        raise ValueError(f"Failed to modify: {e}")
