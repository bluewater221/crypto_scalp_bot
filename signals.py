import logging
import asyncio
import pandas as pd
import config
import market_data
import utils
import sheets
import google.generativeai as genai
import json
import os

logger = logging.getLogger(__name__)

async def validate_with_ai(symbol, market_type, signal, setup, df):
    """
    Asks Gemini to validate the technical signal.
    """
    if not config.GEMINI_API_KEY:
        return {'confidence': 'N/A', 'reasoning': 'AI Key missing'}

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Prepare Technical Context (Last 5 candles)
        recent_data = df.tail(5).to_string()
        
        prompt = (
            f"Act as a Senior Trading Analyst. Validate this scalping signal:\n"
            f"Asset: {symbol} ({market_type})\n"
            f"Signal: {signal}\n"
            f"Setup: {setup}\n\n"
            f"Recent Price Action (OHLCV + Indicators):\n{recent_data}\n\n"
            f"Analyze the Trend, Momentum (RSI), and Volume profile.\n"
            f"Return ONLY a JSON object with keys:\n"
            f"- confidence (0-100 score, integer)\n"
            f"- reasoning (concise explanation, max 20 words)\n"
            f"- verdict (APPROVED or REJECTED)"
        )
        
        # Run in thread to not block async loop
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        # Clean JSON
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw_text)
        
        return {
            'confidence': f"{data.get('confidence', 0)}%",
            'reasoning': data.get('reasoning', 'No reasoning'),
            'verdict': data.get('verdict', 'APPROVED') # Default to approve if unsure
        }
        
    except Exception as e:
        logger.error(f"AI Validation Failed: {e}")
        return {'confidence': 'Error', 'reasoning': 'AI Unresponsive', 'verdict': 'APPROVED'}


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
        # AI Validation
        ai_data = await validate_with_ai(symbol, 'CRYPTO', signal, setup_type, df)
        
        if ai_data.get('verdict') == 'REJECTED':
            logger.info(f"🚫 AI Rejected Signal for {symbol}: {ai_data['reasoning']}")
            return None
            
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
            'ai_confidence': ai_data['confidence'],
            'ai_reasoning': ai_data['reasoning'],
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
        # AI Validation
        ai_data = await validate_with_ai(symbol, 'STOCK', signal, setup_type, df)
        
        if ai_data.get('verdict') == 'REJECTED':
            logger.info(f"🚫 AI Rejected Signal for {symbol}: {ai_data['reasoning']}")
            return None

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
            'ai_confidence': ai_data['confidence'],
            'ai_reasoning': ai_data['reasoning'],
            'df': df
        }
        sheets.log_signal(signal_data)
        return signal_data

    return None
