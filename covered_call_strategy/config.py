"""
Covered Call Strategy - Configuration
All strategy parameters are configurable here.
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import os

# ============================================================
# STRATEGY CONFIGURATION
# ============================================================

@dataclass
class StrategyConfig:
    """All configurable parameters for the covered call strategy."""

    # --- Position Sizing ---
    capital: float = 500_000              # Total capital in INR
    nifty_lot_size: int = 25              # Nifty lot size (as of 2024)
    num_lots: int = 1                     # Number of lots to trade

    # --- Strike Selection ---
    # Options: "atm", "otm_points", "otm_percent", "delta"
    strike_selection: str = "otm_points"
    otm_offset_points: int = 200          # Points above spot for OTM (used if strike_selection="otm_points")
    otm_offset_percent: float = 2.0       # Percent above spot for OTM (used if strike_selection="otm_percent")
    target_delta: float = 0.3             # Delta for strike selection (used if strike_selection="delta")
    strike_step: int = 50                 # Nifty options strike interval

    # --- Entry Timing ---
    # Options: "on_expiry", "days_before_expiry"
    entry_timing: str = "on_expiry"
    entry_days_before_expiry: int = 30    # Used if entry_timing="days_before_expiry"

    # --- Exit / Roll Rules ---
    stop_loss_percent: float = 50.0       # Exit if call premium doubles (50% of premium received = SL on underlying move)
    stop_loss_on_underlying: float = 3.0  # Exit if Nifty drops more than 3% (protect the long position)
    profit_target_percent: float = 80.0   # Roll/exit if 80% of premium captured
    roll_when_itm: bool = True            # Auto-roll when call goes ITM
    roll_up_threshold: float = 1.5        # Roll up if underlying rises by this % after entry

    # --- Risk Management ---
    max_loss_per_trade: float = 25_000    # Max loss per trade in INR before forced exit
    trailing_stop: bool = False           # Enable trailing stop on the short call
    trailing_stop_percent: float = 30.0   # Trail by 30% of max profit

    # --- Transaction Costs ---
    brokerage_per_order: float = 20.0     # Zerodha flat brokerage
    stt_rate: float = 0.0005              # STT on sell side (options)
    exchange_charges: float = 0.00053     # NSE transaction charges
    gst_rate: float = 0.18               # GST on brokerage + exchange charges
    stamp_duty: float = 0.00003          # Stamp duty on buy side
    sebi_charges: float = 0.000001       # SEBI turnover charges

    # --- Backtest Settings ---
    backtest_start: str = "2021-01-01"
    backtest_end: str = "2025-12-31"
    initial_capital: float = 500_000
    risk_free_rate: float = 0.065         # For Sharpe ratio calculation

    # --- Kite Connect Settings ---
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    # --- Data Settings ---
    data_dir: str = "data"
    results_dir: str = "results"

    def round_to_strike(self, price: float) -> int:
        """Round a price to the nearest valid strike."""
        return int(round(price / self.strike_step) * self.strike_step)

    def get_call_strike(self, spot_price: float) -> int:
        """Calculate the call strike to sell based on current config."""
        if self.strike_selection == "atm":
            return self.round_to_strike(spot_price)
        elif self.strike_selection == "otm_points":
            return self.round_to_strike(spot_price + self.otm_offset_points)
        elif self.strike_selection == "otm_percent":
            offset = spot_price * (self.otm_offset_percent / 100)
            return self.round_to_strike(spot_price + offset)
        elif self.strike_selection == "delta":
            # Delta-based selection is handled in the backtester
            # with actual Greeks data; this is a fallback
            return self.round_to_strike(spot_price + self.otm_offset_points)
        else:
            raise ValueError(f"Unknown strike_selection: {self.strike_selection}")

    def calculate_charges(self, premium: float, qty: int, is_buy: bool) -> float:
        """Calculate total transaction charges for an options trade."""
        turnover = premium * qty
        brokerage = min(self.brokerage_per_order, turnover * 0.03)  # Max 20 or 3%

        stt = turnover * self.stt_rate if not is_buy else 0  # STT only on sell
        exchange = turnover * self.exchange_charges
        sebi = turnover * self.sebi_charges
        stamp = turnover * self.stamp_duty if is_buy else 0

        gst = (brokerage + exchange + sebi) * self.gst_rate
        total = brokerage + stt + exchange + gst + stamp + sebi

        return round(total, 2)

    def save(self, filepath: str):
        """Save config to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'StrategyConfig':
        """Load config from JSON."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        config = cls()
        for k, v in data.items():
            if hasattr(config, k):
                setattr(config, k, v)
        return config


# Default config instance
DEFAULT_CONFIG = StrategyConfig()


# ============================================================
# NIFTY MONTHLY EXPIRY DATES (2021-2025)
# These are the last Thursday of each month.
# The data fetcher will also try to compute these dynamically.
# ============================================================

def get_monthly_expiries(year: int) -> list:
    """Get all monthly expiry dates (last Thursday) for a given year."""
    from datetime import date, timedelta
    expiries = []
    for month in range(1, 13):
        # Find last day of month
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Find last Thursday
        while last_day.weekday() != 3:  # 3 = Thursday
            last_day -= timedelta(days=1)

        expiries.append(last_day)
    return expiries
