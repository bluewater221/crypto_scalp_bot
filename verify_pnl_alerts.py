import asyncio
import os
import logging
from telegram import Bot
import config

async def test_pnl_alerts():
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    # 1. Test Crypto PnL Alert
    crypto_channel = config.TELEGRAM_CRYPTO_PNL_CHANNEL_ID
    if crypto_channel:
        from datetime import datetime
        ist_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🚀 Sending Mock CRYPTO PnL Alert to {crypto_channel}...")
        msg = (
            f"✅ **TRADE CLOSED: BTC/USDT**\n"
            f"Result: WIN\n"
            f"📅 **Time**: {ist_now} IST\n"
            f"PnL: +1.00% ($0.10)\n\n"
            f"💰 **Portfolio Update (CRYPTO\\_SPOT)**\n"
            f"Initial Capital: $10.00\n"
            f"Amount Used: $10.00\n"
            f"New Balance: $10.10\n\n"
            f"Entry: 95000 | Exit: 95950"
        )
        try:
            await bot.send_message(chat_id=crypto_channel, text=msg, parse_mode='Markdown')
            print("✅ Crypto Alert Sent!")
        except Exception as e:
            print(f"❌ Crypto Alert Failed: {e}")
    else:
        print("⚠️ Crypto PnL Channel ID not set.")

    # 2. Test Stock PnL Alert
    stock_channel = config.TELEGRAM_STOCK_PNL_CHANNEL_ID
    if stock_channel:
        ist_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🚀 Sending Mock STOCK PnL Alert to {stock_channel}...")
        msg = (
            f"❌ **TRADE CLOSED: RELIANCE.NS**\n"
            f"Result: LOSS\n"
            f"📅 **Time**: {ist_now} IST\n"
            f"PnL: -0.50% (-₹150.00)\n\n"
            f"💰 **Portfolio Update (STOCK)**\n"
            f"Initial Capital: ₹30,000.00\n"
            f"Amount Used: ₹3,000.00\n"
            f"New Balance: ₹29,850.00\n\n"
            f"Entry: 2500 | Exit: 2487.5"
        )
        try:
            await bot.send_message(chat_id=stock_channel, text=msg, parse_mode='Markdown')
            print("✅ Stock Alert Sent!")
        except Exception as e:
            print(f"❌ Stock Alert Failed: {e}")
    else:
        print("⚠️ Stock PnL Channel ID not set.")

if __name__ == "__main__":
    asyncio.run(test_pnl_alerts())
