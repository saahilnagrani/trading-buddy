"""Instrument cache backed by Redis.

Fetches instruments from Kite once per day, stores in Redis.
Provides search functionality for the trade form autocomplete.
"""

import json
import logging
from datetime import date

import redis.asyncio as aioredis

from app.redis import get_redis
from app.services.kite_service import get_kite_client

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "instruments"
CACHE_TTL = 86400  # 24 hours


async def _get_cache_key(exchange: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{exchange}:{date.today().isoformat()}"


async def refresh_instruments(account_id=None, kite=None) -> bool:
    """Fetch instruments from Kite and store in Redis.

    Uses the provided kite client or the first available one.
    Returns True if successful.
    """
    if kite is None:
        if account_id is None:
            raise ValueError("Either account_id or kite client must be provided")
        kite = get_kite_client(account_id=account_id)

    r = get_redis()
    try:
        import asyncio
        loop = asyncio.get_event_loop()

        for exchange in ("NSE", "NFO"):
            cache_key = await _get_cache_key(exchange)

            # Check if already cached today
            exists = await r.exists(cache_key)
            if exists:
                continue

            instruments = await loop.run_in_executor(None, lambda ex=exchange: kite.instruments(ex))

            # Store as a list of dicts (only fields we need)
            slim_instruments = []
            for inst in instruments:
                slim_instruments.append({
                    "ts": inst["tradingsymbol"],
                    "ex": inst["exchange"],
                    "it": inst.get("instrument_type", ""),
                    "nm": inst.get("name", ""),
                    "ls": inst.get("lot_size", 1),
                    "exp": inst["expiry"].isoformat() if inst.get("expiry") else None,
                    "st": inst.get("strike", 0),
                    "tk": inst.get("tick_size", 0.05),
                })

            await r.set(cache_key, json.dumps(slim_instruments), ex=CACHE_TTL)
            logger.info(f"Cached {len(slim_instruments)} instruments for {exchange}")

        return True
    except Exception as e:
        logger.error(f"Failed to refresh instruments: {e}")
        return False


async def search_instruments(query: str, exchange: str | None = None, limit: int = 20) -> list[dict]:
    """Search instruments by tradingsymbol or name.

    Returns matching instruments sorted by relevance.
    """
    r = get_redis()
    results = []
    exchanges = [exchange] if exchange else ["NSE", "NFO"]
    query_upper = query.upper()

    for ex in exchanges:
        cache_key = await _get_cache_key(ex)
        data = await r.get(cache_key)
        if not data:
            continue

        instruments = json.loads(data)
        for inst in instruments:
            ts = inst["ts"]
            nm = inst["nm"]
            if query_upper in ts.upper() or query_upper in nm.upper():
                results.append({
                    "tradingsymbol": ts,
                    "exchange": inst["ex"],
                    "instrument_type": inst["it"],
                    "name": nm,
                    "lot_size": inst["ls"],
                    "expiry": inst["exp"],
                    "strike": inst["st"] if inst["st"] else None,
                    "tick_size": inst["tk"],
                })

        if len(results) >= limit * 2:
            break

    # Sort: exact prefix matches first, then contains
    results.sort(key=lambda x: (
        0 if x["tradingsymbol"].upper().startswith(query_upper) else 1,
        len(x["tradingsymbol"]),
    ))

    return results[:limit]


async def get_lot_size(exchange: str, tradingsymbol: str) -> int:
    """Look up lot size for a specific instrument from cache."""
    r = get_redis()
    cache_key = await _get_cache_key(exchange)
    data = await r.get(cache_key)
    if not data:
        return 1

    instruments = json.loads(data)
    for inst in instruments:
        if inst["ts"] == tradingsymbol:
            return inst["ls"]
    return 1
