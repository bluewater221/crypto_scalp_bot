import logging
import os
import threading
import asyncio
import nest_asyncio
from flask import Flask
from telegram.ext import Application, ContextTypes
import config
import market_data
import signals

import telegram_handler
import utils
import news_manager

# Apply nest_asyncio to allow nested loops if needed (though PTB handles this well usually)
nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Flask Keep-Alive ---
app_flask = Flask(__name__)

@app_flask.route('/ping')
def ping():
    return "Bot alive! 🟢", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host='0.0.0.0', port=port)

# --- Scanning Jobs ---
async def scan_crypto(context: ContextTypes.DEFAULT_TYPE):
    """Scan Crypto Markets."""
    if not utils.is_market_open('CRYPTO'):
        logger.info("Crypto Market Closed. Skipping scan.")
        return

    logger.info("Scanning CRYPTO...")
    exchange = market_data.get_crypto_exchange()
    if not exchange:
        return

    for symbol in config.CRYPTO_PAIRS:
        try:
            signal = await signals.analyze_crypto(exchange, symbol)
            if signal:
                await telegram_handler.send_signal(context.bot, signal, 'CRYPTO')
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

async def scan_stocks(context: ContextTypes.DEFAULT_TYPE):
    """Scan Stock Markets."""
    if not utils.is_market_open('STOCK'):
        logger.info("Stock Market Closed. Skipping scan.")
        return

    logger.info("Scanning STOCKS...")
    for symbol in config.STOCK_SYMBOLS:
        try:
            signal = await signals.analyze_stock(symbol)
            if signal:
                await telegram_handler.send_signal(context.bot, signal, 'STOCK')
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")


# --- News Job ---
news_service = news_manager.NewsManager()

async def check_news(context: ContextTypes.DEFAULT_TYPE):
    """Checks for news updates."""
    logger.info("Checking for NEWS...")
    
    # 1. Stock News
    if utils.is_market_open('STOCK'):
        stock_news = news_service.fetch_stock_news()
        for item in stock_news:
            await telegram_handler.send_news(context.bot, item, 'STOCK')
            
    # 2. Crypto News (Always open)
    crypto_news = news_service.fetch_crypto_news()
    for item in crypto_news:
        await telegram_handler.send_news(context.bot, item, 'CRYPTO')

    # 3. Expert Charts (CoinTelegraph RSS)
    chart_news = news_service.fetch_expert_analysis()
    for item in chart_news:
        await telegram_handler.send_news(context.bot, item, 'CRYPTO')


def main():
    """Main Entry Point."""
    logger.info("Starting Unified Scalp Bot...")

    # 1. Start Flask (Background Thread)
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()
    
    # 2. Initialize Telegram Bot
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram Token found!")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    job_queue = application.job_queue

    # 3. separate jobs
    logger.info("Starting Scheduler via JobQueue...")
    
    # Crypto Scan
    job_queue.run_repeating(scan_crypto, interval=config.CRYPTO_SCAN_INTERVAL, first=10)
    
    # Stock Scan
    job_queue.run_repeating(scan_stocks, interval=config.STOCK_SCAN_INTERVAL, first=15)
    
    # News Check
    job_queue.run_repeating(check_news, interval=config.NEWS_CHECK_INTERVAL, first=20)

    # 4. Run Telegram Polling
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
