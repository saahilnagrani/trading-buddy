"""Transaction cost calculator for Indian exchanges.

Extracted from covered_call_strategy/config.py and generalized for all instrument types.
"""

from dataclasses import dataclass


@dataclass
class ChargeRates:
    brokerage_per_order: float = 20.0
    stt_rate: float = 0.0005          # STT on sell side for options
    stt_rate_equity: float = 0.001    # STT for equity delivery
    exchange_charges: float = 0.00053
    gst_rate: float = 0.18
    stamp_duty: float = 0.00003
    sebi_charges: float = 0.000001


DEFAULT_RATES = ChargeRates()


def calculate_charges(
    price: float,
    qty: int,
    is_buy: bool,
    instrument_type: str = "OPT",
    rates: ChargeRates = DEFAULT_RATES,
) -> float:
    """Calculate total transaction charges.

    Args:
        price: Trade price (premium for options, price for equity).
        qty: Quantity traded.
        is_buy: True for buy, False for sell.
        instrument_type: "OPT" (options), "FUT" (futures), "EQ" (equity).
        rates: Charge rates to use.

    Returns:
        Total charges in INR.
    """
    turnover = price * qty
    brokerage = min(rates.brokerage_per_order, turnover * 0.03)

    if instrument_type == "EQ":
        stt = turnover * rates.stt_rate_equity
    elif instrument_type == "OPT":
        stt = turnover * rates.stt_rate if not is_buy else 0
    else:  # FUT
        stt = turnover * rates.stt_rate if not is_buy else 0

    exchange = turnover * rates.exchange_charges
    sebi = turnover * rates.sebi_charges
    stamp = turnover * rates.stamp_duty if is_buy else 0
    gst = (brokerage + exchange + sebi) * rates.gst_rate
    total = brokerage + stt + exchange + gst + stamp + sebi

    return round(total, 2)
