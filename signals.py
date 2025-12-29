import logging
import asyncio
import pandas as pd
import config
import market_data
import utils
import sheets

logger = logging.getLogger(__name__)

async def analyze_crypto(exchange, symbol):
    """
    Analyzes a crypto symbol for RSI scalping signals.
    """
    df = await market_data.fetch_crypto_ohlcv(exchange, symbol)
    if df is None or df.empty:
        return None
    
    df = market_data.calculate_indicators_crypto(df)
    if 'rsi' not in df.columns:
        return None
        
    latest = df.iloc[-1]
    rsi = latest['rsi']
    close_price = latest['close']
    
    signal = None
    setup_type = ""
    
    if rsi < config.RSI_OVERSOLD:
        signal = 'LONG'
        setup_type = f'RSI Oversold ({rsi:.1f})'
        entry_price = close_price
        stop_loss = entry_price * (1 - config.CRYPTO_STOP_LOSS)
        take_profit = entry_price * (1 + config.CRYPTO_TAKE_PROFIT)
        
    elif rsi > config.RSI_OVERBOUGHT:
        signal = 'SHORT'
        setup_type = f'RSI Overbought ({rsi:.1f})'
        entry_price = close_price
        stop_loss = entry_price * (1 + config.CRYPTO_STOP_LOSS)
        take_profit = entry_price * (1 - config.CRYPTO_TAKE_PROFIT)

    if signal:
        signal_data = {
            'market': 'CRYPTO',
            'symbol': symbol,
            'side': signal,
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'setup': setup_type,
            'risk_pct': config.CRYPTO_RISK_PER_TRADE,
            'timestamp': utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S'),
            'df': df  # Pass dataframe for chart generation
        }
        # Log to Sheets
        sheets.log_signal(signal_data)
        return signal_data
    
    return None

async def analyze_stock(symbol):
    """
    Analyzes a stock symbol for EMA Crossover + Volume.
    """
    df = await market_data.fetch_stock_data(symbol)
    if df is None or df.empty:
        return None
        
    df = market_data.calculate_indicators_stock(df)
    
    # Need at least 2 rows for crossover check
    if len(df) < 2:
        return None
        
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    close_price = curr['close']
    
    # EMA Cross: 9 crosses above 21
    # Check if EMA9 > EMA21 NOW and EMA9 <= EMA21 BEFORE
    ema_fast_curr = curr['ema_fast']
    ema_slow_curr = curr['ema_slow']
    ema_fast_prev = prev['ema_fast']
    ema_slow_prev = prev['ema_slow']
    
    vol_curr = curr['volume']
    vol_avg = curr['vol_avg']
    
    signal = None
    setup_type = ""
    
    # Long Condition
    if (ema_fast_curr > ema_slow_curr) and (ema_fast_prev <= ema_slow_prev):
        # Volume Confirmation (> 2x Average)
        if vol_curr > (2 * vol_avg):
            signal = 'LONG' # Stocks usually Long only for Spot/Cash unless Intraday Equity? Assuming Intraday.
            setup_type = 'EMA Cross + Vol Spike'
            entry_price = close_price
            stop_loss = entry_price * (1 - config.STOCK_STOP_LOSS)
            take_profit = entry_price * (1 + config.STOCK_TAKE_PROFIT)
    
    if signal:
        signal_data = {
            'market': 'STOCK',
            'symbol': symbol,
            'side': signal,
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'setup': setup_type,
            'risk_pct': config.STOCK_RISK_PER_TRADE,
            'timestamp': utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S'),
            'df': df
        }
        sheets.log_signal(signal_data)
        return signal_data

    return None
