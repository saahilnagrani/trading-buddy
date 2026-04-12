"""
Data Fetcher - Downloads Nifty spot + options data from free sources.
Uses NSE India archives and generates synthetic option prices via Black-Scholes
when actual options chain data is unavailable freely.
"""

import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from scipy.stats import norm
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import StrategyConfig, get_monthly_expiries


# ============================================================
# BLACK-SCHOLES MODEL (for synthetic option pricing)
# ============================================================

def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes price for a European call option.
    S: spot price, K: strike, T: time to expiry (years),
    r: risk-free rate, sigma: annualized volatility
    """
    if T <= 0:
        return max(S - K, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return max(price, 0)


def call_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate delta of a call option."""
    if T <= 0:
        return 1.0 if S > K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1)


def implied_vol_from_vix(vix: float) -> float:
    """Convert India VIX to annualized volatility."""
    return vix / 100.0


# ============================================================
# NIFTY SPOT DATA FETCHER
# ============================================================

class NiftyDataFetcher:
    """Fetches Nifty 50 spot and VIX data from free sources."""

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config.data_dir
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_nifty_spot_yahoo(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch Nifty 50 daily OHLCV data from Yahoo Finance."""
        print("[INFO] Fetching Nifty 50 spot data from Yahoo Finance...")

        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        url = (
            f"https://query1.finance.yahoo.com/v7/finance/download/%5ENSEI"
            f"?period1={start_ts}&period2={end_ts}&interval=1d"
            f"&events=history&includeAdjustedClose=true"
        )

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text), parse_dates=['Date'])
            df = df.rename(columns={
                'Date': 'date', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']].dropna()
            df = df.sort_values('date').reset_index(drop=True)
            print(f"[INFO] Fetched {len(df)} rows of Nifty spot data.")
            return df
        except Exception as e:
            print(f"[WARN] Yahoo Finance fetch failed: {e}")
            return pd.DataFrame()

    def fetch_india_vix_yahoo(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch India VIX data from Yahoo Finance."""
        print("[INFO] Fetching India VIX data from Yahoo Finance...")

        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        url = (
            f"https://query1.finance.yahoo.com/v7/finance/download/%5EINDIAVIX"
            f"?period1={start_ts}&period2={end_ts}&interval=1d"
            f"&events=history&includeAdjustedClose=true"
        )

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text), parse_dates=['Date'])
            df = df.rename(columns={'Date': 'date', 'Close': 'vix_close'})
            df = df[['date', 'vix_close']].dropna()
            df = df.sort_values('date').reset_index(drop=True)
            print(f"[INFO] Fetched {len(df)} rows of India VIX data.")
            return df
        except Exception as e:
            print(f"[WARN] India VIX fetch failed: {e}")
            return pd.DataFrame()

    def generate_synthetic_options_data(
        self, spot_df: pd.DataFrame, vix_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate synthetic Nifty options prices using Black-Scholes model.
        This creates call option prices for each trading day at various strikes
        around the spot price, using India VIX as the volatility input.
        """
        print("[INFO] Generating synthetic options data using Black-Scholes...")

        # Merge spot and VIX data
        merged = spot_df.merge(vix_df, on='date', how='left')
        merged['vix_close'] = merged['vix_close'].ffill().fillna(15.0)

        # Get all monthly expiries in the date range
        start_year = merged['date'].dt.year.min()
        end_year = merged['date'].dt.year.max()
        all_expiries = []
        for yr in range(start_year, end_year + 1):
            all_expiries.extend(get_monthly_expiries(yr))

        all_expiries = [e for e in all_expiries
                        if merged['date'].min().date() <= e <= merged['date'].max().date()]

        risk_free = self.config.risk_free_rate
        records = []

        for _, row in merged.iterrows():
            trade_date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
            spot = row['close']
            vix = row['vix_close']
            sigma = implied_vol_from_vix(vix)

            # Find the next TWO monthly expiries (current + next month)
            # so that on expiry day we have data for the following month's options
            upcoming_expiries = []
            for exp in all_expiries:
                if exp >= trade_date:
                    upcoming_expiries.append(exp)
                    if len(upcoming_expiries) >= 2:
                        break
            if not upcoming_expiries:
                continue

            # Generate strikes: spot +/- 1500 points in steps
            step = self.config.strike_step
            center = self.config.round_to_strike(spot)
            strikes = range(center - 1500, center + 1600, step)

            for next_expiry in upcoming_expiries:
                dte = (next_expiry - trade_date).days
                T = max(dte / 365.0, 1/365.0)

                for K in strikes:
                    if K <= 0:
                        continue
                    call_price = black_scholes_call(spot, K, T, risk_free, sigma)
                    delta_val = call_delta(spot, K, T, risk_free, sigma)

                    records.append({
                        'date': row['date'],
                        'spot': spot,
                        'strike': K,
                        'expiry': pd.Timestamp(next_expiry),
                        'dte': dte,
                        'call_price': round(call_price, 2),
                        'call_delta': round(delta_val, 4),
                        'iv': round(sigma, 4),
                        'vix': vix,
                    })

        options_df = pd.DataFrame(records)
        print(f"[INFO] Generated {len(options_df)} synthetic option price rows.")
        return options_df

    def fetch_and_prepare(self) -> dict:
        """
        Main method: fetch all data and return a dict of DataFrames.
        Returns: {'spot': df, 'vix': df, 'options': df}
        """
        start = self.config.backtest_start
        end = self.config.backtest_end

        # 1. Fetch spot data
        spot_df = self.fetch_nifty_spot_yahoo(start, end)

        if spot_df.empty:
            print("[WARN] Could not fetch live data. Generating sample data for demo...")
            spot_df = self._generate_sample_spot_data(start, end)

        # 2. Fetch VIX data
        vix_df = self.fetch_india_vix_yahoo(start, end)

        if vix_df.empty:
            print("[WARN] VIX data unavailable. Using default VIX=15.")
            vix_df = pd.DataFrame({
                'date': spot_df['date'],
                'vix_close': 15.0
            })

        # 3. Generate synthetic options
        options_df = self.generate_synthetic_options_data(spot_df, vix_df)

        # 4. Save to CSV
        spot_path = os.path.join(self.data_dir, 'nifty_spot.csv')
        vix_path = os.path.join(self.data_dir, 'india_vix.csv')
        options_path = os.path.join(self.data_dir, 'nifty_options.csv')

        spot_df.to_csv(spot_path, index=False)
        vix_df.to_csv(vix_path, index=False)
        options_df.to_csv(options_path, index=False)

        print(f"[INFO] Data saved to {self.data_dir}/")
        print(f"  - Spot: {len(spot_df)} rows")
        print(f"  - VIX: {len(vix_df)} rows")
        print(f"  - Options: {len(options_df)} rows")

        return {'spot': spot_df, 'vix': vix_df, 'options': options_df}

    def _generate_sample_spot_data(self, start: str, end: str) -> pd.DataFrame:
        """Generate realistic sample Nifty data using geometric Brownian motion."""
        print("[INFO] Generating realistic sample Nifty spot data...")
        np.random.seed(42)

        dates = pd.bdate_range(start=start, end=end)
        n = len(dates)

        # Start around Nifty's approximate level in 2021
        S0 = 14000
        mu = 0.12     # ~12% annual return
        sigma = 0.16  # ~16% annual vol

        dt = 1 / 252
        prices = [S0]
        for i in range(1, n):
            dS = prices[-1] * (mu * dt + sigma * np.sqrt(dt) * np.random.randn())
            prices.append(max(prices[-1] + dS, prices[-1] * 0.9))  # Floor at 10% drop

        df = pd.DataFrame({
            'date': dates[:n],
            'open': prices,
            'high': [p * (1 + abs(np.random.randn()) * 0.005) for p in prices],
            'low': [p * (1 - abs(np.random.randn()) * 0.005) for p in prices],
            'close': prices,
            'volume': [np.random.randint(100000, 500000) for _ in prices]
        })
        return df

    def load_cached(self) -> dict:
        """Load previously saved data from CSV files."""
        spot_path = os.path.join(self.data_dir, 'nifty_spot.csv')
        vix_path = os.path.join(self.data_dir, 'india_vix.csv')
        options_path = os.path.join(self.data_dir, 'nifty_options.csv')

        if all(os.path.exists(p) for p in [spot_path, vix_path, options_path]):
            print("[INFO] Loading cached data...")
            return {
                'spot': pd.read_csv(spot_path, parse_dates=['date']),
                'vix': pd.read_csv(vix_path, parse_dates=['date']),
                'options': pd.read_csv(options_path, parse_dates=['date', 'expiry'])
            }
        return None


if __name__ == "__main__":
    config = StrategyConfig()
    fetcher = NiftyDataFetcher(config)
    data = fetcher.fetch_and_prepare()
    print("\n[DONE] Data ready for backtesting.")
