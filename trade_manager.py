import logging
import json
import os
from datetime import datetime
import market_data
import config
import asyncio

logger = logging.getLogger(__name__)

TRADES_FILE = "active_trades.json"
HISTORY_FILE = "trade_history.json"

class TradeManager:
    def __init__(self):
        self.active_trades = self.load_trades(TRADES_FILE)
        self.history = self.load_trades(HISTORY_FILE)

    def load_trades(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
        return []

    def save_trades(self):
        try:
            with open(TRADES_FILE, 'w') as f:
                json.dump(self.active_trades, f, indent=4)
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save trades: {e}")

    def open_trade(self, signal_data):
        """Registers a new trade to track."""
        trade = {
            'id': f"{signal_data['symbol']}_{int(datetime.now().timestamp())}",
            'symbol': signal_data['symbol'],
            'market': signal_data['market'],
            'side': signal_data['side'],
            'entry': signal_data['entry'],
            'tp': signal_data['take_profit'],
            'sl': signal_data['stop_loss'],
            'status': 'OPEN',
            'open_time': signal_data['timestamp']
        }
        self.active_trades.append(trade)
        self.save_trades()
        logger.info(f"Opened Trade: {trade['id']}")

    async def update_trades(self, bot):
        """Checks live price for all active trades."""
        if not self.active_trades:
            return

        for trade in self.active_trades[:]:
            try:
                # Fetch current price
                if trade['market'] == 'CRYPTO':
                    # Simplified: Use fetch_ohlcv to get latest close
                    exchange = market_data.get_crypto_exchange()
                    ticker = await asyncio.to_thread(exchange.fetch_ticker, trade['symbol'])
                    curr_price = ticker['last']
                else:
                    # Stocks
                    df = await market_data.fetch_stock_data(trade['symbol'], period='1d', interval='5m')
                    curr_price = df['close'].iloc[-1]

                # Check Outcomes
                outcome = None
                pnl = 0
                
                if trade['side'] == 'LONG':
                    if curr_price >= trade['tp']:
                        outcome = 'WIN'
                        pnl = config.CRYPTO_TAKE_PROFIT if trade['market'] == 'CRYPTO' else config.STOCK_TAKE_PROFIT
                    elif curr_price <= trade['sl']:
                        outcome = 'LOSS'
                        pnl = -1 * (config.CRYPTO_STOP_LOSS if trade['market'] == 'CRYPTO' else config.STOCK_STOP_LOSS)
                elif trade['side'] == 'SHORT':
                     if curr_price <= trade['tp']:
                        outcome = 'WIN'
                        pnl = config.CRYPTO_TAKE_PROFIT
                     elif curr_price >= trade['sl']:
                        outcome = 'LOSS'
                        pnl = -config.CRYPTO_STOP_LOSS

                if outcome:
                    self.close_trade(trade, outcome, curr_price, pnl, bot)

            except Exception as e:
                logger.error(f"Error updating trade {trade['symbol']}: {e}")

    def close_trade(self, trade, outcome, close_price, pnl_pct, bot):
        trade['status'] = 'CLOSED'
        trade['outcome'] = outcome
        trade['close_price'] = close_price
        trade['close_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade['pnl_pct'] = pnl_pct
        
        self.active_trades.remove(trade)
        self.history.append(trade)
        self.save_trades()
        
        # Send Alert
        emoji = "✅" if outcome == 'WIN' else "❌"
        msg = (
            f"{emoji} **TRADE CLOSED: {trade['symbol']}**\n"
            f"Result: {outcome}\n"
            f"PnL: {pnl_pct*100:.2f}%\n"
            f"Close: {close_price}"
        )
        
        # Route to PnL Channel
        channel_id = None
        if trade['market'] == 'CRYPTO':
            channel_id = config.TELEGRAM_CRYPTO_PNL_CHANNEL_ID
        elif trade['market'] == 'STOCK':
             channel_id = config.TELEGRAM_STOCK_PNL_CHANNEL_ID
             
        # Fallback to generic Log Channel or Signal Channel if PnL channel is missing
        if not channel_id:
            channel_id = config.TELEGRAM_LOG_CHANNEL_ID
        
        # Final Fallback: Send to the Main Signal Channel (so checking PnL is possible)
        if not channel_id:
             if trade['market'] == 'CRYPTO':
                channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID
             else:
                channel_id = config.TELEGRAM_STOCK_CHANNEL_ID

        if channel_id:
             asyncio.create_task(bot.send_message(chat_id=channel_id, text=msg, parse_mode='Markdown'))
        else:
             logger.info(f"Trade Closed ({outcome}): {trade['symbol']} (No Channel set)")

    def calculate_balance(self, market_type):
        """Calculates current balance based on initial capital and trade history (Compounding)."""
        if market_type == 'CRYPTO':
            balance = config.INITIAL_CAPITAL_CRYPTO
            currency = "$"
        else:
            balance = config.INITIAL_CAPITAL_STOCK
            currency = "₹"
            
        trades = [t for t in self.history if t['market'] == market_type]
        
        for t in trades:
            try:
                # Standard Risk Management Calculation
                # Risk Amount = Balance * Risk % (e.g. 0.5%)
                # Position Size = Risk Amount / |Entry - SL|
                # PnL = (Exit - Entry) * Size
                
                risk_per_trade = t.get('risk_pct', 0.005)
                risk_amt = balance * risk_per_trade
                
                entry = t['entry']
                sl = t['sl']
                exit_price = t['close_price']
                
                # Protect against zero division
                if entry == sl: continue

                # Quantity
                qty = risk_amt / abs(entry - sl)
                
                # Realized PnL
                if t['side'] == 'LONG':
                    pnl = (exit_price - entry) * qty
                else:
                    pnl = (entry - exit_price) * qty
                
                balance += pnl
            except Exception as e:
                logger.error(f"Error calculating balance for trade {t.get('symbol')}: {e}")
                
        return balance, currency

    def get_stats(self):
        if not self.history:
            return (
                "📊 **Portfolio Status**\n"
                f"Stocks: ₹{config.INITIAL_CAPITAL_STOCK:,.2f} (Start)\n"
                f"Crypto: ${config.INITIAL_CAPITAL_CRYPTO:,.2f} (Start)\n\n"
                "No trades closed yet."
            )
        
        # Calculate Balances
        stock_bal, stock_curr = self.calculate_balance('STOCK')
        crypto_bal, crypto_curr = self.calculate_balance('CRYPTO')
        
        # Calculate Growth
        stock_growth = ((stock_bal - config.INITIAL_CAPITAL_STOCK) / config.INITIAL_CAPITAL_STOCK) * 100
        crypto_growth = ((crypto_bal - config.INITIAL_CAPITAL_CRYPTO) / config.INITIAL_CAPITAL_CRYPTO) * 100
        
        wins = len([t for t in self.history if t['outcome'] == 'WIN'])
        total = len(self.history)
        win_rate = (wins / total) * 100
        
        stats = (
            f"📊 **Portfolio Performance**\n\n"
            f"📈 **Stocks**\n"
            f"Balance: {stock_curr}{stock_bal:,.2f}\n"
            f"Growth: {stock_growth:+.2f}%\n\n"
            f"💰 **Crypto**\n"
            f"Balance: {crypto_curr}{crypto_bal:,.2f}\n"
            f"Growth: {crypto_growth:+.2f}%\n\n"
            f"🏆 **Trade Stats**\n"
            f"Win Rate: {win_rate:.1f}% ({wins}/{total})\n"
            f"Total Trades: {total}"
        )
        return stats
