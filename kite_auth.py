import logging
import os
import config
from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class KiteDataClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KiteDataClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        
        self.kite = None
        self.active = False
        
        if config.KITE_API_KEY and config.KITE_ACCESS_TOKEN:
            try:
                self.kite = KiteConnect(api_key=config.KITE_API_KEY)
                self.kite.set_access_token(config.KITE_ACCESS_TOKEN)
                self.active = True
                logger.info("✅ Kite Connect Client Initialized (Read-Only)")
            except Exception as e:
                logger.error(f"Failed to init Kite Client: {e}")
        else:
            logger.info("ℹ️ Kite Credentials missing. Using yfinance fallback.")
            
        self._initialized = True

    def get_instrument_token(self, symbol):
        # Basic mapping - In production, you'd fetch the full instrument dump and cache it.
        # For now, we rely on the symbol being standard like "NSE:RELIANCE" or just "RELIANCE.NS" -> "NSE:RELIANCE"
        
        # We need to lookup instrument token. 
        # This is expensive to do every time. Ideally, we download instruments once on startup.
        # For simplicity in this script, we'll try to use the symbol string directly if allowed? 
        # No, Kite historical needs instrument_token.
        
        # Quick hack: Fetch instruments for NSE and search.
        try:
            instruments = self.kite.instruments("NSE")
            # symbol format: RELIANCE.NS -> RELIANCE
            tradingsymbol = symbol.replace('.NS', '').upper()
            
            for inst in instruments:
                if inst['tradingsymbol'] == tradingsymbol:
                    return inst['instrument_token']
        except Exception as e:
            logger.error(f"Error fetching token for {symbol}: {e}")
        return None

    def fetch_ohlc(self, symbol, interval, days=5):
        """
        Fetches historical data.
        interval: 'minute', '5minute', 'day'
        """
        if not self.active: return None
        
        try:
            token = self.get_instrument_token(symbol)
            if not token:
                logger.warning(f"Could not find Kite token for {symbol}")
                return None
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Map Config Interval to Kite Interval
            # config: '5m' -> Kite: '5minute'
            kite_interval = interval
            if interval == '5m': kite_interval = '5minute'
            elif interval == '1m': kite_interval = 'minute'
            elif interval == '1h': kite_interval = '60minute'
            
            records = self.kite.historical_data(token, from_date, to_date, kite_interval)
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            if df.empty: return None
            
            # Rename columns to match existing bot logic (date -> timestamp)
            df.rename(columns={'date': 'timestamp'}, inplace=True)
            
            # Ensure timezone is naive or consistent (Kite returns +0530)
            # Remove timezone to match yfinance style if needed or keep it.
            # yfinance returns naive or aware? Usually aware.
            
            return df
            
        except Exception as e:
            logger.error(f"Kite Data Fetch Error for {symbol}: {e}")
            return None
