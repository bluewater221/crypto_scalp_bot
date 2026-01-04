import logging
import json
import os
import threading
from datetime import datetime
import market_data
import config
import asyncio
import sheets

logger = logging.getLogger(__name__)

class TradeManager:
    def __init__(self, market_tag, trades_file, history_file, initial_capital, leverage=1):
        self.market_tag = market_tag
        self.trades_file = trades_file
        self.history_file = history_file
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.currency = "₹" if 'STOCK' in market_tag else "$"
        self._lock = threading.Lock()
        
        self.active_trades = self.load_trades(self.trades_file)
        logger.info(f"[{self.market_tag}] 📂 Loaded {len(self.active_trades)} ACTIVE trades from {self.trades_file}")
        
        # Try to restore history from Google Sheets (Persistent Storage)
        sheet_history = sheets.fetch_trade_history()
        
        if sheet_history:
             # Filter only trades relevant to this manager (Case Insensitive)
             self.history = [t for t in sheet_history if str(t.get('market', '')).upper() == self.market_tag.upper()]
             logger.info(f"[{self.market_tag}] ✅ Restored {len(self.history)} trades from Sheet (out of {len(sheet_history)} total history).")
        else:
             self.history = self.load_trades(self.history_file)
             logger.info(f"[{self.market_tag}] 📜 Loaded {len(self.history)} trades from local {self.history_file}")

        # Final Balance Check for Debugging
        initial_balance = self.calculate_balance()
        logger.info(f"[{self.market_tag}] 💰 Initial Portfolio Balance: {self.currency}{initial_balance:,.2f}")

    def load_trades(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
        return []

    def save_trades(self):
        with self._lock:
            try:
                with open(self.trades_file, 'w') as f:
                    json.dump(self.active_trades, f, indent=4)
                with open(self.history_file, 'w') as f:
                    json.dump(self.history, f, indent=4)
            except Exception as e:
                logger.error(f"Failed to save {self.trades_file}: {e}")

    def open_trade(self, signal_data):
        """register a new trade for this specific manager."""
        # Risk Pct
        if 'STOCK' in self.market_tag:
             risk_pct = config.STOCK_RISK_PER_TRADE
        else:
             risk_pct = config.CRYPTO_RISK_PER_TRADE
        
        # Create Unique ID
        trade_id = f"{signal_data['symbol']}_{self.market_tag}_{int(datetime.now().timestamp())}"
        
        trade = {
            'id': trade_id,
            'symbol': signal_data['symbol'],
            'market': self.market_tag,
            'side': signal_data['side'],
            'entry': signal_data['entry'],
            'tp': signal_data['take_profit'],
            'sl': signal_data['stop_loss'],
            'status': 'OPEN',
            'open_time': signal_data['timestamp'],
            'risk_pct': risk_pct
        }
        self.active_trades.append(trade)
        self.save_trades()
        logger.info(f"Opened Trade: {trade['id']} ({self.market_tag})")

    async def update_trades(self, bot):
        """Checks live price for all active trades."""
        if not self.active_trades:
            return

        for trade in self.active_trades[:]:
            try:
                # Fetch current price with retries
                curr_price = None
                for attempt in range(3):
                    try:
                        if 'CRYPTO' in trade['market']:
                            exchange = market_data.get_crypto_exchange()
                            ticker = await asyncio.to_thread(exchange.fetch_ticker, trade['symbol'])
                            curr_price = ticker['last']
                        else:
                            # Stocks
                            df = await market_data.fetch_stock_data(trade['symbol'], period='1d', interval='5m')
                            if df is not None and not df.empty:
                                curr_price = df['close'].iloc[-1]
                        
                        if curr_price is not None:
                            break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt+1} failed for {trade['symbol']}: {e}")
                        await asyncio.sleep(1)

                if curr_price is None:
                    continue

                # Check Outcomes
                outcome = None
                pnl = 0
                
                if trade['side'] == 'LONG':
                    if curr_price >= trade['tp']:
                        outcome = 'WIN'
                        pnl = config.CRYPTO_TAKE_PROFIT if 'CRYPTO' in trade['market'] else config.STOCK_TAKE_PROFIT
                    elif curr_price <= trade['sl']:
                        outcome = 'LOSS'
                        pnl = -1 * (config.CRYPTO_STOP_LOSS if 'CRYPTO' in trade['market'] else config.STOCK_STOP_LOSS)
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
                # "Smart" self-healing: If ticker fetch fails repeatedly, we could auto-close or flag.
                # For now, just logging error loudly.

    def close_trade(self, trade, outcome, close_price, pnl_pct, bot):
        trade['status'] = 'CLOSED'
        trade['outcome'] = outcome
        trade['close_price'] = close_price
        trade['close_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade['pnl_pct'] = pnl_pct
        
        # Calculate balance and usage BEFORE adding to history
        # Calculate balance and usage BEFORE adding to history
        balance_before = self.calculate_balance()
        
        # Risk Calc
        risk_per_trade = trade.get('risk_pct', (config.CRYPTO_RISK_PER_TRADE if 'STOCK' not in self.market_tag else config.STOCK_RISK_PER_TRADE))
        risk_amt = balance_before * risk_per_trade
        
        entry = trade['entry']
        sl = trade['sl']
        
        if entry != sl:
            # Position Sizing
            dist_to_sl_pct = abs(entry - sl) / entry
            raw_position_value = risk_amt / dist_to_sl_pct
            
            dist_to_sl_pct = abs(entry - sl) / entry
            raw_position_value = risk_amt / dist_to_sl_pct
            
            if self.leverage > 1:
                 max_buying_power = balance_before * self.leverage
                 actual_position_val = min(raw_position_value, max_buying_power)
                 margin_used = actual_position_val / self.leverage
                 amount_used_display = margin_used
            else:
                 actual_position_val = min(raw_position_value, balance_before)
                 amount_used_display = actual_position_val
            
            qty = actual_position_val / entry
            
            # Realized PnL Amount
            if trade['side'] == 'LONG':
                pnl_amt = (close_price - entry) * qty
            else:
                pnl_amt = (entry - close_price) * qty
        else:
            actual_position_val = 0
            pnl_amt = 0
            
        balance_after = balance_before + pnl_amt
        
        self.active_trades.remove(trade)
        self.history.append(trade)
        self.save_trades()
        
        # Sync to Persistent Storage
        sheets.log_closed_trade(trade)
        
        # Send Alert
        market_display = self.market_tag.replace('_', '\\_')
        emoji = "✅" if outcome == 'WIN' else "❌"
        ist_now = utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
        balance_before = balance_after - pnl_amt
        
        # Calculate localized risk display
        risk_per_trade_display = f"{risk_per_trade * 100:.1f}%"
        
        msg = (
            f"{emoji} **TRADE CLOSED: {trade['symbol']}**\n"
            f"Result: {outcome}\n"
            f"📅 **Time**: {ist_now} IST\n"
            f"PnL: {pnl_pct*100:.2f}% ({self.currency}{pnl_amt:,.2f})\n\n"
            f"💰 **Portfolio Update ({market_display})**\n"
            f"Capital Before: {self.currency}{balance_before:,.2f}\n"
            f"Risk Allowed: {risk_per_trade_display} ({self.currency}{risk_amt:,.2f})\n"
            f"Position Size: {self.currency}{amount_used_display:,.2f} {'(Margin)' if self.leverage > 1 else ''}\n"
            f"Remaining Capital: {self.currency}{balance_after:,.2f}\n\n"
            f"Entry: {entry} | Exit: {close_price}"
        )
        
        # Route to PnL Channel
        channel_id = None
        if 'CRYPTO' in trade['market']:
            channel_id = config.TELEGRAM_CRYPTO_PNL_CHANNEL_ID
        elif trade['market'] == 'STOCK':
             channel_id = config.TELEGRAM_STOCK_PNL_CHANNEL_ID
             
        # Fallback to generic Log Channel or Signal Channel if PnL channel is missing
        if not channel_id:
            channel_id = config.TELEGRAM_LOG_CHANNEL_ID
        
        # Final Fallback: Send to the Main Signal Channel (so checking PnL is possible)
        if not channel_id:
             if 'CRYPTO' in trade['market']:
                channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID
             else:
                channel_id = config.TELEGRAM_STOCK_CHANNEL_ID

        if channel_id:
             asyncio.create_task(bot.send_message(chat_id=channel_id, text=msg, parse_mode='Markdown'))
        else:
             logger.info(f"Trade Closed ({outcome}): {trade['symbol']} (No Channel set)")

    def calculate_balance(self):
        """Calculates current balance based on initial capital and trade history (Compounding)."""
        balance = self.initial_capital
        
        if not self.history:
            return balance

        for t in self.history:
            try:
                # Handle CREDIT entries
                if t.get('side') == 'CREDIT':
                    credit = t.get('credit_amount', 0)
                    balance += credit
                    logger.debug(f"[{self.market_tag}] Applied Credit: {self.currency}{credit}, New balance: {self.currency}{balance:,.2f}")
                    continue
                    
                # Standard Risk Management Calculation
                risk_per_trade = t.get('risk_pct', 0.005)
                risk_amt = balance * risk_per_trade
                
                entry = t.get('entry', 0)
                sl = t.get('sl', 0)
                exit_price = t.get('close_price', 0)
                
                if entry == 0 or sl == 0 or exit_price == 0:
                    logger.warning(f"[{self.market_tag}] Skipping trade with zero values: {t.get('symbol')}")
                    continue

                if entry == sl: continue

                # Quantity
                dist_to_sl_pct = abs(entry - sl) / entry
                if dist_to_sl_pct == 0: continue
                
                raw_position_value = risk_amt / dist_to_sl_pct
                
                if self.leverage > 1:
                    max_buying_power = balance * self.leverage
                    actual_position_val = min(raw_position_value, max_buying_power)
                else:
                    actual_position_val = min(raw_position_value, balance)
                
                qty = actual_position_val / entry
                
                # Realized PnL
                if t['side'] == 'LONG':
                    pnl = (exit_price - entry) * qty
                else:
                    pnl = (entry - exit_price) * qty
                
                balance += pnl
                logger.debug(f"[{self.market_tag}] Trade {t.get('symbol')} closed: {t.get('outcome')}, PnL: {self.currency}{pnl:,.2f}, New balance: {self.currency}{balance:,.2f}")

            except Exception as e:
                logger.error(f"[{self.market_tag}] Error calculating balance for trade {t.get('symbol')}: {e}")
                
        return balance

    def check_balance_sufficiency(self):
        """Checks balance and adds credit if below minimum (Paper Trading Mode)."""
        balance = self.calculate_balance()
        
        if 'STOCK' not in self.market_tag:
            min_required = config.MIN_TRADE_AMOUNT_CRYPTO
            credit_amount = 5  # $5 credit
        else:
            min_required = 1000
            credit_amount = 1000  # ₹1000 credit
            
        if balance < min_required:
            # Add credit by inserting a "deposit" into history
            self.history.append({
                'id': f'CREDIT_{self.market_tag}_{int(datetime.now().timestamp())}',
                'symbol': 'CREDIT',
                'market': self.market_tag,
                'side': 'CREDIT',
                'entry': 0,
                'close_price': 0,
                'tp': 0,
                'sl': 0,
                'status': 'CREDIT',
                'outcome': 'CREDIT',
                'pnl_pct': 0,
                'credit_amount': credit_amount,
                'open_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'close_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_pct': 0
            })
            self.save_trades()
            logger.info(f"💰 Auto-Credit: Added {self.currency}{credit_amount} to {self.market_tag} portfolio (Balance was {self.currency}{balance:.2f})")
            balance += credit_amount
            
        return True, balance, min_required

    def get_stats(self):
        if not self.history:
             return f"[{self.market_tag}] No trades yet. Start: {self.currency}{self.initial_capital}"

        balance = self.calculate_balance()
        growth = ((balance - self.initial_capital) / self.initial_capital) * 100
        
        wins = len([t for t in self.history if t['outcome'] == 'WIN'])
        total = len(self.history)
        win_rate = (wins / total) * 100 if total > 0 else 0
        
        return (
            f"📈 **{self.market_tag}**\n"
            f"Balance: {self.currency}{balance:,.2f} ({growth:+.2f}%)\n"
            f"Wins: {wins}/{total} ({win_rate:.1f}%)\n"
        )
