import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.order import Order
from app.schemas.order import (
    PlaceOrderRequest,
    PlaceOrderResponse,
    OrderResponse,
    OrderListResponse,
    ModifyOrderRequest,
    InstrumentSearchResult,
)
from app.services.order_engine import place_multi_account_order, cancel_order, modify_order
from app.utils.instruments import search_instruments

router = APIRouter()


@router.post("/place", response_model=PlaceOrderResponse)
async def place_orders(req: PlaceOrderRequest, db: AsyncSession = Depends(get_db)):
    # Resolve "all" to actual account IDs
    if req.account_ids == ["all"]:
        result = await db.execute(
            select(Account.id).where(Account.is_active.is_(True))
        )
        account_ids = [row[0] for row in result.all()]
    else:
        account_ids = [uuid.UUID(aid) for aid in req.account_ids]

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


@router.get("/instruments/search", response_model=list[InstrumentSearchResult])
async def search_instruments_endpoint(
    q: str = Query(..., min_length=2),
    exchange: str | None = Query(None),
):
    results = await search_instruments(query=q, exchange=exchange)
    return [InstrumentSearchResult(**r) for r in results]
