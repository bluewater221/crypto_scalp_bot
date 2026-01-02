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

@app_flask.route('/')
def home():
    return "<h1>🚀 Scalp Bot is Running!</h1><p>Status: Active 🟢</p><p>Check Telegram for updates.</p>", 200

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
        await update.message.reply_text("Usage: /price <symbol>\nExamples: /price BTC, /price ETH, /price RELIANCE")
        return
    
    symbol = context.args[0].upper()
    
    # If symbol contains a dot (like RELIANCE.NS), it's definitely a stock
    if '.' in symbol:
        await fetch_stock_price(update, symbol)
        return
    
    # Common coin ID mappings
    common_ids = {
        'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'ripple',
        'DOGE': 'dogecoin', 'ADA': 'cardano', 'DOT': 'polkadot', 'MATIC': 'polygon',
        'BNB': 'binancecoin', 'AVAX': 'avalanche-2', 'LINK': 'chainlink',
        'UNI': 'uniswap', 'ATOM': 'cosmos', 'LTC': 'litecoin', 'SHIB': 'shiba-inu',
        'TRX': 'tron', 'NEAR': 'near', 'APT': 'aptos', 'ARB': 'arbitrum', 
        'OP': 'optimism', 'INJ': 'injective-protocol', 'SUI': 'sui', 'SEI': 'sei-network',
        'PEPE': 'pepe', 'WIF': 'dogwifcoin', 'BONK': 'bonk', 'FET': 'fetch-ai',
        'TON': 'the-open-network', 'HBAR': 'hedera-hashgraph', 'ICP': 'internet-computer'
    }
    
    # Check if it's a known crypto symbol
    if symbol in common_ids:
        try:
            import requests
            coin_id = common_ids[symbol]
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            logger.info(f"Fetching crypto price from CoinGecko: {url}")
            
            resp = await asyncio.to_thread(requests.get, url, timeout=15)
            logger.info(f"CoinGecko response status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"CoinGecko data: {data}")
                
                if coin_id in data and 'usd' in data[coin_id]:
                    price = data[coin_id]['usd']
                    change = data[coin_id].get('usd_24h_change', 0) or 0
                    emoji = "🟢" if change >= 0 else "🔴"
                    msg = (
                        f"💰 **{symbol}/USD**\n\n"
                        f"Price: ${price:,.2f}\n"
                        f"24h Change: {emoji} {change:+.2f}%"
                    )
                    await update.message.reply_text(msg, parse_mode='Markdown')
                    return
                else:
                    logger.error(f"CoinGecko returned unexpected data: {data}")
            else:
                logger.error(f"CoinGecko returned status {resp.status_code}: {resp.text}")
                
        except Exception as e:
            logger.error(f"CoinGecko error for {symbol}: {e}")
        
        # If CoinGecko failed, show error (don't try as stock for known crypto)
        await update.message.reply_text(f"❌ Could not fetch crypto price for {symbol}. Try again later.")
        return
    
    # Dynamic Search via CoinGecko
    try:
        import requests
        search_url = f"https://api.coingecko.com/api/v3/search?query={symbol}"
        logger.info(f"Searching CoinGecko for: {symbol}")
        
        search_resp = await asyncio.to_thread(requests.get, search_url, timeout=10)
        
        if search_resp.status_code == 200:
            search_data = search_resp.json()
            coins = search_data.get('coins', [])
            
            if coins:
                # Take the first best match
                best_match = coins[0]
                coin_id = best_match['id']
                coin_name = best_match['name']
                coin_symbol = best_match['symbol']
                
                # Fetch price for this ID
                price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
                price_resp = await asyncio.to_thread(requests.get, price_url, timeout=10)
                
                if price_resp.status_code == 200:
                    data = price_resp.json()
                    if coin_id in data:
                        price = data[coin_id]['usd']
                        change = data[coin_id].get('usd_24h_change', 0) or 0
                        emoji = "🟢" if change >= 0 else "🔴"
                        
                        msg = (
                            f"💰 **{coin_name} ({coin_symbol.upper()})/USD**\n\n"
                            f"Price: ${price:,.6f}\n" # 6 decimals for shitcoins
                            f"24h Change: {emoji} {change:+.2f}%"
                        )
                        await update.message.reply_text(msg, parse_mode='Markdown')
                        return

        # If crypto search fails, try Stock
        await fetch_stock_price(update, f"{symbol}.NS")

    except Exception as e:
        logger.error(f"Error resolving symbol {symbol}: {e}")
        try:
             # Last resort: Stock
            await fetch_stock_price(update, f"{symbol}.NS")
        except:
             await update.message.reply_text(f"❌ Could not find price for {symbol} (Crypto or Stock)")

async def fetch_stock_price(update: Update, stock_symbol: str):
    """Helper to fetch and display stock price."""
    import yfinance as yf
    ticker = yf.Ticker(stock_symbol)
    info = ticker.fast_info
    price = info.last_price
    prev_close = info.previous_close
    
    if price is None:
        await update.message.reply_text(f"❌ Could not fetch price for {stock_symbol}")
        return
        
    change = ((price - prev_close) / prev_close) * 100 if prev_close else 0
    emoji = "🟢" if change >= 0 else "🔴"
    msg = (
        f"📈 **{stock_symbol}**\n\n"
        f"Price: ₹{price:,.2f}\n"
        f"Change: {emoji} {change:+.2f}%"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger news fetch and send to user."""
    await update.message.reply_text("📰 Fetching latest news...")
    
    try:
        # Fetch news
        stock_news = await news_service.fetch_stock_news()
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

async def airdrops_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger airdrop fetch and send to user."""
    await update.message.reply_text("🪂 Checking for latest airdrops...")
    
    try:
        airdrops = await news_service.fetch_airdrop_opportunities()
        
        if not airdrops:
            await update.message.reply_text("No new airdrops found. Check back later!")
        else:
            for item in airdrops:
                await telegram_handler.send_airdrop(context.bot, item)
            
            await update.message.reply_text(f"✅ Sent {len(airdrops)} airdrop alerts to the channel!")
            
    except Exception as e:
        logger.error(f"Error in airdrops command: {e}")
        await update.message.reply_text(f"❌ Error fetching airdrops: {str(e)}")

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show global market sentiment."""
    await update.message.reply_text("🏥 Checking Market Pulse...")
    
    try:
        # 1. Crypto Sentiment
        fng = market_data.get_fear_and_greed_index()
        fng_val = fng.get('value', 0)
        fng_class = fng.get('value_classification', 'Unknown')
        
        # Color coding for F&G
        fng_emoji = "😐"
        if fng_val >= 75: fng_emoji = "🤑" # Extreme Greed
        elif fng_val >= 55: fng_emoji = "🙂" # Greed
        elif fng_val <= 25: fng_emoji = "😨" # Extreme Fear
        elif fng_val <= 45: fng_emoji = "😟" # Fear
        
        # 2. Stock Market Trend (Nifty 50)
        nifty = await market_data.get_market_status()
        nifty_msg = "🇮🇳 **Nifty 50**: N/A"
        
        if nifty:
            trend_emoji = "🟢" if nifty['trend'] == 'BULLISH' else "🔴"
            nifty_msg = (
                f"🇮🇳 **Nifty 50**: {trend_emoji} {nifty['trend']}\n"
                f"Price: {nifty['price']:,.2f} ({nifty['pct_change']:+.2f}%)"
            )
            
        # 3. Construct Message
        msg = (
            f"🏥 **Market Pulse**\n\n"
            f"{nifty_msg}\n\n"
            f"₿ **Crypto Sentiment**\n"
            f"{fng_emoji} **{fng_class}** ({fng_val}/100)\n"
            f"Ref: Alternative.me"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in market command: {e}")
        await update.message.reply_text("❌ Failed to fetch market data.")

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
    success_count = 0
    fail_count = 0
    failed_symbols = []
    
    for symbol in config.STOCK_SYMBOLS:
        try:
            signal = await signals.analyze_stock(symbol)
            if signal:
                await telegram_handler.send_signal(context.bot, signal, 'STOCK')
                trade_mgr.open_trade(signal)
            success_count += 1
        except Exception as e:
            fail_count += 1
            failed_symbols.append(symbol)
            logger.warning(f"Failed to scan {symbol}: {type(e).__name__}")
    
    # Log summary
    if fail_count > 0:
        logger.warning(f"Stock scan complete: {success_count} OK, {fail_count} failed: {', '.join(failed_symbols)}")
    else:
        logger.info(f"Stock scan complete: {success_count}/{len(config.STOCK_SYMBOLS)} symbols scanned")

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
        stock_news = await news_service.fetch_stock_news()
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

async def check_airdrops(context: ContextTypes.DEFAULT_TYPE):
    """Checks for airdrop updates."""
    logger.info("Checking for AIRDROPS...")
    airdrops = await news_service.fetch_airdrop_opportunities()
    
    for item in airdrops:
        await telegram_handler.send_airdrop(context.bot, item)



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
    application.add_handler(CommandHandler("airdrops", airdrops_command))
    application.add_handler(CommandHandler("market", market_command))


    # 3. separate jobs
    job_queue = application.job_queue
    if job_queue:
        logger.info("Starting Scheduler via JobQueue...")
        
        # Crypto Scan
        job_queue.run_repeating(scan_crypto, interval=config.CRYPTO_SCAN_INTERVAL, first=10)
        
        # Stock Scan
        job_queue.run_repeating(scan_stocks, interval=config.STOCK_SCAN_INTERVAL, first=15)
        
        # News & Airdrops -> Moved to GitHub Actions (run_content_job.py)
        # job_queue.run_repeating(news_job, interval=config.NEWS_CHECK_INTERVAL, first=30)
        # job_queue.run_repeating(airdrop_job, interval=config.AIRDROP_CHECK_INTERVAL, first=60)
        
        # Trade Manager (New) - Check every 5 minutes
        job_queue.run_repeating(check_trades, interval=300, first=40)
    else:
        logger.error("❌ JobQueue is not available! Make sure 'python-telegram-bot[job-queue]' is installed.")

    # 4. Run Telegram Polling
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
