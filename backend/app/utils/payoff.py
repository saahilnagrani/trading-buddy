"""Option strategy payoff calculator.

Computes P&L at expiry for a set of option/futures legs across a range of underlying prices.
"""

from dataclasses import dataclass


@dataclass
class Leg:
    strike: float
    instrument_type: str  # CE, PE, FUT
    transaction_type: str  # BUY, SELL
    quantity: int
    premium: float  # Premium paid/received per unit


def calculate_payoff(
    legs: list[Leg],
    spot_range: tuple[float, float] | None = None,
    num_points: int = 200,
) -> dict:
    """Calculate P&L across a range of underlying prices at expiry.

    Returns:
        {
            "points": [{"underlying_price": float, "pnl": float}, ...],
            "max_profit": float | None,
            "max_loss": float | None,
            "breakevens": [float, ...],
        }
    """
    if not legs:
        return {"points": [], "max_profit": None, "max_loss": None, "breakevens": []}

    # Determine price range if not provided
    strikes = [leg.strike for leg in legs if leg.instrument_type != "FUT"]
    if not strikes:
        strikes = [leg.strike for leg in legs]

    center = sum(strikes) / len(strikes) if strikes else 20000
    spread = max(strikes) - min(strikes) if len(strikes) > 1 else center * 0.1
    margin = max(spread * 2, center * 0.1)

    if spot_range is None:
        low = center - margin
        high = center + margin
    else:
        low, high = spot_range

    step = (high - low) / num_points

    points = []
    prev_pnl = None
    breakevens = []

    for i in range(num_points + 1):
        spot = low + i * step
        total_pnl = 0.0

        for leg in legs:
            multiplier = 1 if leg.transaction_type == "BUY" else -1

            if leg.instrument_type == "CE":
                intrinsic = max(0, spot - leg.strike)
                pnl = (intrinsic - leg.premium) * leg.quantity * multiplier
            elif leg.instrument_type == "PE":
                intrinsic = max(0, leg.strike - spot)
                pnl = (intrinsic - leg.premium) * leg.quantity * multiplier
            elif leg.instrument_type == "FUT":
                pnl = (spot - leg.strike) * leg.quantity * multiplier
            else:
                pnl = 0.0

            total_pnl += pnl

        points.append({"underlying_price": round(spot, 2), "pnl": round(total_pnl, 2)})

        # Detect breakeven (zero crossing)
        if prev_pnl is not None and prev_pnl * total_pnl < 0:
            # Linear interpolation
            prev_spot = low + (i - 1) * step
            ratio = abs(prev_pnl) / (abs(prev_pnl) + abs(total_pnl))
            be = prev_spot + ratio * step
            breakevens.append(round(be, 2))

        prev_pnl = total_pnl

    pnls = [p["pnl"] for p in points]
    max_profit = max(pnls) if pnls else None
    max_loss = min(pnls) if pnls else None

    # If max_profit or max_loss is at the boundary, it may be unbounded
    if pnls and pnls[-1] == max_profit and pnls[-1] > pnls[-2]:
        max_profit = None  # Unbounded profit
    if pnls and pnls[0] == max_loss and pnls[0] < pnls[1]:
        max_loss = None  # Unbounded loss

    return {
        "points": points,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "breakevens": breakevens,
    }
