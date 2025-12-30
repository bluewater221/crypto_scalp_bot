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
import trade_manager

# Apply nest_asyncio to allow nested loops if needed (though PTB handles this well usually)
nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global Services
news_service = news_manager.NewsManager()
trade_mgr = trade_manager.TradeManager()

# --- Flask Keep-Alive ---
app_flask = Flask(__name__)

@app_flask.route('/ping')
def ping():
    return "Bot alive! 🟢", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host='0.0.0.0', port=port)

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    await update.message.reply_text("🚀 Scalp Bot 2.0 (AI Edition) is active!")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Returns the Chat ID of the current chat."""
    chat_id = update.effective_chat.id
    title = update.effective_chat.title or "Private Chat"
    await update.effective_message.reply_text(f"🆔 **Chat ID**: `{chat_id}`\nTitle: {title}", parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show performance stats."""
    stats = trade_mgr.get_stats()
    await update.message.reply_text(stats, parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to check if bot is responsive and config is loaded."""
    crypto_status = "✅ Configured" if config.TELEGRAM_CRYPTO_CHANNEL_ID else "❌ Missing"
    stock_status = "✅ Configured" if config.TELEGRAM_STOCK_CHANNEL_ID else "❌ Missing"
    
    msg = (
        f"🤖 **Bot Status**: Online\n"
        f"📅 **Time**: {utils.get_ist_time().strftime('%Y-%m-%d %H:%M:%S')} IST\n\n"
        f"**Configuration Check**:\n"
        f"• Crypto Channel: {crypto_status}\n"
        f"• Stock Channel: {stock_status}\n"
        f"• Scheduling: Active 🟢"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands."""
    msg = (
        "🤖 **Scalp Bot Commands**\n\n"
        "📊 **Market Data**\n"
        "/price <symbol> - Get current price\n"
        "  _Examples: /price BTC, /price RELIANCE_\n\n"
        "📰 **News**\n"
        "/news - Get latest market news now\n\n"
        "📈 **Trading**\n"
        "/stats - View performance stats\n"
        "/test - Check bot status\n\n"
        "🔧 **Utility**\n"
        "/id - Get chat ID\n"
        "/help - Show this message"
    )
    await update.effective_message.reply_text(msg, parse_mode='Markdown')

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current price for a crypto or stock symbol."""
    if not context.args:
        await update.message.reply_text("Usage: /price <symbol>\nExamples: /price BTC, /price RELIANCE")
        return
    
    symbol = context.args[0].upper()
    
    try:
        # Check if it's a crypto symbol
        if symbol in ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'DOT', 'MATIC', 'BNB', 'AVAX']:
            # Try using ccxt with Bybit
            try:
                exchange = market_data.get_crypto_exchange()
                if exchange:
                    # Load markets first
                    await asyncio.to_thread(exchange.load_markets)
                    ticker = await asyncio.to_thread(exchange.fetch_ticker, f"{symbol}/USDT")
                    price = ticker['last']
                    change = ticker.get('percentage', 0) or 0
                    emoji = "🟢" if change >= 0 else "🔴"
                    msg = (
                        f"💰 **{symbol}/USDT**\n\n"
                        f"Price: ${price:,.2f}\n"
                        f"24h Change: {emoji} {change:+.2f}%"
                    )
                else:
                    raise Exception("Exchange not available")
            except Exception as e:
                logger.warning(f"Bybit failed for {symbol}: {e}, trying CoinGecko...")
                # Fallback to CoinGecko API
                import requests
                coin_ids = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'ripple', 
                           'DOGE': 'dogecoin', 'ADA': 'cardano', 'DOT': 'polkadot', 'MATIC': 'polygon',
                           'BNB': 'binancecoin', 'AVAX': 'avalanche-2'}
                coin_id = coin_ids.get(symbol, symbol.lower())
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
                resp = await asyncio.to_thread(requests.get, url, timeout=10)
                data = resp.json()
                if coin_id in data:
                    price = data[coin_id]['usd']
                    change = data[coin_id].get('usd_24h_change', 0) or 0
                    emoji = "🟢" if change >= 0 else "🔴"
                    msg = (
                        f"💰 **{symbol}/USD**\n\n"
                        f"Price: ${price:,.2f}\n"
                        f"24h Change: {emoji} {change:+.2f}%"
                    )
                else:
                    msg = f"❌ Could not fetch price for {symbol}"
        else:
            # Assume it's a stock - add .NS if not present
            stock_symbol = symbol if '.' in symbol else f"{symbol}.NS"
            import yfinance as yf
            ticker = yf.Ticker(stock_symbol)
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change = ((price - prev_close) / prev_close) * 100 if prev_close else 0
            emoji = "🟢" if change >= 0 else "🔴"
            msg = (
                f"📈 **{stock_symbol}**\n\n"
                f"Price: ₹{price:,.2f}\n"
                f"Change: {emoji} {change:+.2f}%"
            )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        await update.message.reply_text(f"❌ Could not fetch price for {symbol}")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger news fetch and send to user."""
    await update.message.reply_text("📰 Fetching latest news...")
    
    try:
        # Fetch news
        stock_news = news_service.fetch_stock_news()
        crypto_news = news_service.fetch_crypto_news()
        
        total = len(stock_news) + len(crypto_news)
        
        if total == 0:
            await update.message.reply_text("No new news found. Check back later!")
        else:
            # Send news to channels
            for item in stock_news:
                await telegram_handler.send_news(context.bot, item, 'STOCK')
            for item in crypto_news:
                await telegram_handler.send_news(context.bot, item, 'CRYPTO')
            
            await update.message.reply_text(f"✅ Sent {total} news items to channels!")
            
    except Exception as e:
        logger.error(f"Error in news command: {e}")
        await update.message.reply_text(f"❌ Error fetching news: {str(e)}")

# --- Scanning Jobs ---
async def scan_crypto(context: ContextTypes.DEFAULT_TYPE):
    """Scan Crypto Markets."""
    if not utils.is_market_open('CRYPTO'):
        logger.info("Crypto Market Closed. Skipping scan.")
        return

    logger.info("Scanning CRYPTO...")
    exchange = market_data.get_crypto_exchange()
    if not exchange: return

    for symbol in config.CRYPTO_PAIRS:
        try:
            signal = await signals.analyze_crypto(exchange, symbol)
            if signal:
                await telegram_handler.send_signal(context.bot, signal, 'CRYPTO')
                trade_mgr.open_trade(signal)
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
                trade_mgr.open_trade(signal)
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

# --- Trade Manager Job ---
async def check_trades(context: ContextTypes.DEFAULT_TYPE):
    """Update active trades."""
    await trade_mgr.update_trades(context.bot)

# --- News Job ---
# news_service is global
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
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("news", news_command))

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
        
        # Trade Manager (New) - Check every 5 minutes
        job_queue.run_repeating(check_trades, interval=300, first=30)
    else:
        logger.error("❌ JobQueue is not available! Make sure 'python-telegram-bot[job-queue]' is installed.")

    # 4. Run Telegram Polling
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
