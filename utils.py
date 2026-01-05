import pytz
from datetime import datetime
import config
import numpy as np

def get_ist_time():
    """Returns current time in IST."""
    tz = pytz.timezone(config.TIMEZONE_STR)
    return datetime.now(tz)

def is_market_open(market_type='CRYPTO'):
    """Check if market is open based on config hours."""
    now_ist = get_ist_time()
    current_hour = now_ist.hour
    current_minute = now_ist.minute
    
    if market_type == 'CRYPTO':
        # 9 AM to 11 PM
        return config.CRYPTO_MARKET_OPEN <= current_hour < config.CRYPTO_MARKET_CLOSE
        
    elif market_type == 'STOCK':
        # Check Weekday (Mon=0, Sun=6)
        if now_ist.weekday() >= 5: # Saturday (5) or Sunday (6)
            return False

        # 9:15 AM to 3:30 PM
        current_time_minutes = current_hour * 60 + current_minute
        open_time = config.STOCK_MARKET_OPEN_HOUR * 60 + config.STOCK_MARKET_OPEN_MINUTE
        close_time = config.STOCK_MARKET_CLOSE_HOUR * 60 + config.STOCK_MARKET_CLOSE_MINUTE
        return open_time <= current_time_minutes < close_time
        
    return False

def calculate_position_size(account_balance, risk_percentage, stop_loss_percentage):
    """
    Calculate position size based on risk involved.
    Risk Amount = Balance * Risk%
    Position Size = Risk Amount / SL%
    """
    risk_amount = account_balance * (risk_percentage / 100)
    if stop_loss_percentage == 0:
        return 0
    position_size = risk_amount / stop_loss_percentage
    position_size = risk_amount / stop_loss_percentage
    return position_size

# --- Lightweight Indicators (Zero-Pandas) ---

def calculate_sma(values, period):
    """Simple Moving Average using NumPy."""
    if len(values) < period: return None
    return float(np.mean(values[-period:]))

def calculate_ema(values, period):
    """Exponential Moving Average using NumPy (or manual loop)."""
    if len(values) < period: return None
    
    # Simple initialization with SMA
    ema = np.mean(values[:period]) 
    multiplier = 2 / (period + 1)
    
    for value in values[period:]:
        ema = (value - ema) * multiplier + ema
        
    return float(ema)

def calculate_rsi(prices, period=14):
    """Relative Strength Index using NumPy."""
    if len(prices) < period + 1: return 50.0 # Default neutral
    
    deltas = np.diff(prices)
    gains = np.maximum(deltas, 0)
    losses = np.abs(np.minimum(deltas, 0))
    
    # Calculate initial averages
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # Optimize: If avg_loss is 0, RSI is 100
    if avg_loss == 0: return 100.0
    
    # Smoothed updates (Wilder's Smoothing)
    # The standard formula usually keeps updating. 
    # For a snapshot, a simple SMA based RSI is often "close enough" but 
    # Wilder's is better. Let's do a simple rolling update if we have enough data.
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))

def calculate_vwap(high, low, close, volume):
    """Volume Weighted Average Price (Full Series)."""
    # Assuming inputs are lists or arrays of same length
    h = np.array(high)
    l = np.array(low)
    c = np.array(close)
    v = np.array(volume)
    
    typical_price = (h + l + c) / 3
    # Cumulative VWAP
    # We only need the latest VWAP really, but standard definition is cumulative from start of session.
    # For crypto (24/7), 'session' is ambiguous. 
    # Usually rolling VWAP or valid for the loaded window (100 candles).
    
    tp_v = typical_price * v
    cum_tp_v = np.cumsum(tp_v)
    cum_vol = np.cumsum(v)
    
    vwap_series = cum_tp_v / cum_vol
    return vwap_series[-1] # Return latest value only
