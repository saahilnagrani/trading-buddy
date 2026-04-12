#!/usr/bin/env python3
"""
Main runner script for the Covered Call Backtest.

Usage:
    python run_backtest.py                          # Run with defaults
    python run_backtest.py --config my_config.json  # Run with custom config
    python run_backtest.py --strike atm             # Override strike selection
    python run_backtest.py --otm-points 300         # Override OTM offset
    python run_backtest.py --lots 2                 # Override lot count
    python run_backtest.py --no-charts              # Skip chart generation
"""

import os
import sys
import argparse
import json

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import StrategyConfig
from data.fetcher import NiftyDataFetcher
from backtest.engine import CoveredCallBacktester
from backtest.analyzer import BacktestAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Nifty Covered Call Strategy - Backtester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_backtest.py
  python run_backtest.py --strike otm_points --otm-points 300
  python run_backtest.py --strike atm --lots 2 --start 2022-01-01
  python run_backtest.py --config my_config.json
  python run_backtest.py --stop-loss 30000 --profit-target 70
        """
    )

    # Config file
    parser.add_argument('--config', '-c', help='Load config from JSON file')
    parser.add_argument('--save-config', help='Save current config to JSON file')

    # Strike selection
    parser.add_argument('--strike', choices=['atm', 'otm_points', 'otm_percent', 'delta'],
                        help='Strike selection method')
    parser.add_argument('--otm-points', type=int, help='OTM offset in points (default: 200)')
    parser.add_argument('--otm-percent', type=float, help='OTM offset in percent (default: 2.0)')

    # Position sizing
    parser.add_argument('--lots', type=int, help='Number of lots (default: 1)')
    parser.add_argument('--capital', type=float, help='Initial capital (default: 500000)')

    # Timing
    parser.add_argument('--entry', choices=['on_expiry', 'days_before_expiry'],
                        help='Entry timing (default: on_expiry)')

    # Exit rules
    parser.add_argument('--stop-loss', type=float, help='Max loss per trade in INR (default: 25000)')
    parser.add_argument('--profit-target', type=float, help='Profit target %% of premium (default: 80)')
    parser.add_argument('--sl-underlying', type=float, help='Stop loss on underlying drop %% (default: 3)')
    parser.add_argument('--no-roll', action='store_true', help='Disable ITM roll')

    # Date range
    parser.add_argument('--start', help='Backtest start date (default: 2021-01-01)')
    parser.add_argument('--end', help='Backtest end date (default: 2025-12-31)')

    # Output
    parser.add_argument('--no-charts', action='store_true', help='Skip chart generation')
    parser.add_argument('--refresh-data', action='store_true', help='Force re-download data')

    return parser.parse_args()


def main():
    args = parse_args()

    # Load or create config
    if args.config and os.path.exists(args.config):
        config = StrategyConfig.load(args.config)
        print(f"[INFO] Loaded config from {args.config}")
    else:
        config = StrategyConfig()

    # Apply CLI overrides
    if args.strike:
        config.strike_selection = args.strike
    if args.otm_points is not None:
        config.otm_offset_points = args.otm_points
    if args.otm_percent is not None:
        config.otm_offset_percent = args.otm_percent
    if args.lots is not None:
        config.num_lots = args.lots
    if args.capital is not None:
        config.initial_capital = args.capital
        config.capital = args.capital
    if args.entry:
        config.entry_timing = args.entry
    if args.stop_loss is not None:
        config.max_loss_per_trade = args.stop_loss
    if args.profit_target is not None:
        config.profit_target_percent = args.profit_target
    if args.sl_underlying is not None:
        config.stop_loss_on_underlying = args.sl_underlying
    if args.no_roll:
        config.roll_when_itm = False
    if args.start:
        config.backtest_start = args.start
    if args.end:
        config.backtest_end = args.end

    # Save config if requested
    if args.save_config:
        config.save(args.save_config)
        print(f"[INFO] Config saved to {args.save_config}")

    # ========================================
    # STEP 1: Fetch Data
    # ========================================
    print("\n[STEP 1] Fetching / Loading Data...")
    fetcher = NiftyDataFetcher(config)

    if not args.refresh_data:
        cached = fetcher.load_cached()
        if cached:
            data = cached
        else:
            data = fetcher.fetch_and_prepare()
    else:
        data = fetcher.fetch_and_prepare()

    # ========================================
    # STEP 2: Run Backtest
    # ========================================
    print("\n[STEP 2] Running Backtest...")
    backtester = CoveredCallBacktester(config, data)
    metrics = backtester.run()

    if not metrics:
        print("\n[ERROR] Backtest produced no results. Check data and config.")
        return

    # ========================================
    # STEP 3: Generate Reports
    # ========================================
    if not args.no_charts:
        print("\n[STEP 3] Generating Reports...")
        trades_df = backtester.get_trades_df()
        equity_df = backtester.get_equity_df()

        analyzer = BacktestAnalyzer(trades_df, equity_df, metrics, config)
        analyzer.generate_all_reports()

    # ========================================
    # STEP 4: Summary
    # ========================================
    print("\n" + "=" * 60)
    print("  BACKTEST COMPLETE")
    print("=" * 60)
    print(f"\n  Results saved in: {config.results_dir}/")
    print(f"  - dashboard.png       (visual summary)")
    print(f"  - equity_curve.png    (portfolio growth)")
    print(f"  - monthly_pnl.png     (month-by-month P&L)")
    print(f"  - trade_distribution.png")
    print(f"  - drawdown.png")
    print(f"  - trade_log.csv       (all trades)")
    print(f"  - metrics_summary.txt")
    print(f"\n  To go LIVE on Kite:")
    print(f"  1. Set API key/secret in config.py or pass via CLI")
    print(f"  2. python live/kite_trader.py login --api-key YOUR_KEY")
    print(f"  3. python live/kite_trader.py auth -t REQUEST_TOKEN")
    print(f"  4. python live/kite_trader.py entry")
    print(f"  5. python live/kite_trader.py monitor (run periodically)")
    print("=" * 60)


if __name__ == "__main__":
    main()
