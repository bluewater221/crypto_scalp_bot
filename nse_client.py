import logging
import pandas as pd
from datetime import datetime, timedelta
import asyncio

# Attempt import, handle failure if not installed yet
try:
    from nsepython import equity_history
    NSE_PYTHON_AVAILABLE = True
except ImportError:
    NSE_PYTHON_AVAILABLE = False

logger = logging.getLogger(__name__)

class NSEDataClient:
    def __init__(self):
        if not NSE_PYTHON_AVAILABLE:
            logger.warning("nsepython library not found.")
    
    def fetch_ohlc(self, symbol, days=5):
        """
        Fetches historical data via nsepython.
        symbol: e.g. "RELIANCE" (without .NS)
        days: Number of days to look back
        """
        if not NSE_PYTHON_AVAILABLE: return None
        
        try:
            # Format Symbol: Remove .NS if present
            clean_symbol = symbol.replace('.NS', '').upper()
            
            # Dates
            end_date = datetime.now().strftime("%d-%m-%Y")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%d-%m-%Y")
            
            logger.info(f"Fetching NSE data for {clean_symbol} ({start_date} to {end_date})")
            
            # Run blocking call in thread
            # equity_history returns a list of dictionaries or similar
            # Series EQ is standard for stocks
            df = equity_history(clean_symbol, "EQ", start_date, end_date)
            
            if df is None or df.empty:
                logger.warning(f"NSEPython returned empty data for {clean_symbol}")
                return None
                
            # nsepython returns DataFrame usually?
            # Columns are typically: CH_TIMESTAMP, CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, CH_TRADE_LOW_PRICE, CH_CLOSING_PRICE, CH_TOT_TRADED_QTY
            
            # Handle standard NSE columns
            # Standardize names to: timestamp, open, high, low, close, volume
            
            rename_map = {
                'CH_TIMESTAMP': 'timestamp', 
                'CH_OPENING_PRICE': 'open',
                'CH_TRADE_HIGH_PRICE': 'high', 
                'CH_TRADE_LOW_PRICE': 'low',
                'CH_CLOSING_PRICE': 'close', 
                'CH_TOT_TRADED_QTY': 'volume'
            }
            
            # Filter just the columns we need if they exist
            cols_to_keep = [c for c in rename_map.keys() if c in df.columns]
            df = df[cols_to_keep].copy()
            df.rename(columns=rename_map, inplace=True)
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d") # Format might vary
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # NSEPython often returns EOD data mostly? 
            # equity_history is usually daily data. 
            # Does user need Intraday?
            # nsepython doesn't easily support 1-minute intraday history publicly without heavy scraping.
            # YFinance provides 1m/5m intraday.
            # If user wants SCALPING (5m charts), daily data is useless for EMA crossover signals on 5m.
            
            # CHECK: Does equity_history give intraday? No, usually EOD.
            # If bot needs 5m candles, NSEPython might NOT be suitable unless "intraday" function exists.
            
            # Let's check nse_fetch logic or similar.
            # Most free NSE scrapers only give EOD history or Live Quote (snapshot).
            # Live Quote is useful for current price, but not for EMA history.
            
            # Pivot: If NSEPython is EOD only, it CANNOT replace YFinance for 5m scalping.
            # I must check if I can get intraday.
            
            logger.warning("NSEPython equity_history is typically Daily data. Checking if useful for scalping...")
            # If we need 5m bars, we might be stuck with YFinance or Kite/Upstox.
            # However, let's return what we have. If it's daily, the bot might use it for Daily Trend?
            # But signals.py uses 5m.
            
            # For now, return DF. If it's daily data (one row per day), it won't work for 5m scalping logic which calls signals.py.
            # We'll see.
            
            return df
            
        except Exception as e:
            logger.error(f"NSEPython Error for {clean_symbol}: {e}")
            return None
