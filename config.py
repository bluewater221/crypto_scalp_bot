import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- API Keys ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CRYPTO_CHANNEL_ID = os.getenv("TELEGRAM_CRYPTO_CHANNEL_ID")
TELEGRAM_STOCK_CHANNEL_ID = os.getenv("TELEGRAM_STOCK_CHANNEL_ID")
TELEGRAM_CRYPTO_PNL_CHANNEL_ID = os.getenv("TELEGRAM_CRYPTO_PNL_CHANNEL_ID") 
TELEGRAM_STOCK_PNL_CHANNEL_ID = os.getenv("TELEGRAM_STOCK_PNL_CHANNEL_ID")
TELEGRAM_LOG_CHANNEL_ID = os.getenv("TELEGRAM_LOG_CHANNEL_ID") # Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") # Fallback
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

# Google Sheets
GOOGLE_SHEETS_JSON = 'credentials.json' # File path or Env Var content
GOOGLE_SHEET_NAME = "ScalpBot_DB"

# --- Trading Configuration ---
CRYPTO_SCAN_INTERVAL = 60 # Seconds
STOCK_SCAN_INTERVAL = 300 # Seconds
NEWS_CHECK_INTERVAL = 3600 # 1 Hour
AIRDROP_CHECK_INTERVAL = 21600 # 6 Hours

# Crypto Strategy (RSI Scalp)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
CRYPTO_STOP_LOSS = 0.005 # 0.5%
CRYPTO_TAKE_PROFIT = 0.01 # 1%
CRYPTO_RISK_PER_TRADE = 0.95 # 95% Risk for micro account (5 USDT) to ensure trade size > minimum
INITIAL_CAPITAL_CRYPTO = 10 # USD (User Real Balance) - Default
INITIAL_CAPITAL_CRYPTO_SPOT = 10 # USD
INITIAL_CAPITAL_CRYPTO_FUTURE = 10 # USD
ENABLE_SPOT_TRADING = False
ENABLE_FUTURES_TRADING = True
FUTURE_LEVERAGE = 5 # x5 Leverage
MIN_TRADE_AMOUNT_CRYPTO = 5 # Binance Min
ENABLE_COMPOUNDING = False # Set to False to ALWAYS start with Initial Capital (Ignore History PnL)

# --- Stock Configuration (Indian Markets) ---
# NIFTY500 or selected highly liquid stocks. 
# For demo, using a small list of liquid reliable stocks.
STOCK_SYMBOLS = [
    # --- Major Stocks ---
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "MARUTI.NS", "TATASTEEL.NS", "M&M.NS",
    "ASIANPAINT.NS", "TITAN.NS", "SUNPHARMA.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS",
    
    # --- Midcap / Volatile (Good for Scalping) ---
    "ADANIENT.NS", "ADANIPORTS.NS", "TATAMOTORS.NS", "VEDL.NS", "ZOMATO.NS",
    "PAYTM.NS", "DLF.NS", "HAL.NS", "BEL.NS", "TRENT.NS"
]

STOCK_STOP_LOSS = 0.005 # 0.5%
STOCK_TAKE_PROFIT = 0.01 # 1%
STOCK_RISK_PER_TRADE = 0.20 # 20% of Capital per trade for Stocks
INITIAL_CAPITAL_STOCK = 30000 # INR - Paper Trading Balance

# Indicators logic
# EMA Cross Strategy
EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 50 
EMA_CROSS_THRESHOLD = 0.001 # 0.1% separation required

# ADX Filter
ADX_MIN = 20
ADX_MAX = 50 # Avoid extreme trends (reversal risk)

# RSI Filter for Stocks
RSI_MIN = 45 # Momentum start
RSI_MAX = 65 # Momentum continuation (avoid Overbought > 70 for entry)
