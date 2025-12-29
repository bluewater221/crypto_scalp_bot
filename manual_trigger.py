import asyncio
import logging
import config
from telegram import Bot
import bot
import market_data
import signals
import telegram_handler
import news_manager

# Mock Context
class MockContext:
    def __init__(self, token):
        self.bot = Bot(token=token)

async def scan_and_report_crypto(context):
    print("--- Starting Manual Crypto Scan ---")
    exchange = market_data.get_crypto_exchange()
    if not exchange:
        print("❌ Failed to initialize exchange.")
        return

    signals_found = 0
    for symbol in config.CRYPTO_PAIRS:
        print(f"Analyzing {symbol}...")
        try:
            signal = await signals.analyze_crypto(exchange, symbol)
            if signal:
                print(f"✅ SIGNAL FOUND for {symbol}! Sending to Telegram...")
                if 'ai_confidence' in signal:
                    print(f"🧠 AI: {signal['ai_confidence']} | {signal['ai_reasoning']}")
                await telegram_handler.send_signal(context.bot, signal, 'CRYPTO')
                signals_found += 1
            else:
                print(f"ℹ️ No signal for {symbol}.")
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")
            
    if signals_found == 0:
        print("--- Crypto Scan Complete: No signals generated. ---")
        try:
            channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID
            if channel_id:
                await context.bot.send_message(chat_id=channel_id, text="🔔 Manual Scan Complete: No Crypto signals found.")
                print("✅ Sent 'No signals' confirmation to Telegram.")
            else:
                print("⚠️ No Channel ID configured (CRYPTO).")
        except Exception as e:
            print(f"❌ Failed to send confirmation: {e}")
    else:
        print(f"--- Crypto Scan Complete: Sent {signals_found} signals. ---")

async def scan_and_report_stocks(context):
    print("\n--- Starting Manual Stock Scan ---")
    # Note: We are bypassing utils.is_market_open check here to force a test
    
    signals_found = 0
    for symbol in config.STOCK_SYMBOLS:
        print(f"Analyzing {symbol}...")
        try:
            signal = await signals.analyze_stock(symbol)
            if signal:
                print(f"✅ SIGNAL FOUND for {symbol}! Sending to Telegram...")
                await telegram_handler.send_signal(context.bot, signal, 'STOCK')
                signals_found += 1
            else:
                print(f"ℹ️ No signal for {symbol}.")
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")

    if signals_found == 0:
        print("--- Stock Scan Complete: No signals generated. ---")
    else:
        print(f"--- Stock Scan Complete: Sent {signals_found} signals. ---")

async def scan_and_report_news(context):
    print("\n--- Starting Manual News Check ---")
    news_mgr = news_manager.NewsManager()
    
    # 1. Stocks
    print("Fetching Stock News...")
    s_news = news_mgr.fetch_stock_news()
    if s_news:
        print(f"✅ Found {len(s_news)} Stock News items.")
        for item in s_news:
             print(f"   - {item['title']}")
             sent = item.get('sentiment')
             if isinstance(sent, dict):
                 print(f"     🤖 AI: {sent.get('sentiment')} | {sent.get('ai_insight')}")
             else:
                 print(f"     Sentiment: {sent}")
             await telegram_handler.send_news(context.bot, item, 'STOCK')
    else:
        print("ℹ️ No Stock News found.")

    # 2. Crypto
    print("Fetching Crypto News (CryptoPanic)...")
    c_news = news_mgr.fetch_crypto_news()
    if c_news:
        print(f"✅ Found {len(c_news)} Crypto News items.")
        for item in c_news:
             print(f"   - {item['title']}")
             sent = item.get('sentiment')
             if isinstance(sent, dict):
                 print(f"     🤖 AI: {sent.get('sentiment')} | {sent.get('ai_insight')}")
             else:
                 print(f"     Sentiment: {sent}")
             await telegram_handler.send_news(context.bot, item, 'CRYPTO')
    else:
        print("ℹ️ No Crypto News found (Check API Key).")
        
    # 3. Charts
    print("Fetching Expert Analysis...")
    charts = news_mgr.fetch_expert_analysis()
    if charts:
        print(f"✅ Found {len(charts)} Chart Analysis items.")
        for item in charts:
             print(f"   - {item['title']}")
             sent = item.get('sentiment')
             if isinstance(sent, dict):
                 print(f"     🤖 AI: {sent.get('sentiment')} | {sent.get('ai_insight')}")
             else:
                 print(f"     Sentiment: {sent}")
             await telegram_handler.send_news(context.bot, item, 'CRYPTO')
    else:
        print("ℹ️ No Expert Analysis found.")

async def main():
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    ctx = MockContext(config.TELEGRAM_BOT_TOKEN)
    await scan_and_report_crypto(ctx)
    await scan_and_report_stocks(ctx)
    await scan_and_report_news(ctx)

if __name__ == "__main__":
    asyncio.run(main())
