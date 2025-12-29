import logging
import os
import threading
import asyncio
import nest_asyncio
from flask import Flask
from telegram.ext import Application
import config
import market_data
import signals
import telegraph_handler # typo in original imports? No, it was telegram_handler
import telegram_handler
import utils
import news_manager
import schedule
import time

# Apply nest_asyncio to allow nested loops if needed (e.g. running async from sync schedule)
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
async def scan_crypto(app):
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
                await telegram_handler.send_signal(app.bot, signal, 'CRYPTO')
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

async def scan_stocks(app):
    """Scan Stock Markets."""
    if not utils.is_market_open('STOCK'):
        logger.info("Stock Market Closed. Skipping scan.")
        return

    logger.info("Scanning STOCKS...")
    for symbol in config.STOCK_SYMBOLS:
        try:
            signal = await signals.analyze_stock(symbol)
            if signal:
                await telegram_handler.send_signal(app.bot, signal, 'STOCK')
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")


# --- News Job ---
news_service = news_manager.NewsManager()

async def check_news(app):
    """Checks for news updates."""
    logger.info("Checking for NEWS...")
    
    # 1. Stock News
    if utils.is_market_open('STOCK'):
        stock_news = news_service.fetch_stock_news()
        for item in stock_news:
            await telegram_handler.send_news(app.bot, item, 'STOCK')
            
    # 2. Crypto News (Always open)
    crypto_news = news_service.fetch_crypto_news()
    for item in crypto_news:
        await telegram_handler.send_news(app.bot, item, 'CRYPTO')

    # 3. Expert Charts (CoinTelegraph RSS)
    chart_news = news_service.fetch_expert_analysis()
    for item in chart_news:
        await telegram_handler.send_news(app.bot, item, 'CRYPTO')

# --- Scheduler ---

def run_scheduler_loop(app):
    """Runs the schedule loop."""
    logger.info("Starting Scheduler Loop...")
    
    # Schedule Definitions
    schedule.every(config.CRYPTO_SCAN_INTERVAL // 60).minutes.do(
        lambda: asyncio.run(scan_crypto(app))
    )
    schedule.every(config.STOCK_SCAN_INTERVAL // 60).minutes.do(
        lambda: asyncio.run(scan_stocks(app))
    )
    schedule.every(config.NEWS_CHECK_INTERVAL // 60).minutes.do(
        lambda: asyncio.run(check_news(app))
    )
    
    while True:
        schedule.run_pending()
        time.sleep(1)

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

    # 3. Start Scheduler (Background Thread) - Passing app to it
    # We use a distinct thread for scheduling to avoid blocking main loop if we were using polling
    # But since we aren't using polling for updates (send only), we can just run scheduler in main?
    # Actually, Application.run_polling() blocks.
    # If we want to support commands like /status in the future, we need run_polling().
    # So scheduler should be a thread.
    
    t_scheduler = threading.Thread(target=run_scheduler_loop, args=(application,))
    t_scheduler.daemon = True
    t_scheduler.start()
    
    # 4. Run Telegram Polling (keeps main thread alive and handles commands)
    # Even if we don't have commands yet, this keeps the process up.
    # For Render, the Flask thread + this polling loop keeps it alive.
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
