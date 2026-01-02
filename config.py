import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Common Configuration ---
LOGGING_LEVEL = 'INFO'
TIMEZONE_STR = 'Asia/Kolkata'
PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CRYPTO_CHANNEL_ID = os.getenv('TELEGRAM_CRYPTO_CHANNEL_ID') # @cryptoscalp
TELEGRAM_STOCK_CHANNEL_ID = os.getenv('TELEGRAM_STOCK_CHANNEL_ID')   # @stockscalp
TELEGRAM_CRYPTO_PNL_CHANNEL_ID = os.getenv('TELEGRAM_CRYPTO_PNL_CHANNEL_ID') # PnL Channel
TELEGRAM_STOCK_PNL_CHANNEL_ID = os.getenv('TELEGRAM_STOCK_PNL_CHANNEL_ID')   # PnL Channel
TELEGRAM_LOG_CHANNEL_ID = os.getenv('TELEGRAM_LOG_CHANNEL_ID')       # @scalper_logs (Optional)
CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')


# Google Sheets
GOOGLE_SHEETS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON', 'credentials.json')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Scalper_Logs')




# --- Crypto Configuration (Public Data) ---
# --- Crypto Configuration (Public Data) ---
CRYPTO_PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT']
CRYPTO_TIMEFRAME = '1m' # Using 1m data for calculation
CRYPTO_SCAN_INTERVAL = 60 # 1 minute
CRYPTO_MARKET_OPEN = 9
CRYPTO_MARKET_CLOSE = 23

# Crypto Strategy (RSI Scalp)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
CRYPTO_STOP_LOSS = 0.005 # 0.5%
CRYPTO_TAKE_PROFIT = 0.01 # 1%
CRYPTO_RISK_PER_TRADE = 0.005 # 0.5%
INITIAL_CAPITAL_CRYPTO = 100 # USD

# --- Stock Configuration (Indian Markets) ---
# NIFTY500 or selected highly liquid stocks. 
# For demo, using a small list of liquid reliable stocks.
STOCK_SYMBOLS = [
    # --- Major Stocks ---
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'SBIN.NS', 'ICICIBANK.NS',
    'AXISBANK.NS', 'KOTAKBANK.NS', 'LT.NS', 'HINDUNILVR.NS', 'ITC.NS', 'BAJFINANCE.NS', 
    'MARUTI.NS',
    
    # --- Index ETFs ---
    'NIFTYBEES.NS', 'BANKBEES.NS', 'JUNIORBEES.NS', 'MID150BEES.NS', 'CPSEETF.NS',
    
    # --- Sectoral ETFs ---
    'ITBEES.NS', 'PHARMABEES.NS', 'PSUBNKBEES.NS', 'AUTOBEES.NS', 'INFRABEES.NS',
    
    # --- Commodity & International ETFs ---
    'GOLDBEES.NS', 'SILVERBEES.NS', 'MON100.NS', 'MAFANG.NS'
] 
STOCK_TIMEFRAME = '5m'
STOCK_SCAN_INTERVAL = 300 # 5 minutes
STOCK_MARKET_OPEN_HOUR = 9
STOCK_MARKET_OPEN_MINUTE = 25 # Start 9:25 AM (Avoid opening chaos)
STOCK_MARKET_CLOSE_HOUR = 14
STOCK_MARKET_CLOSE_MINUTE = 45 # Stop 2:45 PM (Avoid intraday square-off chaos)


# Stock Strategy (EMA Cross)
EMA_FAST = 9
EMA_SLOW = 21
STOCK_STOP_LOSS = 0.005
STOCK_TAKE_PROFIT = 0.015 # 1.5R Minimum
STOCK_RISK_PER_TRADE = 0.005 
INITIAL_CAPITAL_STOCK = 10000 # INR 
EMA_CROSS_THRESHOLD = 0.001 # 0.1% Separation required 


ADX_MIN = 15 # Lowered from 20 to allow more trades
ADX_MAX = 40
RSI_MIN = 45
RSI_MAX = 65 

# --- Kite Connect Configuration (Removed - Using yfinance fallback) ---
KITE_API_KEY = None
KITE_ACCESS_TOKEN = None

# --- News & Airdrop Configuration ---
# --- News & Airdrop Configuration ---
NEWS_CHECK_INTERVAL = 14400 # 4 hours (Was 30 mins) - "Less News"
AIRDROP_CHECK_INTERVAL = 86400 # 24 hours (Was 6 hours)

def check_config():
    print("--- Configuration Check ---")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ Set' if TELEGRAM_BOT_TOKEN else '❌ Missing'}")
    print(f"GEMINI_API_KEY: {'✅ Set' if GEMINI_API_KEY else '⚠️ Missing (AI Disabled)'}")
    print(f"GROQ_API_KEY: {'✅ Set' if GROQ_API_KEY else '⚠️ Missing (AI Disabled)'}")
    print(f"OPENROUTER_API_KEY: {'✅ Set' if OPENROUTER_API_KEY else '⚠️ Missing (OpenRouter Fallback Disabled)'}")
    print(f"CRYPTO_PAIRS: {len(CRYPTO_PAIRS)} configured")
    print(f"STOCK_SYMBOLS: {len(STOCK_SYMBOLS)} configured")
    print("---------------------------")

check_config()
