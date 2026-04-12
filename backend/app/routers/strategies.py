import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.account import Account
from app.models.strategy import Strategy, StrategyLeg
from app.schemas.strategy import (
    StrategyCreate,
    StrategyResponse,
    StrategyExecuteRequest,
    PayoffResponse,
    PayoffPoint,
    STRATEGY_TEMPLATES,
)
from app.services.strategy_engine import execute_strategy
from app.utils.payoff import calculate_payoff, Leg

router = APIRouter()


@router.get("/templates")
async def list_templates():
    return STRATEGY_TEMPLATES


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Strategy)
        .options(selectinload(Strategy.legs))
        .order_by(Strategy.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Strategy).options(selectinload(Strategy.legs)).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(data: StrategyCreate, db: AsyncSession = Depends(get_db)):
    strategy = Strategy(
        name=data.name,
        strategy_type=data.strategy_type,
        underlying=data.underlying,
        expiry_date=data.expiry_date,
        partial_fill_timeout_secs=data.partial_fill_timeout_secs,
        auto_cancel_unfilled=data.auto_cancel_unfilled,
        square_off_on_partial=data.square_off_on_partial,
    )
    for leg_data in data.legs:
        strategy.legs.append(StrategyLeg(**leg_data.model_dump()))
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy, attribute_names=["legs"])
    return strategy


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if strategy.status in ("ACTIVE", "PARTIALLY_FILLED"):
        raise HTTPException(status_code=400, detail="Cannot delete active strategy")
    await db.delete(strategy)
    await db.commit()


@router.post("/{strategy_id}/execute")
async def execute_strategy_endpoint(
    strategy_id: uuid.UUID,
    req: StrategyExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    if req.account_ids == ["all"]:
        result = await db.execute(select(Account.id).where(Account.is_active.is_(True)))
        account_ids = [row[0] for row in result.all()]
    else:
        account_ids = [uuid.UUID(aid) for aid in req.account_ids]

    try:
        result = await execute_strategy(
            strategy_id=strategy_id,
            account_ids=account_ids,
            mode=req.mode,
            uniform_lots=req.uniform_lots,
            custom_allocations=req.custom_allocations,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{strategy_id}/cancel")
async def cancel_strategy(strategy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Strategy).options(selectinload(Strategy.legs)).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status not in ("ACTIVE", "PARTIALLY_FILLED", "DRAFT"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel strategy in status {strategy.status}")

    from app.services.order_engine import cancel_order
    cancelled = 0
    for leg in strategy.legs:
        if leg.status in ("PLACED", "OPEN") and leg.order_id:
            try:
                await cancel_order(leg.order_id, db)
                leg.status = "CANCELLED"
                cancelled += 1
            except Exception:
                pass

    strategy.status = "CANCELLED"
    await db.commit()
    return {"status": "CANCELLED", "legs_cancelled": cancelled}


@router.post("/{strategy_id}/payoff", response_model=PayoffResponse)
async def get_payoff(strategy_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Strategy).options(selectinload(Strategy.legs)).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    legs = []
    for leg in strategy.legs:
        if leg.instrument_type and leg.strike is not None:
            legs.append(Leg(
                strike=float(leg.strike),
                instrument_type=leg.instrument_type,
                transaction_type=leg.transaction_type,
                quantity=leg.quantity,
                premium=float(leg.price) if leg.price else 0,
            ))

    payoff = calculate_payoff(legs)
    return PayoffResponse(
        points=[PayoffPoint(**p) for p in payoff["points"]],
        max_profit=payoff["max_profit"],
        max_loss=payoff["max_loss"],
        breakevens=payoff["breakevens"],
    )
