"""Portfolio aggregation service.

Fetches positions and margins from Kite for all accounts,
aggregates into a unified view.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account, AccountToken
from app.models.portfolio import Position
from app.services.kite_service import get_kite_client

logger = logging.getLogger(__name__)


async def _fetch_account_data(account, kite) -> dict:
    """Fetch positions and margins for a single account."""
    loop = asyncio.get_event_loop()
    try:
        positions_data = await loop.run_in_executor(None, kite.positions)
        net_positions = positions_data.get("net", [])
    except Exception as e:
        logger.error(f"Failed to fetch positions for {account.name}: {e}")
        net_positions = []

    try:
        margins_data = await loop.run_in_executor(None, kite.margins)
        equity_margin = margins_data.get("equity", {})
        commodity_margin = margins_data.get("commodity", {})
    except Exception as e:
        logger.error(f"Failed to fetch margins for {account.name}: {e}")
        equity_margin = {}
        commodity_margin = {}

    # Calculate totals
    total_pnl = sum(float(p.get("pnl", 0)) for p in net_positions)
    realized_pnl = sum(float(p.get("realised", 0)) for p in net_positions)
    unrealized_pnl = sum(float(p.get("unrealised", 0)) for p in net_positions)

    eq_used = float(equity_margin.get("utilised", {}).get("debits", 0))
    eq_avail = float(equity_margin.get("available", {}).get("live_balance", 0))

    return {
        "account_id": str(account.id),
        "account_name": account.name,
        "positions": net_positions,
        "total_pnl": total_pnl,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "margin_used": eq_used,
        "margin_available": eq_avail,
        "position_count": len([p for p in net_positions if p.get("quantity", 0) != 0]),
    }


async def get_portfolio_summary(db: AsyncSession) -> dict:
    """Get aggregated portfolio summary across all logged-in accounts."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

    tasks = []
    for account in accounts:
        valid_token = next(
            (t for t in account.tokens if t.is_valid and t.expires_at > now),
            None,
        )
        if not valid_token:
            continue
        if not account.kite_api_key:
            logger.warning(f"Skipping {account.name}: no kite_api_key configured")
            continue
        try:
            kite = get_kite_client(account_id=account.id, api_key=account.kite_api_key, access_token_encrypted=valid_token.access_token)
            tasks.append(_fetch_account_data(account, kite))
        except Exception:
            continue

    if not tasks:
        return {
            "total_pnl": 0, "total_realized_pnl": 0, "total_unrealized_pnl": 0,
            "total_margin_used": 0, "total_margin_available": 0,
            "total_position_count": 0, "accounts": [],
        }

    results = await asyncio.gather(*tasks, return_exceptions=True)
    account_summaries = [r for r in results if isinstance(r, dict)]

    return {
        "total_pnl": sum(a["total_pnl"] for a in account_summaries),
        "total_realized_pnl": sum(a["realized_pnl"] for a in account_summaries),
        "total_unrealized_pnl": sum(a["unrealized_pnl"] for a in account_summaries),
        "total_margin_used": sum(a["margin_used"] for a in account_summaries),
        "total_margin_available": sum(a["margin_available"] for a in account_summaries),
        "total_position_count": sum(a["position_count"] for a in account_summaries),
        "accounts": [
            {
                "account_id": a["account_id"],
                "account_name": a["account_name"],
                "total_pnl": a["total_pnl"],
                "realized_pnl": a["realized_pnl"],
                "unrealized_pnl": a["unrealized_pnl"],
                "margin_used": a["margin_used"],
                "margin_available": a["margin_available"],
                "position_count": a["position_count"],
            }
            for a in account_summaries
        ],
    }


async def get_positions(db: AsyncSession, account_id: uuid.UUID | None = None) -> list[dict]:
    """Get positions from DB (synced by background task)."""
    query = select(Position).order_by(Position.tradingsymbol)
    if account_id:
        query = query.where(Position.account_id == account_id)

    result = await db.execute(query)
    positions = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "account_id": str(p.account_id),
            "account_name": p.account.name if p.account else None,
            "tradingsymbol": p.tradingsymbol,
            "exchange": p.exchange,
            "product": p.product,
            "quantity": p.quantity,
            "average_price": float(p.average_price) if p.average_price else None,
            "last_price": float(p.last_price) if p.last_price else None,
            "pnl": float(p.pnl) if p.pnl else None,
            "day_change": float(p.day_change) if p.day_change else None,
            "day_change_pct": float(p.day_change_pct) if p.day_change_pct else None,
            "value": float(p.value) if p.value else None,
            "instrument_type": p.instrument_type,
            "strike": float(p.strike) if p.strike else None,
            "expiry": p.expiry.isoformat() if p.expiry else None,
            "synced_at": p.synced_at.isoformat(),
        }
        for p in positions
        if p.quantity != 0
    ]
