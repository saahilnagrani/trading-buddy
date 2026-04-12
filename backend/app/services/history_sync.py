"""Historical data sync from Kite.

Syncs today's trades at end of day. Captures daily portfolio snapshots.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account, AccountToken
from app.models.portfolio import Position, PortfolioSnapshot, TradeHistory
from app.services.kite_service import get_kite_client

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


async def sync_positions(db: AsyncSession):
    """Sync current positions from Kite for all logged-in accounts.

    Called every 1 minute during market hours.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

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
            loop = asyncio.get_event_loop()
            positions_data = await loop.run_in_executor(None, kite.positions)
            net_positions = positions_data.get("net", [])

            # Delete old positions for this account and insert fresh
            await db.execute(
                delete(Position).where(Position.account_id == account.id)
            )

            for p in net_positions:
                qty = p.get("quantity", 0)
                if qty == 0:
                    continue

                pos = Position(
                    account_id=account.id,
                    tradingsymbol=p.get("tradingsymbol", ""),
                    exchange=p.get("exchange", ""),
                    product=p.get("product", ""),
                    quantity=qty,
                    average_price=Decimal(str(p.get("average_price", 0))),
                    last_price=Decimal(str(p.get("last_price", 0))),
                    pnl=Decimal(str(p.get("pnl", 0))),
                    day_change=Decimal(str(p.get("unrealised", 0))),
                    value=Decimal(str(abs(qty) * p.get("last_price", 0))),
                    synced_at=now,
                )
                db.add(pos)

            await db.commit()
            logger.debug(f"Synced {len(net_positions)} positions for {account.name}")

        except Exception as e:
            logger.error(f"Position sync failed for {account.name}: {e}")


async def capture_daily_snapshot(db: AsyncSession):
    """Capture end-of-day portfolio snapshot for all accounts.

    Called at 3:35 PM IST.
    """
    now = datetime.now(timezone.utc)
    today = datetime.now(IST).date()

    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

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
            loop = asyncio.get_event_loop()

            positions_data = await loop.run_in_executor(None, kite.positions)
            margins_data = await loop.run_in_executor(None, kite.margins)

            net_positions = positions_data.get("net", [])
            eq_margin = margins_data.get("equity", {})

            total_pnl = sum(float(p.get("pnl", 0)) for p in net_positions)
            realized = sum(float(p.get("realised", 0)) for p in net_positions)
            unrealized = sum(float(p.get("unrealised", 0)) for p in net_positions)
            margin_used = float(eq_margin.get("utilised", {}).get("debits", 0))
            margin_avail = float(eq_margin.get("available", {}).get("live_balance", 0))
            pos_count = len([p for p in net_positions if p.get("quantity", 0) != 0])

            # Upsert snapshot
            existing = await db.execute(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.account_id == account.id,
                    PortfolioSnapshot.snapshot_date == today,
                )
            )
            snapshot = existing.scalar_one_or_none()
            if snapshot:
                snapshot.total_pnl = Decimal(str(total_pnl))
                snapshot.realized_pnl = Decimal(str(realized))
                snapshot.unrealized_pnl = Decimal(str(unrealized))
                snapshot.margin_used = Decimal(str(margin_used))
                snapshot.margin_available = Decimal(str(margin_avail))
                snapshot.total_value = Decimal(str(margin_avail + margin_used))
                snapshot.position_count = pos_count
            else:
                snapshot = PortfolioSnapshot(
                    account_id=account.id,
                    snapshot_date=today,
                    total_pnl=Decimal(str(total_pnl)),
                    realized_pnl=Decimal(str(realized)),
                    unrealized_pnl=Decimal(str(unrealized)),
                    margin_used=Decimal(str(margin_used)),
                    margin_available=Decimal(str(margin_avail)),
                    total_value=Decimal(str(margin_avail + margin_used)),
                    position_count=pos_count,
                )
                db.add(snapshot)

            await db.commit()
            logger.info(f"Snapshot captured for {account.name}: P&L={total_pnl:.0f}")

        except Exception as e:
            logger.error(f"Snapshot failed for {account.name}: {e}")


async def sync_trade_history(db: AsyncSession):
    """Sync today's trades from Kite for all accounts.

    Called at 3:35 PM IST.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Account)
        .options(selectinload(Account.tokens))
        .where(Account.is_active.is_(True))
    )
    accounts = result.scalars().all()

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
            loop = asyncio.get_event_loop()
            trades = await loop.run_in_executor(None, kite.trades)

            for t in trades:
                trade_id = t.get("order_id", "")
                # Check if already synced
                existing = await db.execute(
                    select(TradeHistory).where(
                        TradeHistory.account_id == account.id,
                        TradeHistory.kite_order_id == str(trade_id),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                trade = TradeHistory(
                    account_id=account.id,
                    kite_order_id=str(trade_id),
                    tradingsymbol=t.get("tradingsymbol", ""),
                    exchange=t.get("exchange", ""),
                    transaction_type=t.get("transaction_type", ""),
                    quantity=t.get("quantity", 0),
                    price=Decimal(str(t.get("average_price", 0))),
                    trade_date=t.get("fill_timestamp") or now,
                    order_execution_time=t.get("order_timestamp"),
                    synced_at=now,
                )
                db.add(trade)

            await db.commit()
            logger.info(f"Synced {len(trades)} trades for {account.name}")

        except Exception as e:
            logger.error(f"Trade sync failed for {account.name}: {e}")
