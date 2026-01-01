
import asyncio
import logging
from telegram import Bot
import config
import news_manager
import telegram_handler
from datetime import datetime, timezone
import market_data

# Configure Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Content Job (The Analyst)...")
    
    # Initialize Bot
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("No Bot Token found!")
        return
        
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    nm = news_manager.NewsManager()

    try:
        # 1. Fetch & Send Stock News
        logger.info("Fetching Stock News...")
        stock_news = await nm.fetch_stock_news()
        for item in stock_news:
             await telegram_handler.send_news(bot, item, 'STOCK')
             await asyncio.sleep(1) # Rate limit safety

        # 2. Fetch & Send Crypto News
        logger.info("Fetching Crypto News...")
        crypto_news = nm.fetch_crypto_news()
        for item in crypto_news:
             await telegram_handler.send_news(bot, item, 'CRYPTO')
             await asyncio.sleep(1)

        # 3. Fetch & Send Airdrops
        logger.info("Fetching Airdrops...")
        airdrops = await nm.fetch_airdrop_opportunities()
        for item in airdrops:
             await telegram_handler.send_airdrop(bot, item)
             await asyncio.sleep(1)

        # 4. Market Pulse Summary (Morning Check)
        # Check if it's "Morning" in IST (approx 08:00 - 09:00 IST)
        # Github runs UTC. 03:00 UTC is 08:30 IST.
        now_hour = datetime.now(timezone.utc).hour
        if 2 <= now_hour <= 4: # Run between 7:30 AM and 9:30 AM IST
            logger.info("Sending Daily Market Pulse...")
            
            # Reusing logic from bot.py market_command but specialized for job
            fng = market_data.get_fear_and_greed_index()
            nifty = await market_data.get_market_status()
            
            # Reuse logic strictly or duplicate? Duplicating small logic is safer than importing bot.py (circular)
            fng_val = fng.get('value', 0)
            fng_class = fng.get('value_classification', 'Unknown')
            fng_emoji = "😐"
            if fng_val >= 75: fng_emoji = "🤑" 
            elif fng_val >= 55: fng_emoji = "🙂"
            elif fng_val <= 25: fng_emoji = "😨"
            elif fng_val <= 45: fng_emoji = "😟"

            nifty_msg = "🇮🇳 **Nifty 50**: N/A"
            if nifty:
                trend_emoji = "🟢" if nifty['trend'] == 'BULLISH' else "🔴"
                nifty_msg = f"🇮🇳 **Nifty 50**: {trend_emoji} {nifty['trend']} ({nifty['pct_change']:+.2f}%)"

            msg = (
                f"🌅 **Morning Market Pulse**\n\n"
                f"{nifty_msg}\n"
                f"₿ **Crypto**: {fng_emoji} {fng_class} ({fng_val})\n"
            )
            
            # Send to both channels
            if config.TELEGRAM_STOCK_CHANNEL_ID:
                await bot.send_message(chat_id=config.TELEGRAM_STOCK_CHANNEL_ID, text=msg, parse_mode='Markdown')
            if config.TELEGRAM_CRYPTO_CHANNEL_ID:
                await bot.send_message(chat_id=config.TELEGRAM_CRYPTO_CHANNEL_ID, text=msg, parse_mode='Markdown')

        logger.info("Content Job Complete.")

    except Exception as e:
        logger.error(f"Error in Content Job: {e}")

if __name__ == "__main__":
    asyncio.run(main())
