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

async def validate_with_ai(symbol, market_type, signal, setup, df, context_summary=None):
    """
    Asks AI (Gemini or Groq) to validate the technical signal.
    """
    gemini = get_genai_client()
    groq = get_groq_client()
    
    if not gemini and not groq:
        return {'confidence': 'N/A', 'reasoning': 'AI Keys missing', 'verdict': 'APPROVED'}

    # Technical Context
    # Technical Context
    if df is not None:
        recent_data = df.tail(5).to_string()
    elif context_summary:
        recent_data = context_summary
    else:
        recent_data = "Data unavailable (Zero-Pandas Mode)"
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
                model='gemini-flash-latest',
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

    # 3. Try OpenRouter (Final Fallback)
    openrouter_key = config.OPENROUTER_API_KEY
    if openrouter_key:
        try:
             # Standard OpenAI-format call
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model="deepseek/deepseek-r1-distill-llama-70b", # Cost effective, high IQ
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                   "HTTP-Referer": "https://github.com/crypto-scalp-bot", 
                   "X-Title": "CryptoScalpBot"
                 },
                response_format={"type": "json_object"}
            )
            data = json.loads(completion.choices[0].message.content)
            return {
                'confidence': f"{data.get('confidence', 0)}% (OR)",
                'reasoning': data.get('reasoning', 'No reasoning'),
                'verdict': data.get('verdict', 'APPROVED')
            }
        except Exception as e:
            logger.warning(f"OpenRouter validation failed: {e}")

    # Fallback after all fail
    return {'confidence': 'Error', 'reasoning': 'AI Unresponsive', 'verdict': 'APPROVED'}


async def analyze_crypto(exchange, symbol, raw_candles=None, raw_htf_candles=None):
    """
    Analyzes a crypto symbol for RSI scalping signals.
    Uses config.CRYPTO_TIMEFRAME for execution (e.g., 5m) and 15m for Trend.
    ZERO-PANDAS IMPLEMENTATION (List/NumPy only).
    """
    # 1. Fetch Execution Data (e.g. 5m)
    if raw_candles is None:
        raw_candles = await market_data.fetch_crypto_candles_raw(exchange, symbol, timeframe=config.CRYPTO_TIMEFRAME)
    if not raw_candles or len(raw_candles) < 50: 
        logger.debug(f"{symbol}: Not enough execution data ({len(raw_candles) if raw_candles else 0})")
        return None

    # 2. Fetch HTF Data (Trend Filter - 15m)
    if raw_htf_candles is None:
        # If execution is 5m, use 15m for trend. If execution is 1m, maybe 5m.
        # Hardcoding 15m as 'HTF' for the 5m Strategy (Option C).
        htf_frame = '15m'
        raw_htf_candles = await market_data.fetch_crypto_candles_raw(exchange, symbol, timeframe=htf_frame)
    if not raw_htf_candles or len(raw_htf_candles) < 50: 
        logger.debug(f"{symbol}: Not enough HTF data ({len(raw_htf_candles) if raw_htf_candles else 0})")
        return None

    # Extract Lists
    
    # Execution Data
    closes = [x[4] for x in raw_candles]
    vols = [x[5] for x in raw_candles]
    
    # HTF Data
    highs_htf = [x[2] for x in raw_htf_candles]
    lows_htf = [x[3] for x in raw_htf_candles]
    closes_htf = [x[4] for x in raw_htf_candles]
    vols_htf = [x[5] for x in raw_htf_candles]

    # --- Indicators ---
    
    # Execution Indicators
    rsi_curr = utils.calculate_rsi(closes, period=config.RSI_PERIOD)
    rsi_series = utils.calculate_rsi_series(closes, period=config.RSI_PERIOD) # For lookback
    
    # Vol Spike
    vol_curr = vols[-1]
    vol_ma_20 = utils.calculate_sma(vols, period=20)

    # HTF Indicators (Trend)
    ema_20_htf = utils.calculate_ema(closes_htf, period=20)
    ema_50_htf = utils.calculate_ema(closes_htf, period=50)
    vwap_htf = utils.calculate_vwap(highs_htf, lows_htf, closes_htf, vols_htf)
    
    # Current Close
    close_curr = closes[-1]
    
    # --- HTF TREND & CONFIRMATION FILTER ---
    if ema_20_htf is None or ema_50_htf is None: return None
    
    trend_htf = 'BULLISH' if ema_20_htf > ema_50_htf else 'BEARISH'
    
    # VWAP Filter (Using Latest)
    price_vs_vwap = 'ABOVE' if close_curr > vwap_htf else 'BELOW'
    
    rsi_curr = rsi_series[-1]

    # Lookback logic
    valid_signal_found = False
    
    lookback = 10
    for i in range(1, lookback + 1):
        idx_curr = -i
        idx_prev = -(i + 1)
        
        if abs(idx_prev) > len(rsi_series): break
        
        r_curr = rsi_series[idx_curr]
        r_prev = rsi_series[idx_prev]
        
        v_c = vols[idx_curr]
        v_ma_val = utils.calculate_sma(vols[:idx_curr], period=20)
        
        # Check volume spike only if required by config
        v_spike = True
        if config.REQUIRE_VOLUME_SPIKE:
            v_spike = v_c > v_ma_val if v_ma_val else False
        
        # Determine specific signal time logic
        # LONG
        if trend_htf == 'BULLISH' and price_vs_vwap == 'ABOVE' and v_spike:
            if r_prev < config.RSI_OVERSOLD and r_curr >= config.RSI_OVERSOLD:
                signal = 'LONG'
                setup_type = f'RSI_Reversal_VWAP_Trend (Candle -{i})'
                entry_price = closes[idx_curr]
                stop_loss = entry_price * (1 - config.CRYPTO_STOP_LOSS)
                take_profit = entry_price * (1 + config.CRYPTO_TAKE_PROFIT)
                valid_signal_found = True
                break
            else:
                # Debug logging for rejection
                logger.debug(f"{symbol} C-{i}: T={trend_htf} V={price_vs_vwap} S={v_spike} | RSI {r_prev:.1f}->{r_curr:.1f} | REJECTED: RSI Cond")
        
        # SHORT
        elif trend_htf == 'BEARISH' and price_vs_vwap == 'BELOW' and v_spike:
            if r_prev > config.RSI_OVERBOUGHT and r_curr <= config.RSI_OVERBOUGHT:
                signal = 'SHORT'
                setup_type = f'RSI_Reversal_VWAP_Trend (Candle -{i})'
                entry_price = closes[idx_curr]
                stop_loss = entry_price * (1 + config.CRYPTO_STOP_LOSS)
                take_profit = entry_price * (1 - config.CRYPTO_TAKE_PROFIT)
                valid_signal_found = True
                break
            else:
                 logger.debug(f"{symbol} C-{i}: T={trend_htf} V={price_vs_vwap} S={v_spike} | RSI {r_prev:.1f}->{r_curr:.1f} | REJECTED: RSI Cond")
        else:
             logger.debug(f"{symbol} C-{i}: T={trend_htf} V={price_vs_vwap} S={v_spike} | RSI {r_prev:.1f}->{r_curr:.1f} | REJECTED: Setup Cond")

    if valid_signal_found:
        pass # Signal set variables above
    else:
        signal = None

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
                'df': None 
             }

        # AI Validation
        # NOTE: validate_with_ai expects a dataframe for formatted printing.
        # We need to construct a lightweight string representation instead of passing full DF.
        # Or just pass an empty df or skip.
        # Let's mock a simple dict for context.
        
        # Simple context string
        context_str = f"Last 5 Candles (Close): {closes[-5:]} | RSI(14): {rsi_curr:.2f} | Trend: {trend_htf} | VWAP: {price_vs_vwap} | Volume Spike: {v_spike}"
        
        ai_data = await validate_with_ai(symbol, 'CRYPTO', signal, setup_type, None, context_summary=context_str) # Passing Context String
        
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
            'df': None
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
        
    # Lookback loop for Stocks (Check last 4 candles)
    if len(df) < 5: return None
    
    signal = None
    
    for i in range(1, 5):
        # Index -i is Candidate, -(i+1) is Prev
        curr = df.iloc[-i]
        prev = df.iloc[-(i+1)]
        
        close_price = curr['close']
        
        # Extract Indicators for this candle
        ema_fast = curr.get('ema_fast')
        ema_slow = curr.get('ema_slow')
        ema_trend = curr.get('ema_trend')
        ema_slope = curr.get('ema_trend_slope', 0)
        adx = curr.get('adx', 0)
        adx_prev = prev.get('adx', 0)
        
        rsi = curr.get('rsi')
        vol_curr = curr.get('volume')
        vol_avg = curr.get('vol_avg')
        vol_prev = prev.get('volume')
        
        vals_to_check = [ema_fast, ema_slow, ema_trend, rsi, vol_curr, vol_avg]
        if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in vals_to_check):
            continue

        # SHIELD 1: Momentum Signal (Primary)
        cross_signal = (ema_fast > ema_slow) and (prev['ema_fast'] <= prev['ema_slow'])
        separation = (ema_fast - ema_slow) / close_price
        has_separation = separation >= config.EMA_CROSS_THRESHOLD
        closes_above_emas = (close_price > ema_fast) and (close_price > ema_slow)
        
        if cross_signal and has_separation and closes_above_emas:
            trend_ok = (close_price > ema_trend) and (ema_slope > 0)
            strength_ok = (adx > config.ADX_MIN) and (adx > adx_prev) and (adx < config.ADX_MAX)
            momentum_ok = (rsi >= config.RSI_MIN) and (rsi <= config.RSI_MAX)
            volume_ok = (vol_curr > (1.2 * vol_avg)) and (vol_curr > vol_prev)
            
            if trend_ok and strength_ok and momentum_ok and volume_ok:
                signal = 'LONG'
                setup_type = f'5-Shield Sniper (Candle -{i})'
                entry_price = close_price
                sl_ema = ema_slow * (1 - 0.0005)
                sl_fixed = entry_price * (1 - config.STOCK_STOP_LOSS)
                stop_loss = max(sl_ema, sl_fixed)
                risk = entry_price - stop_loss
                take_profit = entry_price + (1.5 * risk)
                break # Stop at most recent signal
            else:
                reasons = []
                if not trend_ok: reasons.append("Trend/Slope")
                if not strength_ok: reasons.append("ADX")
                if not momentum_ok: reasons.append("RSI")
                if not volume_ok: reasons.append("Volume")
                logger.debug(f"{symbol} Candle -{i} Signal REJECTED. Shields failed: {', '.join(reasons)}")

    
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
            'df': None # Memory Optimization: Dropped DataFrame
        }
        sheets.log_signal(signal_data)
        
        # Explicit cleanup
        del df
        
        return signal_data

    # Cleanup if no signal
    del df
    return None
