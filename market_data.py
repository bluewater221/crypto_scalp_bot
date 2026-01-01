import ccxt
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import config
import logging
import asyncio
import kite_auth
import nse_client

logger = logging.getLogger(__name__)

# --- Exchange Setup ---
def get_crypto_exchange():
    """Initialize the Kraken exchange (public data, no API key needed)."""
    try:
        # Using Kraken - more cloud-friendly than Bybit/Binance
        exchange = ccxt.kraken({
            'enableRateLimit': True,
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

async def fetch_stock_data(symbol, timeframe=config.STOCK_TIMEFRAME, period='5d'):
    """Fetch Intraday data from Kite (Best), NSE (Backup), or Yahoo (Default)."""
    
    # 1. Try Kite (Best for Intraday)
    try:
        kite = kite_auth.KiteDataClient()
        if kite.active:
            # Run in thread to avoid blocking main loop
            df = await asyncio.to_thread(kite.fetch_ohlc, symbol, timeframe, 5 if period=='5d' else 1)
            if df is not None and not df.empty:
                return df
    except Exception as e:
        logger.warning(f"Kite fetch failed for {symbol}: {e}")
        
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

    try:
        # 3. yfinance Fallback (Reliable Intraday)
        # yfinance download is blocking, run in thread
        # yfinance download is blocking, run in thread
        df = await asyncio.to_thread(yf.download, tickers=symbol, period=period, interval=timeframe, progress=False)
        
        if df is None or df.empty:
            return None
            
        # Handle multi-index columns which occur in newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.reset_index(inplace=True)
        # Standardize column names to lowercase
        df.columns = [str(col).lower() for col in df.columns]
        
        # Map timestamp
        if 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif 'date' in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)
            
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
    except Exception as e:
        logger.error(f"Error calculating Stock Indicators: {e}")
        return df
