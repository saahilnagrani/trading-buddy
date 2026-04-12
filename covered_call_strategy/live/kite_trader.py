"""
Kite Connect Live Trading Module
Executes the covered call strategy on Zerodha Kite.

IMPORTANT: This module places REAL orders. Use with extreme caution.
Always test with small quantities first.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import StrategyConfig, get_monthly_expiries

try:
    from kiteconnect import KiteConnect, KiteTicker
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    print("[WARN] kiteconnect not installed. Run: pip install kiteconnect")


# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('covered_call_live.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# KITE LIVE TRADER
# ============================================================

class KiteCoveredCallTrader:
    """
    Live covered call strategy execution on Zerodha Kite.

    Workflow:
    1. Authenticate with Kite Connect
    2. Fetch current Nifty spot price
    3. Determine the right call option to sell
    4. Place/manage orders
    5. Monitor positions and apply exit rules
    """

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.kite: Optional[KiteConnect] = None
        self.positions = {}
        self.state_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'live_state.json'
        )

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def authenticate(self, request_token: str = None) -> str:
        """
        Initialize Kite Connect and authenticate.

        First time: Pass the request_token from the login URL.
        Subsequently: Use saved access_token.

        Returns the login URL if request_token is not provided.
        """
        if not KITE_AVAILABLE:
            raise ImportError("kiteconnect package not installed.")

        self.kite = KiteConnect(api_key=self.config.kite_api_key)

        if request_token:
            # Generate access token from request token
            data = self.kite.generate_session(
                request_token,
                api_secret=self.config.kite_api_secret
            )
            access_token = data["access_token"]
            self.config.kite_access_token = access_token
            self.kite.set_access_token(access_token)
            logger.info(f"Authenticated successfully. Token: {access_token[:10]}...")

            # Save token
            self._save_state({'access_token': access_token})
            return access_token

        elif self.config.kite_access_token:
            self.kite.set_access_token(self.config.kite_access_token)
            logger.info("Using saved access token.")
            return self.config.kite_access_token

        else:
            login_url = self.kite.login_url()
            logger.info(f"Please login at: {login_url}")
            logger.info("After login, you'll be redirected with a request_token in the URL.")
            return login_url

    # ========================================================
    # MARKET DATA
    # ========================================================

    def get_nifty_spot(self) -> float:
        """Get current Nifty 50 spot price."""
        quote = self.kite.quote(["NSE:NIFTY 50"])
        spot = quote["NSE:NIFTY 50"]["last_price"]
        logger.info(f"Nifty spot: {spot}")
        return spot

    def get_nifty_fut_price(self) -> Tuple[float, str]:
        """Get current month Nifty futures price and tradingsymbol."""
        # Find current month expiry
        today = date.today()
        expiries = get_monthly_expiries(today.year)
        next_expiry = None
        for exp in expiries:
            if exp >= today:
                next_expiry = exp
                break

        if next_expiry is None:
            expiries = get_monthly_expiries(today.year + 1)
            next_expiry = expiries[0]

        # Nifty futures symbol format: NIFTY{YYMM}FUT
        fut_symbol = f"NFO:NIFTY{next_expiry.strftime('%y%b').upper()}FUT"

        try:
            quote = self.kite.quote([fut_symbol])
            price = quote[fut_symbol]["last_price"]
            return price, fut_symbol
        except Exception as e:
            logger.warning(f"Futures quote failed for {fut_symbol}: {e}")
            # Fallback: use spot
            spot = self.get_nifty_spot()
            return spot, "NSE:NIFTY 50"

    def find_option_instrument(self, strike: int, option_type: str = "CE") -> dict:
        """
        Find the Nifty option instrument for the given strike and type.
        Returns instrument details including tradingsymbol.
        """
        today = date.today()
        expiries = get_monthly_expiries(today.year)
        next_expiry = None
        for exp in expiries:
            if exp >= today:
                next_expiry = exp
                break

        if next_expiry is None:
            expiries = get_monthly_expiries(today.year + 1)
            next_expiry = expiries[0]

        # Nifty options symbol: NIFTY{YYMM}{strike}{CE/PE}
        # Example: NIFTY2530620000CE
        expiry_str = next_expiry.strftime('%y%b').upper()

        # Try different symbol formats (Zerodha format can vary)
        possible_symbols = [
            f"NFO:NIFTY{next_expiry.strftime('%y%m%d')}{strike}{option_type}",
            f"NFO:NIFTY{expiry_str}{strike}{option_type}",
        ]

        # Search instruments
        try:
            instruments = self.kite.instruments("NFO")
            for inst in instruments:
                if (inst['name'] == 'NIFTY' and
                    inst['strike'] == strike and
                    inst['instrument_type'] == option_type and
                    inst['expiry'] == next_expiry):
                    logger.info(f"Found option: {inst['tradingsymbol']} (token: {inst['instrument_token']})")
                    return inst
        except Exception as e:
            logger.error(f"Instrument search failed: {e}")

        return None

    def get_option_ltp(self, tradingsymbol: str) -> float:
        """Get last traded price for an option."""
        key = f"NFO:{tradingsymbol}"
        quote = self.kite.quote([key])
        return quote[key]["last_price"]

    # ========================================================
    # ORDER MANAGEMENT
    # ========================================================

    def sell_call(self, strike: int, qty: int = None) -> dict:
        """
        Sell a Nifty call option (short call leg of covered call).
        Returns order details.
        """
        if qty is None:
            qty = self.config.num_lots * self.config.nifty_lot_size

        instrument = self.find_option_instrument(strike, "CE")
        if not instrument:
            logger.error(f"Could not find CE option for strike {strike}")
            return None

        symbol = instrument['tradingsymbol']
        ltp = self.get_option_ltp(symbol)

        logger.info(f"Selling {qty} qty of {symbol} @ ~{ltp}")

        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NFO,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_SELL,
                quantity=qty,
                product=self.kite.PRODUCT_NRML,
                order_type=self.kite.ORDER_TYPE_LIMIT,
                price=ltp,  # Limit order at LTP
                validity=self.kite.VALIDITY_DAY,
            )
            logger.info(f"Sell order placed. Order ID: {order_id}")

            # Save position state
            self._save_position({
                'type': 'short_call',
                'symbol': symbol,
                'strike': strike,
                'qty': qty,
                'entry_price': ltp,
                'order_id': order_id,
                'entry_time': datetime.now().isoformat(),
            })

            return {'order_id': order_id, 'symbol': symbol, 'price': ltp}

        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None

    def buy_call_to_close(self, symbol: str, qty: int) -> dict:
        """Buy back the short call to close the position."""
        ltp = self.get_option_ltp(symbol)
        logger.info(f"Buying to close {qty} qty of {symbol} @ ~{ltp}")

        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NFO,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_BUY,
                quantity=qty,
                product=self.kite.PRODUCT_NRML,
                order_type=self.kite.ORDER_TYPE_LIMIT,
                price=ltp,
                validity=self.kite.VALIDITY_DAY,
            )
            logger.info(f"Buy-to-close order placed. Order ID: {order_id}")
            return {'order_id': order_id, 'symbol': symbol, 'price': ltp}

        except Exception as e:
            logger.error(f"Close order failed: {e}")
            return None

    # ========================================================
    # STRATEGY EXECUTION
    # ========================================================

    def execute_entry(self) -> dict:
        """
        Execute the covered call entry:
        1. Check if there's an existing position
        2. Get Nifty spot and determine strike
        3. Sell the call option

        NOTE: This assumes you already have a long Nifty position
        (via futures, ETF, or equivalent). The strategy only manages
        the short call leg.
        """
        logger.info("=" * 50)
        logger.info("EXECUTING COVERED CALL ENTRY")
        logger.info("=" * 50)

        # Check existing positions
        existing = self._load_position()
        if existing and existing.get('type') == 'short_call':
            logger.warning(f"Active short call exists: {existing['symbol']}")
            logger.warning("Close existing position first or run monitor.")
            return None

        # Get spot and calculate strike
        spot = self.get_nifty_spot()
        call_strike = self.config.get_call_strike(spot)

        logger.info(f"Spot: {spot}, Target strike: {call_strike}")
        logger.info(f"Strike selection: {self.config.strike_selection}")

        # Sell the call
        result = self.sell_call(call_strike)

        if result:
            logger.info(f"Entry complete. Sold {call_strike} CE @ {result['price']}")
            logger.info(f"Premium collected: INR {result['price'] * self.config.num_lots * self.config.nifty_lot_size:,.2f}")
        else:
            logger.error("Entry failed!")

        return result

    def monitor_and_manage(self) -> dict:
        """
        Monitor the current position and apply exit/roll rules.
        Call this periodically (e.g., every 5 minutes during market hours).

        Returns action taken, if any.
        """
        position = self._load_position()
        if not position:
            logger.info("No active position to monitor.")
            return {'action': 'none', 'reason': 'no_position'}

        symbol = position['symbol']
        strike = position['strike']
        entry_price = position['entry_price']
        qty = position['qty']

        # Get current prices
        try:
            current_premium = self.get_option_ltp(symbol)
            spot = self.get_nifty_spot()
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return {'action': 'error', 'reason': str(e)}

        logger.info(
            f"Monitor | Spot: {spot} | Strike: {strike} | "
            f"Entry Prem: {entry_price} | Curr Prem: {current_premium}"
        )

        # Check exit conditions

        # 1. Stop loss on call (premium has risen significantly)
        loss_on_call = (current_premium - entry_price) * qty
        if loss_on_call > self.config.max_loss_per_trade:
            logger.warning(f"STOP LOSS triggered! Loss: INR {loss_on_call:,.2f}")
            result = self.buy_call_to_close(symbol, qty)
            self._clear_position()
            return {'action': 'stop_loss', 'loss': loss_on_call, 'result': result}

        # 2. Profit target (captured enough premium decay)
        if entry_price > 0:
            captured_pct = (entry_price - current_premium) / entry_price * 100
            if captured_pct >= self.config.profit_target_percent:
                logger.info(f"PROFIT TARGET reached! Captured {captured_pct:.1f}% of premium")
                result = self.buy_call_to_close(symbol, qty)
                self._clear_position()
                return {'action': 'profit_target', 'captured_pct': captured_pct, 'result': result}

        # 3. Roll when deep ITM
        if self.config.roll_when_itm and spot > strike * 1.01:
            logger.info(f"ROLL ITM: Spot {spot} > Strike {strike}")
            # Close current
            close_result = self.buy_call_to_close(symbol, qty)
            self._clear_position()

            # Open new position at higher strike
            new_strike = self.config.get_call_strike(spot)
            sell_result = self.sell_call(new_strike)

            return {
                'action': 'roll_itm',
                'old_strike': strike,
                'new_strike': new_strike,
                'close_result': close_result,
                'sell_result': sell_result
            }

        # 4. Check DTE for roll to next month
        today = date.today()
        expiries = get_monthly_expiries(today.year)
        next_expiry = None
        for exp in expiries:
            if exp >= today:
                next_expiry = exp
                break

        if next_expiry:
            dte = (next_expiry - today).days
            if dte <= 1:
                logger.info(f"EXPIRY DAY: DTE={dte}. Letting option expire/settle.")
                self._clear_position()
                return {'action': 'expiry', 'dte': dte}

        return {'action': 'hold', 'current_premium': current_premium, 'spot': spot}

    def get_positions_summary(self) -> dict:
        """Get a summary of current Kite positions."""
        if not self.kite:
            return {}

        try:
            positions = self.kite.positions()
            orders = self.kite.orders()

            net_positions = positions.get('net', [])
            nifty_positions = [p for p in net_positions if 'NIFTY' in p.get('tradingsymbol', '')]

            return {
                'nifty_positions': nifty_positions,
                'pending_orders': [o for o in orders if o['status'] == 'OPEN'],
                'total_pnl': sum(p.get('pnl', 0) for p in nifty_positions),
            }
        except Exception as e:
            logger.error(f"Position fetch failed: {e}")
            return {}

    # ========================================================
    # STATE MANAGEMENT
    # ========================================================

    def _save_position(self, position: dict):
        """Save current position to file."""
        state = self._load_state()
        state['current_position'] = position
        self._save_state(state)

    def _load_position(self) -> Optional[dict]:
        """Load current position from file."""
        state = self._load_state()
        return state.get('current_position')

    def _clear_position(self):
        """Clear current position."""
        state = self._load_state()
        state['current_position'] = None
        self._save_state(state)

    def _save_state(self, state: dict):
        """Save full state to file."""
        existing = self._load_state()
        existing.update(state)
        with open(self.state_file, 'w') as f:
            json.dump(existing, f, indent=2, default=str)

    def _load_state(self) -> dict:
        """Load full state from file."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """CLI for live trading operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Covered Call - Live Trading on Kite")
    parser.add_argument('action', choices=['login', 'auth', 'entry', 'monitor', 'status', 'close'],
                        help='Action to perform')
    parser.add_argument('--request-token', '-t', help='Kite request token for authentication')
    parser.add_argument('--config', '-c', help='Path to config JSON file')
    parser.add_argument('--api-key', help='Kite API key')
    parser.add_argument('--api-secret', help='Kite API secret')
    args = parser.parse_args()

    # Load config
    if args.config and os.path.exists(args.config):
        config = StrategyConfig.load(args.config)
    else:
        config = StrategyConfig()

    if args.api_key:
        config.kite_api_key = args.api_key
    if args.api_secret:
        config.kite_api_secret = args.api_secret

    if not config.kite_api_key:
        logger.error("Kite API key is required. Set it in config or pass --api-key")
        return

    trader = KiteCoveredCallTrader(config)

    if args.action == 'login':
        url = trader.authenticate()
        print(f"\nLogin URL: {url}")
        print("After logging in, copy the request_token from the redirect URL.")
        print("Then run: python kite_trader.py auth --request-token YOUR_TOKEN")

    elif args.action == 'auth':
        if not args.request_token:
            print("Error: --request-token is required for auth")
            return
        token = trader.authenticate(args.request_token)
        print(f"Authenticated! Access token saved.")

    elif args.action == 'entry':
        trader.authenticate()
        result = trader.execute_entry()
        if result:
            print(f"\nEntry successful!")
            print(f"  Order ID: {result['order_id']}")
            print(f"  Symbol: {result['symbol']}")
            print(f"  Premium: {result['price']}")

    elif args.action == 'monitor':
        trader.authenticate()
        result = trader.monitor_and_manage()
        print(f"\nMonitor result: {result['action']}")
        print(json.dumps(result, indent=2, default=str))

    elif args.action == 'status':
        trader.authenticate()
        summary = trader.get_positions_summary()
        print(json.dumps(summary, indent=2, default=str))

    elif args.action == 'close':
        trader.authenticate()
        position = trader._load_position()
        if position:
            result = trader.buy_call_to_close(position['symbol'], position['qty'])
            trader._clear_position()
            print(f"Position closed: {result}")
        else:
            print("No active position to close.")


if __name__ == "__main__":
    main()
