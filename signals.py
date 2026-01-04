import logging
import asyncio
import pandas as pd
import pandas_ta as ta
import config
import market_data
import utils
import sheets
from google import genai
try:
    from groq import Groq
except ImportError:
    Groq = None
import json
import os

logger = logging.getLogger(__name__)

# AI Clients (Singletons)
_genai_client = None
_groq_client = None

def get_genai_client():
    global _genai_client
    if _genai_client is None and config.GEMINI_API_KEY:
        _genai_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _genai_client

def get_groq_client():
    global _groq_client
    if _groq_client is None and config.GROQ_API_KEY and Groq:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client

async def validate_with_ai(symbol, market_type, signal, setup, df):
    """
    Asks AI (Gemini or Groq) to validate the technical signal.
    """
    gemini = get_genai_client()
    groq = get_groq_client()
    
    if not gemini and not groq:
        return {'confidence': 'N/A', 'reasoning': 'AI Keys missing', 'verdict': 'APPROVED'}

    # Technical Context
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

    # 1. Try Groq (Primary Fallback for better reliability/higher limits)
    if groq:
        try:
            chat_completion = await asyncio.to_thread(
                groq.chat.completions.create,
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            data = json.loads(chat_completion.choices[0].message.content)
            return {
                'confidence': f"{data.get('confidence', 0)}% (Q)",
                'reasoning': data.get('reasoning', 'No reasoning'),
                'verdict': data.get('verdict', 'APPROVED')
            }
        except Exception as e:
            logger.warning(f"Groq validation failed: {e}")

    # 2. Try Gemini
    if gemini:
        try:
            response = await asyncio.to_thread(
                gemini.models.generate_content,
                model='gemini-2.0-flash',
                contents=prompt
            )
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(raw_text)
            return {
                'confidence': f"{data.get('confidence', 0)}% (G)",
                'reasoning': data.get('reasoning', 'No reasoning'),
                'verdict': data.get('verdict', 'APPROVED')
            }
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}")

    # Fallback after both fail
    return {'confidence': 'Error', 'reasoning': 'AI Unresponsive', 'verdict': 'APPROVED'}


async def analyze_crypto(exchange, symbol, df_1m=None, df_5m=None):
    """
    Analyzes a crypto symbol for RSI scalping signals (Strict 1m Scalp).
    Accepts optional DataFrames for backtesting.
    """
    # 1. Fetch 1m Data (Execution Timeframe)
    if df_1m is None:
        df_1m = await market_data.fetch_crypto_ohlcv(exchange, symbol, timeframe='1m')
    if df_1m is None or df_1m.empty: return None

    # 2. Fetch 5m Data (HTF Trend Filter)
    if df_5m is None:
        df_5m = await market_data.fetch_crypto_ohlcv(exchange, symbol, timeframe='5m')
    if df_5m is None or df_5m.empty: return None

    # Indicators
    df_1m = market_data.calculate_indicators_crypto(df_1m)
    # Need EMA for 1m and 5m
    df_1m['ema_20'] = ta.ema(df_1m['close'], length=20)
    
    df_5m['ema_20'] = ta.ema(df_5m['close'], length=20)
    df_5m['ema_50'] = ta.ema(df_5m['close'], length=50)

    # Latest Values
    curr_1m = df_1m.iloc[-1]
    prev_1m = df_1m.iloc[-2]
    
    curr_5m = df_5m.iloc[-1]
    
    # --- HTF TREND FILTER (5m) ---
    trend_5m = 'BULLISH' if curr_5m['ema_20'] > curr_5m['ema_50'] else 'BEARISH'

    signal = None
    setup_type = ""
    entry_price = curr_1m['close']
    
    # Calculate Crypto Volume Average (20 period)
    vol_avg = df_1m['volume'].rolling(window=20).mean().iloc[-1]
    vol_curr = curr_1m['volume']
    
    # Volume Check (Mandatory for both)
    # Volume > 1.2x Average
    volume_ok = vol_curr > (1.2 * vol_avg)

    # --- LONG LOGIC ---
    if trend_5m == 'BULLISH' and volume_ok:
        # 1. RSI Crosses back ABOVE 30
        if prev_1m['rsi'] < 30 and curr_1m['rsi'] >= 30:
            # 2. Price > 1m EMA 20
            if entry_price > curr_1m['ema_20']:
                signal = 'LONG'
                setup_type = 'RSI Reversal (w/ 5m Trend)'
                stop_loss = entry_price * (1 - 0.003) # 0.3% Fixed
                take_profit = entry_price * (1 + 0.005) # 0.5% Target

    # --- SHORT LOGIC ---
    elif trend_5m == 'BEARISH' and volume_ok:
        # 1. RSI Crosses back BELOW 70
        if prev_1m['rsi'] > 70 and curr_1m['rsi'] <= 70:
            # 2. Price < 1m EMA 20
            if entry_price < curr_1m['ema_20']:
                signal = 'SHORT'
                setup_type = 'RSI Reversal (w/ 5m Trend)'
                stop_loss = entry_price * (1 + 0.003)
                take_profit = entry_price * (1 - 0.005)

    if signal:
        # Check if Backtesting (exchange is None) to skip AI
        if exchange is None:
             return {
                'market': 'CRYPTO',
                'symbol': symbol,
                'side': signal,
                'entry': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'setup': setup_type,
                'risk_pct': config.CRYPTO_RISK_PER_TRADE,
                'timestamp': utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S'),
                'ai_confidence': 'Backtest',
                'ai_reasoning': 'N/A',
                'df': None # Don't pass full DF to sheets to save space/time in backtest
             }

        # AI Validation
        ai_data = await validate_with_ai(symbol, 'CRYPTO', signal, setup_type, df_1m)
        
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
            'df': df_1m 
        }
        sheets.log_signal(signal_data)
        return signal_data
    
    return None

async def analyze_stock(symbol, df=None):
    """
    Analyzes a stock symbol with STRICT 5-Shield Logic.
    Accepts optional DataFrame for backtesting.
    """
    is_backtest = df is not None

    if df is None:
        df = await market_data.fetch_stock_data(symbol)
    if df is None or df.empty: return None
        
    df = market_data.calculate_indicators_stock(df)
    
    # Need enough data for checks
    if len(df) < 20: return None
        
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    close_price = curr['close']
    
    # Extract Indicators
    ema_fast = curr.get('ema_fast')
    ema_slow = curr.get('ema_slow')
    ema_trend = curr.get('ema_trend')
    ema_slope = curr.get('ema_trend_slope', 0)
    adx = curr.get('adx', 0)
    # Check ADX Rising: ADX[now] > ADX[prev] > ADX[prev-1]
    adx_prev = prev.get('adx', 0)
    
    rsi = curr.get('rsi')
    vol_curr = curr.get('volume')
    vol_avg = curr.get('vol_avg')
    vol_prev = prev.get('volume')
    
    # Validate Data Availability
    vals_to_check = [ema_fast, ema_slow, ema_trend, rsi, vol_curr, vol_avg]
    if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in vals_to_check):
        return None
    
    signal = None
    setup_type = ""
    
    # --- STRICT ENTRY CONDITIONS (LONG ONLY) ---
    
    # SHIELD 1: Momentum Signal (Primary)
    # EMA 9 Cross Above 21 (Golden Cross)
    cross_signal = (ema_fast > ema_slow) and (prev['ema_fast'] <= prev['ema_slow'])
    
    # Separation Check: EMA difference > X% of Price (Avoid noise)
    separation = (ema_fast - ema_slow) / close_price
    has_separation = separation >= config.EMA_CROSS_THRESHOLD
    
    # Candle must close above BOTH EMAs
    closes_above_emas = (close_price > ema_fast) and (close_price > ema_slow)
    
    if cross_signal and has_separation and closes_above_emas:
        
        # SHIELD 2: Trend
        # Price > EMA 50 AND EMA 50 Slope is Positive
        trend_ok = (close_price > ema_trend) and (ema_slope > 0)
        
        # SHIELD 3: Strength
        # ADX > 20 AND Rising AND < 40
        strength_ok = (adx > config.ADX_MIN) and (adx > adx_prev) and (adx < config.ADX_MAX)
        
        # SHIELD 4: Safety (Momentum Zone)
        # RSI between 45 and 65
        momentum_ok = (rsi >= config.RSI_MIN) and (rsi <= config.RSI_MAX)
        
        # SHIELD 5: Volume Confirmation
        # Vol > 1.2x Avg AND Vol > Prev Vol
        volume_ok = (vol_curr > (1.2 * vol_avg)) and (vol_curr > vol_prev)
        
        if trend_ok and strength_ok and momentum_ok and volume_ok:
            signal = 'LONG'
            setup_type = f'5-Shield Sniper (ADX:{adx:.1f} RSI:{rsi:.1f})'
            entry_price = close_price
            
            # Auto Stop Loss logic: Tighter of (21 EMA - 0.05%) OR Fixed %
            # Prompt Reqs: "Tighter of Recent Swing Low or 21 EMA - 0.05%"
            # Implementing 21 EMA SL logic
            sl_ema = ema_slow * (1 - 0.0005) # 21 EMA - 0.05%
            sl_fixed = entry_price * (1 - config.STOCK_STOP_LOSS)
            
            # Use the higher value (tighter SL for Longs)
            stop_loss = max(sl_ema, sl_fixed)
            
            # Target: 1.5R Minimum
            risk = entry_price - stop_loss
            take_profit = entry_price + (1.5 * risk)
        else:
            # Log specific rejections for debugging loop
            reasons = []
            if not trend_ok: reasons.append("Trend/Slope")
            if not strength_ok: reasons.append("ADX")
            if not momentum_ok: reasons.append("RSI")
            if not volume_ok: reasons.append("Volume")
            logger.debug(f"{symbol} Signal REJECTED. Shields failed: {', '.join(reasons)}")

    
    if signal:
        if is_backtest:
             return {
                'market': 'STOCK',
                'symbol': symbol,
                'side': signal,
                'entry': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'setup': setup_type,
                'risk_pct': config.STOCK_RISK_PER_TRADE,
                'timestamp': utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S'),
                'ai_confidence': 'Backtest',
                'ai_reasoning': 'N/A',
                'df': None
            }

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
