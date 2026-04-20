import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.account import Account, AccountToken
from app.models.order import Order
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.order import (
    PlaceOrderRequest,
    PlaceOrderResponse,
    OrderResponse,
    OrderListResponse,
    ModifyOrderRequest,
    InstrumentSearchResult,
)
from app.services.order_engine import place_multi_account_order, cancel_order, modify_order
from app.utils.instruments import search_instruments, refresh_instruments
from app.services.kite_service import get_kite_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/place", response_model=PlaceOrderResponse)
async def place_orders(
    req: PlaceOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve "all" to the current user's active account IDs only
    if req.account_ids == ["all"]:
        result = await db.execute(
            select(Account.id).where(Account.is_active.is_(True), Account.user_id == current_user.id)
        )
        account_ids = [row[0] for row in result.all()]
    else:
        requested_ids = [uuid.UUID(aid) for aid in req.account_ids]
        # Verify all requested accounts belong to the current user
        result = await db.execute(
            select(Account.id).where(
                Account.id.in_(requested_ids),
                Account.user_id == current_user.id,
                Account.is_active.is_(True),
            )
        )
        account_ids = [row[0] for row in result.all()]
        if len(account_ids) != len(requested_ids):
            raise HTTPException(status_code=403, detail="One or more accounts not found or not accessible")

    if not account_ids:
        raise HTTPException(status_code=400, detail="No accounts selected")

    if req.mode == "uniform" and not req.uniform_quantity:
        raise HTTPException(status_code=400, detail="uniform_quantity required for uniform mode")

    if req.mode == "custom" and not req.custom_allocations:
        raise HTTPException(status_code=400, detail="custom_allocations required for custom mode")

    order_params = req.order.model_dump(exclude_none=True)

    result = await place_multi_account_order(
        account_ids=account_ids,
        mode=req.mode,
        order_params=order_params,
        uniform_quantity=req.uniform_quantity,
        custom_allocations=req.custom_allocations,
        db=db,
    )

    return PlaceOrderResponse(**result)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    account_id: uuid.UUID | None = Query(None),
    group_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).order_by(desc(Order.created_at))

    if account_id:
        query = query.where(Order.account_id == account_id)
    if group_id:
        query = query.where(Order.group_id == group_id)
    if status:
        query = query.where(Order.status == status.upper())
    if date_from:
        query = query.where(Order.created_at >= date_from)
    if date_to:
        query = query.where(Order.created_at <= date_to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch page
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    orders = result.scalars().all()

    order_responses = []
    for o in orders:
        account_name = o.account.name if o.account else None
        order_responses.append(OrderResponse(
            id=o.id,
            account_id=o.account_id,
            account_name=account_name,
            group_id=o.group_id,
            kite_order_id=o.kite_order_id,
            exchange=o.exchange,
            tradingsymbol=o.tradingsymbol,
            transaction_type=o.transaction_type,
            order_type=o.order_type,
            product=o.product,
            variety=o.variety,
            quantity=o.quantity,
            price=o.price,
            trigger_price=o.trigger_price,
            filled_quantity=o.filled_quantity,
            average_price=o.average_price,
            status=o.status,
            status_message=o.status_message,
            placed_at=o.placed_at,
            created_at=o.created_at,
        ))

    return OrderListResponse(orders=order_responses, total=total)


@router.get("/group/{group_id}", response_model=OrderListResponse)
async def get_order_group(group_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.group_id == group_id).order_by(Order.created_at)
    )
    orders = result.scalars().all()

    order_responses = []
    for o in orders:
        account_name = o.account.name if o.account else None
        order_responses.append(OrderResponse(
            id=o.id,
            account_id=o.account_id,
            account_name=account_name,
            group_id=o.group_id,
            kite_order_id=o.kite_order_id,
            exchange=o.exchange,
            tradingsymbol=o.tradingsymbol,
            transaction_type=o.transaction_type,
            order_type=o.order_type,
            product=o.product,
            variety=o.variety,
            quantity=o.quantity,
            price=o.price,
            trigger_price=o.trigger_price,
            filled_quantity=o.filled_quantity,
            average_price=o.average_price,
            status=o.status,
            status_message=o.status_message,
            placed_at=o.placed_at,
            created_at=o.created_at,
        ))

    return OrderListResponse(orders=order_responses, total=len(order_responses))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        id=o.id,
        account_id=o.account_id,
        account_name=o.account.name if o.account else None,
        group_id=o.group_id,
        kite_order_id=o.kite_order_id,
        exchange=o.exchange,
        tradingsymbol=o.tradingsymbol,
        transaction_type=o.transaction_type,
        order_type=o.order_type,
        product=o.product,
        variety=o.variety,
        quantity=o.quantity,
        price=o.price,
        trigger_price=o.trigger_price,
        filled_quantity=o.filled_quantity,
        average_price=o.average_price,
        status=o.status,
        status_message=o.status_message,
        placed_at=o.placed_at,
        created_at=o.created_at,
    )


@router.put("/{order_id}/cancel")
async def cancel_order_endpoint(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        result = await cancel_order(order_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{order_id}/modify")
async def modify_order_endpoint(
    order_id: uuid.UUID,
    req: ModifyOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await modify_order(
            order_id,
            price=req.price,
            quantity=req.quantity,
            trigger_price=req.trigger_price,
            order_type=req.order_type,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/quote")
async def get_quote(
    symbol: str = Query(..., description="EXCHANGE:TRADINGSYMBOL, e.g. NSE:NIFTY 50"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch live quote from Zerodha for a single instrument."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True), Account.kite_api_key.isnot(None))
    )
    for account in result.scalars().all():
        valid_token = next(
            (t for t in account.tokens if t.is_valid and t.expires_at > now), None
        )
        if not valid_token:
            continue
        try:
            kite = get_kite_client(
                account_id=account.id,
                api_key=account.kite_api_key,
                access_token_encrypted=valid_token.access_token,
            )
            loop = asyncio.get_event_loop()
            quotes = await loop.run_in_executor(None, lambda: kite.quote([symbol]))
            q = quotes.get(symbol)
            if not q:
                raise HTTPException(status_code=404, detail=f"No quote data for {symbol}")

            ohlc = q.get("ohlc", {})
            depth = q.get("depth", {})
            best_bid = depth.get("buy", [{}])[0] if depth.get("buy") else {}
            best_ask = depth.get("sell", [{}])[0] if depth.get("sell") else {}

            close = ohlc.get("close", 0)
            ltp = q.get("last_price", 0)
            change = ltp - close if close else 0
            change_pct = (change / close * 100) if close else 0

            return {
                "last_price": ltp,
                "open": ohlc.get("open", 0),
                "high": ohlc.get("high", 0),
                "low": ohlc.get("low", 0),
                "close": close,
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "volume": q.get("volume", 0),
                "oi": q.get("oi", 0),
                "bid": best_bid.get("price", 0),
                "ask": best_ask.get("price", 0),
                "bid_qty": best_bid.get("quantity", 0),
                "ask_qty": best_ask.get("quantity", 0),
                "last_trade_time": q.get("last_trade_time"),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quote fetch failed via {account.name}: {e}")
            continue

    raise HTTPException(status_code=503, detail="No logged-in account available for quotes")


@router.get("/instruments/search", response_model=list[InstrumentSearchResult])
async def search_instruments_endpoint(
    q: str = Query(..., min_length=2),
    exchange: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    results = await search_instruments(query=q, exchange=exchange)

    # Auto-refresh cache if empty (first search of the day)
    if not results:
        # Find any logged-in account to use for fetching instruments
        now = datetime.now(timezone.utc)
        acct_result = await db.execute(
            select(Account)
            .options(selectinload(Account.tokens))
            .where(Account.is_active.is_(True), Account.kite_api_key.isnot(None))
        )
        for account in acct_result.scalars().all():
            valid_token = next(
                (t for t in account.tokens if t.is_valid and t.expires_at > now), None
            )
            if valid_token:
                try:
                    kite = get_kite_client(
                        account_id=account.id,
                        api_key=account.kite_api_key,
                        access_token_encrypted=valid_token.access_token,
                    )
                    await refresh_instruments(kite=kite)
                    results = await search_instruments(query=q, exchange=exchange)
                    break
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to refresh instruments via {account.name}: {e}")
                    continue

    return [InstrumentSearchResult(**r) for r in results]
