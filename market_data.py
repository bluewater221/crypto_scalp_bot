import ccxt
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import config
import logging
import asyncio

import nse_client
import requests

logger = logging.getLogger(__name__)

# --- Exchange Setup ---
def get_crypto_exchange():
    """Initialize the Binance exchange (Singapore server allows this)."""
    try:
        # Using Binance - Best liquidity, works in Singapore
        exchange_config = {
            'enableRateLimit': True,
        }
        if config.BINANCE_API_KEY and config.BINANCE_SECRET_KEY:
            exchange_config['apiKey'] = config.BINANCE_API_KEY
            exchange_config['secret'] = config.BINANCE_SECRET_KEY
            
        exchange = ccxt.binance(exchange_config)
        return exchange
    except Exception as e:
        logger.error(f"Error initializing crypto exchange: {e}")
        return None

# --- Data Fetching ---
async def fetch_crypto_ohlcv(exchange, symbol, timeframe=config.CRYPTO_TIMEFRAME, limit=100):
    """Fetch OHLCV data from Binance (Async wrapper effectively)."""
    try:
        # Check if exchange is async or sync. Using sync ccxt method in async loop is blocking.
        # Ideally use ccxt.async_support but for simplicity we run in executor if needed.
        # For now, we assume low frequency enough that direct call is okay, or wrap in to_thread.
        bars = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching crypto data for {symbol}: {e}")
        return None

async def fetch_stock_data(symbol, timeframe=config.STOCK_TIMEFRAME, period='5d'):
    """Fetch Intraday data from Kite (Best), NSE (Backup), or Yahoo (Default)."""
    
    # 1. Try Kite (Removed temporarily)

        
    # 2. Try NSEPython (Experimental - Often Daily only)
    # Scalping needs 5m data. NSEPython usually gives EOD. 
    # Validating if we should use it for 'Intraday'?
    # Usually no. We skip it for timeframe='5m' unless we solve intraday scraping.
    # For now, strictly falling back to YFinance for 5m which DOES support it.
    
    # try:
    #     nse = nse_client.NSEDataClient()
    #     if timeframe == '1d': # Only use for daily
    #          df = await asyncio.to_thread(nse.fetch_ohlc, symbol, 5)
    #          if df is not None and not df.empty: return df
    # except: pass

    # 3. yfinance Improvement (Session + Retry + Ticker.history)
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
             # Add random delay before request to mitigate rate limits
            await asyncio.sleep(base_delay * (attempt + 1))
            
            # Use Ticker.history with a custom session if possible, or just default
            # Ticker.history is often more reliable for single symbols than download
            
            def get_data_sync():
                ticker = yf.Ticker(symbol)
                # history() doesn't officially support session in all versions, 
                # but we can try to rely on Ticker's internal handling + delays.
                return ticker.history(period=period, interval=timeframe)

            df = await asyncio.to_thread(get_data_sync)
            
            if df is None or df.empty:
                logger.warning(f"Attempt {attempt+1}: No data for {symbol}")
                continue

            # Standardize Columns
            df.reset_index(inplace=True)
            df.columns = [str(col).lower() for col in df.columns]
            
            # Rename for consistency
            rename_map = {
                'date': 'timestamp', 
                'datetime': 'timestamp',
                'stock splits': 'splits'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Ensure Timestamp is localized/naive consistent if needed (usually fine)
            
            # Allow 'adj close' if 'close' missing (common in yf)
            if 'close' not in df.columns and 'adj close' in df.columns:
                 df['close'] = df['adj close']

            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                 continue

            return df

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                logger.warning(f"Rate limited on {symbol} (Attempt {attempt+1}/{max_retries}). Retrying...")
                await asyncio.sleep(5) # Extra wait
            elif "delisted" in error_str:
                logger.warning(f"Ticker {symbol} seems delisted.")
                return None
            else:
                 logger.error(f"Error fetching {symbol}: {e}")
                 # Don't retry on unknown errors to avoid loops
                 break
    
    return None

# --- Indicator Calculation ---
def calculate_indicators_crypto(df):
    """Calculate RSI for Crypto."""
    try:
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        return df
    except Exception as e:
        logger.error(f"Error calculating Crypto Indicators: {e}")
        return df

def calculate_indicators_stock(df):
    """Calculate EMAs and Volume for Stocks."""
    try:
        df['ema_fast'] = ta.ema(df['close'], length=config.EMA_FAST)
        df['ema_slow'] = ta.ema(df['close'], length=config.EMA_SLOW)
        
        # --- Safety Indicators ---
        # 1. Trend Filter: EMA 50
        df['ema_trend'] = ta.ema(df['close'], length=50)
        
        # 2. Momentum Filter: RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # 3. Strength Filter: ADX (Requires High, Low, Close)
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx_df is not None and not adx_df.empty:
            # ADX return columns: ADX_14, DMP_14, DMN_14. We just want ADX.
            df['adx'] = adx_df[adx_df.columns[0]] # usually the first column is ADX
        
        # --- Advanced Safety (Slope) ---
        # Calculate Slope of EMA 50 over last 10 candles
        # Slope = (Current EMA - EMA 10 bars ago) / EMA 10 bars ago
        df['ema_trend_slope'] = (df['ema_trend'] - df['ema_trend'].shift(10)) / df['ema_trend'].shift(10) * 100
        
        # EMA 200 (Optional Safety)
        df['ema_200'] = ta.ema(df['close'], length=200)

        # Volume Moving Average (20 period)
        df['vol_avg'] = ta.sma(df['volume'], length=20)
        
        return df
        return df
    except Exception as e:
        logger.error(f"Error calculating Stock Indicators: {e}")
        return df

# --- Market Pulse (Free APIs) ---
def get_fear_and_greed_index():
    """Fetches Crypto Fear & Greed Index from Alternative.me."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            item = data['data'][0]
            return {
                'value': int(item['value']),
                'value_classification': item['value_classification']
            }
    except Exception as e:
        logger.error(f"Error fetching Fear & Greed Index: {e}")
    return {'value': 0, 'value_classification': 'Unknown'}

async def get_market_status():
    """Fetches Nifty 50 Trend from Yahoo Finance."""
    try:
        # Run in thread as yfinance can be blocking
        ticker = await asyncio.to_thread(yf.Ticker, "^NSEI")
        hist = await asyncio.to_thread(ticker.history, period="1d")
        
        if not hist.empty:
            last_close = float(hist["Close"].iloc[-1])
            open_price = float(hist["Open"].iloc[-1])
            
            change = last_close - open_price
            pct_change = (change / open_price) * 100
            
            trend = "BULLISH" if change > 0 else "BEARISH"
            
            return {
                'symbol': 'NIFTY 50',
                'price': last_close,
                'change': change,
                'pct_change': pct_change,
                'trend': trend
            }
    except Exception as e:
        logger.error(f"Error fetching Market Status: {e}")
    
    return None

async def get_usdinr_status():
    """Fetches USD/INR Price & Trend from Yahoo Finance."""
    try:
        # Run in thread as yfinance can be blocking
        ticker = await asyncio.to_thread(yf.Ticker, "INR=X")
        hist = await asyncio.to_thread(ticker.history, period="1d")
        
        if not hist.empty:
            last_close = float(hist["Close"].iloc[-1])
            open_price = float(hist["Open"].iloc[-1])
            
            change = last_close - open_price
            pct_change = (change / open_price) * 100
            
            trend = "Appreciating" if change < 0 else "Depreciating" # INR vs USD
            
            return {
                'price': last_close,
                'change': change,
                'pct_change': pct_change,
                'trend': trend
            }
    except Exception as e:
        logger.error(f"Error fetching USD/INR: {e}")
    
    return None
