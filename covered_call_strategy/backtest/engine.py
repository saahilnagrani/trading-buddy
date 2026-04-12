"""
Covered Call Backtesting Engine
Simulates the covered call strategy month-by-month with configurable parameters.
"""

import os
import sys
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import StrategyConfig, get_monthly_expiries


# ============================================================
# TRADE RECORD
# ============================================================

@dataclass
class Trade:
    """Record of a single covered call trade (one expiry cycle)."""
    entry_date: datetime
    exit_date: datetime
    expiry_date: datetime
    spot_at_entry: float
    spot_at_exit: float
    call_strike: int
    call_premium_received: float
    call_premium_at_exit: float
    lots: int
    lot_size: int
    entry_charges: float
    exit_charges: float
    pnl_option: float          # P&L from the short call
    pnl_underlying: float      # P&L from holding Nifty (futures proxy)
    pnl_net: float             # Total P&L after charges
    exit_reason: str           # "expiry", "stop_loss", "profit_target", "roll_itm"
    call_delta_at_entry: float
    iv_at_entry: float
    dte_at_entry: int


# ============================================================
# BACKTESTER
# ============================================================

class CoveredCallBacktester:
    """
    Backtests a covered call strategy on Nifty monthly options.

    Strategy:
    - Long position: Nifty futures (or equivalent spot exposure)
    - Short position: 1 lot of Nifty monthly CE (call option)
    - Roll/exit based on configurable rules
    """

    def __init__(self, config: StrategyConfig, data: dict):
        self.config = config
        self.spot_df = data['spot'].copy()
        self.options_df = data['options'].copy()
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []

    def run(self) -> dict:
        """Run the full backtest and return results."""
        print("\n" + "=" * 60)
        print("  COVERED CALL BACKTEST")
        print("=" * 60)
        print(f"  Capital: INR {self.config.initial_capital:,.0f}")
        print(f"  Strike: {self.config.strike_selection} "
              f"(+{self.config.otm_offset_points}pts / +{self.config.otm_offset_percent}%)")
        print(f"  Lots: {self.config.num_lots} x {self.config.nifty_lot_size}")
        print(f"  Period: {self.config.backtest_start} to {self.config.backtest_end}")
        print("=" * 60 + "\n")

        # Ensure dates are datetime
        self.spot_df['date'] = pd.to_datetime(self.spot_df['date'])
        self.options_df['date'] = pd.to_datetime(self.options_df['date'])
        self.options_df['expiry'] = pd.to_datetime(self.options_df['expiry'])

        # Get list of monthly expiries within our backtest range
        start_year = int(self.config.backtest_start[:4])
        end_year = int(self.config.backtest_end[:4])
        all_expiries = []
        for yr in range(start_year, end_year + 1):
            all_expiries.extend(get_monthly_expiries(yr))

        bt_start = pd.Timestamp(self.config.backtest_start).date()
        bt_end = pd.Timestamp(self.config.backtest_end).date()
        expiries = [e for e in all_expiries if bt_start <= e <= bt_end]

        capital = self.config.initial_capital
        self.equity_curve = []

        # Process each expiry cycle
        for i in range(len(expiries) - 1):
            current_expiry = expiries[i]
            next_expiry = expiries[i + 1]

            # Determine entry date
            if self.config.entry_timing == "on_expiry":
                entry_date = pd.Timestamp(current_expiry)
            else:
                entry_date = pd.Timestamp(next_expiry) - pd.Timedelta(
                    days=self.config.entry_days_before_expiry
                )

            # Find nearest trading day for entry
            entry_row = self.spot_df[self.spot_df['date'] >= entry_date].head(1)
            if entry_row.empty:
                continue
            entry_date = entry_row.iloc[0]['date']
            spot_at_entry = entry_row.iloc[0]['close']

            # Determine the call strike to sell
            call_strike = self.config.get_call_strike(spot_at_entry)

            # Look up the option price at entry
            entry_opt = self.options_df[
                (self.options_df['date'] == entry_date) &
                (self.options_df['strike'] == call_strike) &
                (self.options_df['expiry'] == pd.Timestamp(next_expiry))
            ]

            if entry_opt.empty:
                # Try nearest available strike
                available = self.options_df[
                    (self.options_df['date'] == entry_date) &
                    (self.options_df['expiry'] == pd.Timestamp(next_expiry))
                ]
                if available.empty:
                    continue
                nearest_idx = (available['strike'] - call_strike).abs().idxmin()
                entry_opt = available.loc[[nearest_idx]]
                call_strike = int(entry_opt.iloc[0]['strike'])

            premium_received = entry_opt.iloc[0]['call_price']
            entry_delta = entry_opt.iloc[0].get('call_delta', 0.3)
            entry_iv = entry_opt.iloc[0].get('iv', 0.15)
            entry_dte = entry_opt.iloc[0].get('dte', 30)

            if premium_received <= 0.5:
                # Skip if premium is negligible
                continue

            qty = self.config.num_lots * self.config.nifty_lot_size
            entry_charges = self.config.calculate_charges(premium_received, qty, is_buy=False)

            # Simulate day-by-day until exit
            trade_days = self.spot_df[
                (self.spot_df['date'] > entry_date) &
                (self.spot_df['date'] <= pd.Timestamp(next_expiry))
            ]

            exit_date = pd.Timestamp(next_expiry)
            exit_spot = spot_at_entry
            exit_premium = 0.0
            exit_reason = "expiry"

            for _, day in trade_days.iterrows():
                day_date = day['date']
                day_spot = day['close']

                # Look up current option price
                day_opt = self.options_df[
                    (self.options_df['date'] == day_date) &
                    (self.options_df['strike'] == call_strike) &
                    (self.options_df['expiry'] == pd.Timestamp(next_expiry))
                ]

                if day_opt.empty:
                    current_premium = max(day_spot - call_strike, 0)
                else:
                    current_premium = day_opt.iloc[0]['call_price']

                # Check exit conditions

                # 1. Stop loss: call premium has risen too much (loss on short call)
                loss_on_call = (current_premium - premium_received) * qty
                if loss_on_call > self.config.max_loss_per_trade:
                    exit_date = day_date
                    exit_spot = day_spot
                    exit_premium = current_premium
                    exit_reason = "stop_loss_call"
                    break

                # 2. Stop loss on underlying drop
                underlying_drop_pct = (spot_at_entry - day_spot) / spot_at_entry * 100
                if underlying_drop_pct > self.config.stop_loss_on_underlying:
                    exit_date = day_date
                    exit_spot = day_spot
                    exit_premium = current_premium
                    exit_reason = "stop_loss_underlying"
                    break

                # 3. Profit target: captured X% of premium
                if premium_received > 0:
                    captured_pct = (premium_received - current_premium) / premium_received * 100
                    if captured_pct >= self.config.profit_target_percent:
                        exit_date = day_date
                        exit_spot = day_spot
                        exit_premium = current_premium
                        exit_reason = "profit_target"
                        break

                # 4. Roll when ITM
                if self.config.roll_when_itm and day_spot > call_strike * 1.01:
                    exit_date = day_date
                    exit_spot = day_spot
                    exit_premium = current_premium
                    exit_reason = "roll_itm"
                    break

                # Update for expiry day
                if day_date >= pd.Timestamp(next_expiry):
                    exit_date = day_date
                    exit_spot = day_spot
                    exit_premium = max(day_spot - call_strike, 0)  # Intrinsic value at expiry
                    exit_reason = "expiry"
                    break

            # If we went through all days without triggering an exit
            if exit_reason == "expiry" and not trade_days.empty:
                exit_spot = trade_days.iloc[-1]['close']
                exit_date = trade_days.iloc[-1]['date']
                exit_premium = max(exit_spot - call_strike, 0)

            # Calculate P&L
            exit_charges = self.config.calculate_charges(exit_premium, qty, is_buy=True)
            total_charges = entry_charges + exit_charges

            # Short call P&L: premium received - premium paid to close
            pnl_option = (premium_received - exit_premium) * qty

            # Long underlying P&L (Nifty move)
            pnl_underlying = (exit_spot - spot_at_entry) * qty

            # Net P&L
            pnl_net = pnl_option + pnl_underlying - total_charges

            capital += pnl_net

            trade = Trade(
                entry_date=entry_date,
                exit_date=exit_date,
                expiry_date=pd.Timestamp(next_expiry),
                spot_at_entry=spot_at_entry,
                spot_at_exit=exit_spot,
                call_strike=call_strike,
                call_premium_received=premium_received,
                call_premium_at_exit=exit_premium,
                lots=self.config.num_lots,
                lot_size=self.config.nifty_lot_size,
                entry_charges=entry_charges,
                exit_charges=exit_charges,
                pnl_option=round(pnl_option, 2),
                pnl_underlying=round(pnl_underlying, 2),
                pnl_net=round(pnl_net, 2),
                exit_reason=exit_reason,
                call_delta_at_entry=entry_delta,
                iv_at_entry=entry_iv,
                dte_at_entry=entry_dte,
            )
            self.trades.append(trade)

            self.equity_curve.append({
                'date': exit_date,
                'capital': round(capital, 2),
                'trade_pnl': round(pnl_net, 2),
                'cumulative_pnl': round(capital - self.config.initial_capital, 2)
            })

            # Print trade summary
            symbol = "+" if pnl_net >= 0 else "-"
            print(
                f"  {entry_date.strftime('%Y-%m-%d')} -> {exit_date.strftime('%Y-%m-%d')} | "
                f"Spot: {spot_at_entry:,.0f} | Strike: {call_strike} | "
                f"Prem: {premium_received:.1f} | "
                f"P&L: {symbol}INR {abs(pnl_net):,.0f} | "
                f"Exit: {exit_reason} | Capital: {capital:,.0f}"
            )

        # Build results
        results = self._compute_metrics(capital)
        return results

    def _compute_metrics(self, final_capital: float) -> dict:
        """Compute backtest performance metrics."""
        if not self.trades:
            print("[WARN] No trades executed.")
            return {}

        initial = self.config.initial_capital
        total_pnl = final_capital - initial
        num_trades = len(self.trades)

        pnls = [t.pnl_net for t in self.trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]

        win_rate = len(winners) / num_trades * 100 if num_trades > 0 else 0
        avg_win = np.mean(winners) if winners else 0
        avg_loss = np.mean(losers) if losers else 0
        profit_factor = abs(sum(winners) / sum(losers)) if losers and sum(losers) != 0 else float('inf')

        # Equity curve analysis
        eq_df = pd.DataFrame(self.equity_curve)
        if not eq_df.empty:
            eq_df['peak'] = eq_df['capital'].cummax()
            eq_df['drawdown'] = (eq_df['capital'] - eq_df['peak']) / eq_df['peak'] * 100
            max_drawdown = eq_df['drawdown'].min()

            # Monthly returns for Sharpe
            monthly_returns = eq_df['trade_pnl'] / initial
            sharpe = 0
            if monthly_returns.std() > 0:
                sharpe = (monthly_returns.mean() * 12) / (monthly_returns.std() * np.sqrt(12))
        else:
            max_drawdown = 0
            sharpe = 0

        # CAGR
        if not eq_df.empty:
            first_date = self.trades[0].entry_date
            last_date = self.trades[-1].exit_date
            years = max((last_date - first_date).days / 365.25, 0.1)
            cagr = ((final_capital / initial) ** (1 / years) - 1) * 100
        else:
            cagr = 0
            years = 0

        # Exit reason breakdown
        exit_reasons = {}
        for t in self.trades:
            exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

        metrics = {
            'initial_capital': initial,
            'final_capital': round(final_capital, 2),
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round(total_pnl / initial * 100, 2),
            'cagr_pct': round(cagr, 2),
            'num_trades': num_trades,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate_pct': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_win': round(max(pnls), 2) if pnls else 0,
            'max_loss': round(min(pnls), 2) if pnls else 0,
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'exit_reasons': exit_reasons,
            'avg_premium_collected': round(np.mean([t.call_premium_received for t in self.trades]), 2),
            'total_charges': round(sum(t.entry_charges + t.exit_charges for t in self.trades), 2),
        }

        # Print summary
        print("\n" + "=" * 60)
        print("  BACKTEST RESULTS")
        print("=" * 60)
        print(f"  Initial Capital:    INR {initial:>12,.2f}")
        print(f"  Final Capital:      INR {final_capital:>12,.2f}")
        print(f"  Total P&L:          INR {total_pnl:>12,.2f}")
        print(f"  Total Return:       {metrics['total_return_pct']:>11.2f}%")
        print(f"  CAGR:               {cagr:>11.2f}%")
        print(f"  Sharpe Ratio:       {sharpe:>11.2f}")
        print(f"  Max Drawdown:       {max_drawdown:>11.2f}%")
        print("-" * 60)
        print(f"  Total Trades:       {num_trades:>11d}")
        print(f"  Win Rate:           {win_rate:>11.1f}%")
        print(f"  Avg Win:            INR {avg_win:>12,.2f}")
        print(f"  Avg Loss:           INR {avg_loss:>12,.2f}")
        print(f"  Profit Factor:      {profit_factor:>11.2f}")
        print(f"  Total Charges:      INR {metrics['total_charges']:>12,.2f}")
        print("-" * 60)
        print(f"  Exit Reasons:")
        for reason, count in exit_reasons.items():
            print(f"    {reason:25s}: {count}")
        print("=" * 60)

        return metrics

    def get_trades_df(self) -> pd.DataFrame:
        """Return trades as a DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        records = []
        for t in self.trades:
            records.append({
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'expiry': t.expiry_date,
                'spot_entry': t.spot_at_entry,
                'spot_exit': t.spot_at_exit,
                'strike': t.call_strike,
                'premium_in': t.call_premium_received,
                'premium_out': t.call_premium_at_exit,
                'pnl_option': t.pnl_option,
                'pnl_underlying': t.pnl_underlying,
                'pnl_net': t.pnl_net,
                'charges': t.entry_charges + t.exit_charges,
                'exit_reason': t.exit_reason,
                'delta': t.call_delta_at_entry,
                'iv': t.iv_at_entry,
                'dte': t.dte_at_entry,
            })
        return pd.DataFrame(records)

    def get_equity_df(self) -> pd.DataFrame:
        """Return equity curve as a DataFrame."""
        return pd.DataFrame(self.equity_curve)
