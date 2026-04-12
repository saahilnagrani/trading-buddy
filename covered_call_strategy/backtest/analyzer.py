"""
Results Analyzer - Generates charts and detailed reports from backtest results.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import StrategyConfig


class BacktestAnalyzer:
    """Generates visual reports from backtest results."""

    def __init__(self, trades_df: pd.DataFrame, equity_df: pd.DataFrame,
                 metrics: dict, config: StrategyConfig):
        self.trades_df = trades_df
        self.equity_df = equity_df
        self.metrics = metrics
        self.config = config
        self.results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config.results_dir
        )
        os.makedirs(self.results_dir, exist_ok=True)

    def generate_all_reports(self):
        """Generate all charts and save to results directory."""
        print("\n[INFO] Generating backtest reports...")

        if self.trades_df.empty:
            print("[WARN] No trades to analyze.")
            return

        self._plot_equity_curve()
        self._plot_monthly_pnl()
        self._plot_trade_distribution()
        self._plot_drawdown()
        self._plot_dashboard()
        self._save_trade_log()

        print(f"[INFO] Reports saved to {self.results_dir}/")

    def _plot_equity_curve(self):
        """Plot equity curve over time."""
        fig, ax = plt.subplots(figsize=(14, 6))

        dates = pd.to_datetime(self.equity_df['date'])
        capital = self.equity_df['capital']

        ax.plot(dates, capital, color='#2196F3', linewidth=2, label='Portfolio Value')
        ax.fill_between(dates, self.config.initial_capital, capital,
                        where=capital >= self.config.initial_capital,
                        alpha=0.15, color='green', label='Profit')
        ax.fill_between(dates, self.config.initial_capital, capital,
                        where=capital < self.config.initial_capital,
                        alpha=0.15, color='red', label='Loss')

        ax.axhline(y=self.config.initial_capital, color='gray', linestyle='--',
                    alpha=0.5, label=f'Initial: INR {self.config.initial_capital:,.0f}')

        ax.set_title('Covered Call Strategy - Equity Curve', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value (INR)')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'equity_curve.png'), dpi=150)
        plt.close()

    def _plot_monthly_pnl(self):
        """Plot monthly P&L bar chart."""
        fig, ax = plt.subplots(figsize=(14, 6))

        df = self.trades_df.copy()
        df['month'] = pd.to_datetime(df['exit_date']).dt.to_period('M')
        monthly = df.groupby('month')['pnl_net'].sum()

        colors = ['#4CAF50' if v >= 0 else '#F44336' for v in monthly.values]
        x_labels = [str(m) for m in monthly.index]

        ax.bar(range(len(monthly)), monthly.values, color=colors, alpha=0.85, edgecolor='white')
        ax.axhline(y=0, color='black', linewidth=0.8)

        ax.set_title('Monthly P&L', fontsize=14, fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('P&L (INR)')
        ax.set_xticks(range(len(monthly)))
        ax.set_xticklabels(x_labels, rotation=90, fontsize=7)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'monthly_pnl.png'), dpi=150)
        plt.close()

    def _plot_trade_distribution(self):
        """Plot P&L distribution histogram."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # P&L histogram
        ax1 = axes[0]
        pnls = self.trades_df['pnl_net']
        ax1.hist(pnls, bins=25, color='#2196F3', alpha=0.7, edgecolor='white')
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=1)
        ax1.axvline(x=pnls.mean(), color='green', linestyle='--', linewidth=1,
                    label=f'Mean: INR {pnls.mean():,.0f}')
        ax1.set_title('Trade P&L Distribution', fontsize=12, fontweight='bold')
        ax1.set_xlabel('P&L (INR)')
        ax1.set_ylabel('Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Exit reason pie chart
        ax2 = axes[1]
        exit_counts = self.trades_df['exit_reason'].value_counts()
        colors_pie = ['#4CAF50', '#FF9800', '#F44336', '#2196F3', '#9C27B0']
        ax2.pie(exit_counts.values, labels=exit_counts.index, autopct='%1.1f%%',
                colors=colors_pie[:len(exit_counts)], startangle=90)
        ax2.set_title('Exit Reasons', fontsize=12, fontweight='bold')

        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'trade_distribution.png'), dpi=150)
        plt.close()

    def _plot_drawdown(self):
        """Plot drawdown chart."""
        fig, ax = plt.subplots(figsize=(14, 4))

        eq = self.equity_df.copy()
        eq['date'] = pd.to_datetime(eq['date'])
        eq['peak'] = eq['capital'].cummax()
        eq['drawdown_pct'] = (eq['capital'] - eq['peak']) / eq['peak'] * 100

        ax.fill_between(eq['date'], 0, eq['drawdown_pct'],
                        color='#F44336', alpha=0.4)
        ax.plot(eq['date'], eq['drawdown_pct'], color='#D32F2F', linewidth=1)

        ax.set_title('Drawdown (%)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown %')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.results_dir, 'drawdown.png'), dpi=150)
        plt.close()

    def _plot_dashboard(self):
        """Create a comprehensive single-page dashboard."""
        fig = plt.figure(figsize=(18, 14))
        gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)

        # Title
        fig.suptitle('Nifty Covered Call Strategy - Backtest Dashboard',
                      fontsize=16, fontweight='bold', y=0.98)

        # 1. Equity Curve (top, full width)
        ax1 = fig.add_subplot(gs[0, :])
        dates = pd.to_datetime(self.equity_df['date'])
        ax1.plot(dates, self.equity_df['capital'], color='#2196F3', linewidth=2)
        ax1.fill_between(dates, self.config.initial_capital, self.equity_df['capital'],
                         where=self.equity_df['capital'] >= self.config.initial_capital,
                         alpha=0.1, color='green')
        ax1.axhline(y=self.config.initial_capital, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title('Equity Curve')
        ax1.set_ylabel('INR')
        ax1.grid(True, alpha=0.3)

        # 2. Monthly P&L (middle left)
        ax2 = fig.add_subplot(gs[1, :2])
        df = self.trades_df.copy()
        df['month'] = pd.to_datetime(df['exit_date']).dt.to_period('M')
        monthly = df.groupby('month')['pnl_net'].sum()
        colors = ['#4CAF50' if v >= 0 else '#F44336' for v in monthly.values]
        ax2.bar(range(len(monthly)), monthly.values, color=colors, alpha=0.85)
        ax2.axhline(y=0, color='black', linewidth=0.8)
        ax2.set_title('Monthly P&L')
        ax2.set_ylabel('INR')
        ax2.set_xticks(range(0, len(monthly), max(1, len(monthly)//12)))
        labels = [str(m) for m in monthly.index]
        ax2.set_xticklabels([labels[i] for i in range(0, len(labels), max(1, len(labels)//12))],
                            rotation=45, fontsize=7)
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. Key Metrics (middle right)
        ax3 = fig.add_subplot(gs[1, 2])
        ax3.axis('off')
        m = self.metrics
        metrics_text = [
            f"Total Return: {m.get('total_return_pct', 0):.1f}%",
            f"CAGR: {m.get('cagr_pct', 0):.1f}%",
            f"Sharpe Ratio: {m.get('sharpe_ratio', 0):.2f}",
            f"Max Drawdown: {m.get('max_drawdown_pct', 0):.1f}%",
            f"Win Rate: {m.get('win_rate_pct', 0):.1f}%",
            f"Profit Factor: {m.get('profit_factor', 0):.2f}",
            f"Total Trades: {m.get('num_trades', 0)}",
            f"Avg Win: INR {m.get('avg_win', 0):,.0f}",
            f"Avg Loss: INR {m.get('avg_loss', 0):,.0f}",
            f"Avg Premium: INR {m.get('avg_premium_collected', 0):,.0f}",
            f"Total Charges: INR {m.get('total_charges', 0):,.0f}",
        ]
        y_start = 0.95
        for i, text in enumerate(metrics_text):
            color = '#4CAF50' if i < 2 else 'black'
            ax3.text(0.05, y_start - i * 0.085, text, fontsize=10,
                     fontfamily='monospace', transform=ax3.transAxes,
                     color=color, fontweight='bold' if i < 4 else 'normal')
        ax3.set_title('Key Metrics', fontweight='bold')

        # 4. P&L Distribution (bottom left)
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.hist(self.trades_df['pnl_net'], bins=20, color='#2196F3', alpha=0.7, edgecolor='white')
        ax4.axvline(x=0, color='red', linestyle='--')
        ax4.set_title('P&L Distribution')
        ax4.set_xlabel('INR')
        ax4.grid(True, alpha=0.3)

        # 5. Exit reasons (bottom center)
        ax5 = fig.add_subplot(gs[2, 1])
        exit_counts = self.trades_df['exit_reason'].value_counts()
        colors_pie = ['#4CAF50', '#FF9800', '#F44336', '#2196F3', '#9C27B0']
        ax5.pie(exit_counts.values, labels=exit_counts.index, autopct='%1.1f%%',
                colors=colors_pie[:len(exit_counts)])
        ax5.set_title('Exit Reasons')

        # 6. Drawdown (bottom right)
        ax6 = fig.add_subplot(gs[2, 2])
        eq = self.equity_df.copy()
        eq['peak'] = eq['capital'].cummax()
        eq['dd'] = (eq['capital'] - eq['peak']) / eq['peak'] * 100
        ax6.fill_between(range(len(eq)), 0, eq['dd'], color='#F44336', alpha=0.4)
        ax6.set_title('Drawdown %')
        ax6.set_ylabel('%')
        ax6.grid(True, alpha=0.3)

        plt.savefig(os.path.join(self.results_dir, 'dashboard.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Dashboard saved: {self.results_dir}/dashboard.png")

    def _save_trade_log(self):
        """Save detailed trade log to CSV."""
        path = os.path.join(self.results_dir, 'trade_log.csv')
        self.trades_df.to_csv(path, index=False)
        print(f"[INFO] Trade log saved: {path}")

        # Also save metrics summary
        metrics_path = os.path.join(self.results_dir, 'metrics_summary.txt')
        with open(metrics_path, 'w') as f:
            f.write("COVERED CALL STRATEGY - BACKTEST METRICS\n")
            f.write("=" * 50 + "\n\n")
            for k, v in self.metrics.items():
                if isinstance(v, dict):
                    f.write(f"{k}:\n")
                    for kk, vv in v.items():
                        f.write(f"  {kk}: {vv}\n")
                else:
                    f.write(f"{k}: {v}\n")
        print(f"[INFO] Metrics saved: {metrics_path}")
