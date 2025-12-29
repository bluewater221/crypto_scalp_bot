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
CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY')


# Google Sheets
GOOGLE_SHEETS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON', 'credentials.json')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Scalper_Logs')

# --- Crypto Configuration (Binance) ---
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

CRYPTO_PAIRS = ['BTC/USDT', 'ETH/USDT']
CRYPTO_TIMEFRAME = '1m' # Using 1m data for calculation
CRYPTO_SCAN_INTERVAL = 900 # 15 minutes
CRYPTO_MARKET_OPEN = 9
CRYPTO_MARKET_CLOSE = 23

# Crypto Strategy (RSI Scalp)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
CRYPTO_STOP_LOSS = 0.005 # 0.5%
CRYPTO_TAKE_PROFIT = 0.01 # 1%
CRYPTO_RISK_PER_TRADE = 0.5 # 0.5%

# --- Stock Configuration (Indian Markets) ---
# NIFTY500 or selected highly liquid stocks. 
# For demo, using a small list of liquid reliable stocks.
STOCK_SYMBOLS = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'SBIN.NS', 'ICICIBANK.NS', 'TATAMOTORS.NS'] 
STOCK_TIMEFRAME = '5m'
STOCK_SCAN_INTERVAL = 600 # 10 minutes
STOCK_MARKET_OPEN_HOUR = 9
STOCK_MARKET_OPEN_MINUTE = 15
STOCK_MARKET_CLOSE_HOUR = 15
STOCK_MARKET_CLOSE_MINUTE = 30

# Stock Strategy (EMA Cross)
EMA_FAST = 9
EMA_SLOW = 21
STOCK_STOP_LOSS = 0.005
STOCK_TAKE_PROFIT = 0.01
STOCK_RISK_PER_TRADE = 0.5 

# --- News Configuration ---
NEWS_CHECK_INTERVAL = 1800 # 30 minutes

