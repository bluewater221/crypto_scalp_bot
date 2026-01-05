import datetime
import time
import logging
import gc
from flask import Blueprint, request, jsonify
import config
import telegram_handler
import utils
import trade_manager
# from bot import spot_mgr, future_mgr, stock_mgr # REMOVED to avoid circular import

# Blueprint Setup
webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

# Global Watchdog Timestamp
# 0 means no webhook received yet
last_webhook_time = 0

@webhook_bp.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle incoming signals from TradingView.
    """
    global last_webhook_time
    
    try:
        # 1. Payload Validation
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
        
        # 2. Security Check
        passphrase = data.get('passphrase')
        if passphrase != config.WEBHOOK_PASSPHRASE:
            logger.warning(f"⚠️ Webhook Access Denied: Incorrect Passphrase")
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
            
        # 3. Update Watchdog (This pauses local scanning)
        last_webhook_time = time.time()
        logger.info(f"📩 Webhook Received: Keeping Watchdog Awake.")

        # 4. Extract Signal Details
        ticker = data.get('ticker', 'UNKNOWN')
        exchange = data.get('exchange', 'UNKNOWN')
        
        # TradingView sends specific strategy payload
        strategy = data.get('strategy', {})
        action = strategy.get('action') # "buy" or "sell"
        market_pos = strategy.get('market_position') 
        
        bar = data.get('bar', {})
        close_price = bar.get('close', 0.0)
        
        if not action:
            return jsonify({'status': 'ignored', 'message': 'No action in strategy'}), 200

        # Normalize Signal for Bot Pipeline
        # We need to construct a signal dict compatible with telegram_handler and trade_manager
        
        side = 'LONG' if action.lower() in ['buy', 'long'] else 'SHORT'
        symbol = ticker # e.g. BTCUSDT or RELIANCE
        
        # Determine Market Type
        market_type = 'CRYPTO'
        if exchange == 'NSE' or '.NS' in symbol or symbol in config.STOCK_SYMBOLS:
            market_type = 'STOCK'
            if not symbol.endswith('.NS') and exchange == 'NSE':
                symbol = f"{symbol}.NS"
        
        logger.info(f"⚡ Triggger: {side} {symbol} @ {close_price}")

        # Construct Signal Object
        entry_price = float(close_price)
        
        # Simple Risk calc (Default 1% TP / 0.5% SL if not provided in payload)
        # Ideally TV payload sends SL/TP, but let's apply our config defaults
        if market_type == 'CRYPTO':
             stop_loss = entry_price * (1 - config.CRYPTO_STOP_LOSS) if side == 'LONG' else entry_price * (1 + config.CRYPTO_STOP_LOSS)
             take_profit = entry_price * (1 + config.CRYPTO_TAKE_PROFIT) if side == 'LONG' else entry_price * (1 - config.CRYPTO_TAKE_PROFIT)
             # mgr = future_mgr 
             risk_pct = config.CRYPTO_RISK_PER_TRADE
        else:
             stop_loss = entry_price * (1 - config.STOCK_STOP_LOSS) if side == 'LONG' else entry_price * (1 + config.STOCK_STOP_LOSS)
             take_profit = entry_price * (1 + config.STOCK_TAKE_PROFIT) if side == 'LONG' else entry_price * (1 - config.STOCK_TAKE_PROFIT)
             # mgr = stock_mgr
             risk_pct = config.STOCK_RISK_PER_TRADE

        signal = {
            'market': market_type,
            'symbol': symbol,
            'side': side,
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'setup': 'TradingView Webhook',
            'risk_pct': risk_pct,
            'timestamp': utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S'),
            'ai_confidence': 'N/A (Webhook)',
            'ai_reasoning': 'External Signal',
            'df': None # No dataframe
        }
        
        # 5. Execute & Notify
        # We need a context to send telegram message. 
        # But we are in Flask, not PTB context. 
        # Integration Challenge: Accessing the PTB Application instance from Flask.
        # Workaround: Using the global 'application' from bot.py might cause circular imports.
        # Better: telegram_handler.send_signal expects 'bot' object.
        # We can pass the 'bot' object during blueprint registration? 
        # Or Just Import it if initialized?
        
        # Let's Import 'application' from bot ONLY when needed to avoid circular import at module level?
        # Actually bot.py imports webhook_handler. 
        # We can inject the bot instance into the blueprint config or global var.
        
        # Quick Hack for Clean Architecture:
        # We will use a Callback function that bot.py sets.
        
        if pending_signals is not None:
             pending_signals.append(signal)
             logger.info(f"Signal queued. Queue size: {len(pending_signals)}")
        
        return jsonify({'status': 'success', 'timestamp': last_webhook_time}), 200

    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        gc.collect()

# Simple Queue for Bot to poll
# Structure: List of signal dicts
pending_signals = []
