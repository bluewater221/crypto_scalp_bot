import pytz
from datetime import datetime
import config

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
    return position_size
