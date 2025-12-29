import logging
import os
import threading
import asyncio
import nest_asyncio
from flask import Flask
from telegram.ext import Application, ContextTypes, CommandHandler
from telegram import Update
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

# --- Command Handlers ---
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to check if bot is responsive."""
    await update.message.reply_text("Bot is alive and running! 🟢\nScheduling is active.")

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
    # News can happen anytime, not just during market hours
    try:
        stock_news = news_service.fetch_stock_news()
        for item in stock_news:
            await telegram_handler.send_news(context.bot, item, 'STOCK')
    except Exception as e:
        logger.error(f"Stock news fetch failed: {e}")
            
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

    # Check Critical Env Vars
    if not config.TELEGRAM_BOT_TOKEN:
        logger.critical("❌ FATAL: TELEGRAM_BOT_TOKEN is missing! Check your environment variables.")
        return

    # 1. Start Flask (Background Thread)
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()
    
    # 2. Initialize Telegram Bot
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add Command Handlers
    application.add_handler(CommandHandler("test", test_command))

    # 3. separate jobs
    job_queue = application.job_queue
    if job_queue:
        logger.info("Starting Scheduler via JobQueue...")
        
        # Crypto Scan
        job_queue.run_repeating(scan_crypto, interval=config.CRYPTO_SCAN_INTERVAL, first=10)
        
        # Stock Scan
        job_queue.run_repeating(scan_stocks, interval=config.STOCK_SCAN_INTERVAL, first=15)
        
        # News Check
        job_queue.run_repeating(check_news, interval=config.NEWS_CHECK_INTERVAL, first=20)
    else:
        logger.error("❌ JobQueue is not available! Make sure 'python-telegram-bot[job-queue]' is installed.")

    # 4. Run Telegram Polling
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
