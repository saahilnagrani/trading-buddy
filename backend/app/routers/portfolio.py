import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.portfolio import Position, PortfolioSnapshot, TradeHistory
from app.schemas.portfolio import (
    PortfolioSummaryResponse,
    SnapshotResponse,
    TradeHistoryResponse,
)
from app.services.portfolio_service import get_portfolio_summary, get_positions

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def portfolio_summary(db: AsyncSession = Depends(get_db)):
    return await get_portfolio_summary(db)


@router.get("/positions")
async def list_positions(
    account_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_positions(db, account_id)


@router.get("/snapshots", response_model=list[SnapshotResponse])
async def list_snapshots(
    account_id: uuid.UUID | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cutoff = (datetime.utcnow() - timedelta(days=days)).date()
    query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.snapshot_date >= cutoff)
        .order_by(PortfolioSnapshot.snapshot_date)
    )
    if account_id:
        query = query.where(PortfolioSnapshot.account_id == account_id)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    # Aggregate by date if no account filter
    if not account_id:
        by_date: dict[str, dict] = {}
        for s in snapshots:
            key = s.snapshot_date.isoformat()
            if key not in by_date:
                by_date[key] = {
                    "snapshot_date": s.snapshot_date,
                    "total_pnl": 0,
                    "total_value": 0,
                    "margin_used": 0,
                    "position_count": 0,
                }
            by_date[key]["total_pnl"] += float(s.total_pnl or 0)
            by_date[key]["total_value"] += float(s.total_value or 0)
            by_date[key]["margin_used"] += float(s.margin_used or 0)
            by_date[key]["position_count"] += s.position_count or 0
        return [SnapshotResponse(**v) for v in by_date.values()]

    return [
        SnapshotResponse(
            snapshot_date=s.snapshot_date,
            total_pnl=float(s.total_pnl or 0),
            total_value=float(s.total_value or 0),
            margin_used=float(s.margin_used or 0),
            position_count=s.position_count or 0,
        )
        for s in snapshots
    ]


@router.get("/trades", response_model=list[TradeHistoryResponse])
async def list_trades(
    account_id: uuid.UUID | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = (
        select(TradeHistory)
        .where(TradeHistory.trade_date >= cutoff)
        .order_by(desc(TradeHistory.trade_date))
        .limit(limit)
    )
    if account_id:
        query = query.where(TradeHistory.account_id == account_id)

    result = await db.execute(query)
    trades = result.scalars().all()

    return [
        TradeHistoryResponse(
            id=t.id,
            account_id=t.account_id,
            account_name=t.account.name if t.account else None,
            tradingsymbol=t.tradingsymbol,
            exchange=t.exchange,
            transaction_type=t.transaction_type,
            quantity=t.quantity,
            price=t.price,
            trade_date=t.trade_date,
            charges=t.charges,
            pnl=t.pnl,
        )
        for t in trades
    ]
