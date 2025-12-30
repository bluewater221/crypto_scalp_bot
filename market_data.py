import ccxt
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import config
import logging
import asyncio

logger = logging.getLogger(__name__)

# --- Exchange Setup ---
def get_crypto_exchange():
    """Initialize the Bybit exchange (public data, no API key needed)."""
    try:
        # Using Bybit instead of Binance - works globally without API restrictions
        exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}  # Use spot for simple price data
        })
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

async def fetch_stock_data(symbol, timeframe=config.STOCK_TIMEFRAME, period='1d'):
    """Fetch Intraday data from Yahoo Finance."""
    try:
        # yfinance download is blocking, run in thread
        df = await asyncio.to_thread(yf.download, tickers=symbol, period=period, interval=timeframe, progress=False, multi_level_index=False)
        
        if df.empty:
            return None
            
        df.reset_index(inplace=True)
        # Rename columns to standard lowercase
        df.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {e}")
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
        
        # Volume Moving Average (20 period)
        df['vol_avg'] = ta.sma(df['volume'], length=20)
        
        return df
    except Exception as e:
        logger.error(f"Error calculating Stock Indicators: {e}")
        return df
