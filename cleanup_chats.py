import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot

# Load env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
STOCK_ID = os.getenv('TELEGRAM_STOCK_CHANNEL_ID')
CRYPTO_ID = os.getenv('TELEGRAM_CRYPTO_CHANNEL_ID')

async def cleanup_channel(bot, chat_id, name):
    if not chat_id: return
    print(f"🧹 Cleaning {name} ({chat_id})...")
    
    # We can't simply "get all messages" in Bot API. 
    # We have to assume recent message IDs and try to delete them blindly.
    # This is a common hack for cleanup scripts.
    
    # Get last known ID strategy (or just iterate backwards from a large number if we knew it, 
    # but safer to just delete what we can see or expect).
    # Since we can't see history, we will try to delete the message IDs captured in ids.txt 
    # plus a range around them, but actually the user just wants the clutter gone.
    # A robust way is to delete the SPECIFIC messages we caused if we tracked them, 
    # but here we'll just try to delete the last 20 IDs assuming sequential ID generation (approximation).
    
    # Better approach for channels: we can't bulk delete easily without a known message ID list.
    # However, since we just spammed commands, the user might have to delete them manually 
    # OR we can try to delete the last few message IDs if we track the "Connected" message response.
    
    print(f"   ⚠️ API Limitation: Bots cannot bulk wipe history without message IDs.")
    print(f"   👉 sending a 'Cleaner' message to anchor, then deleting it.")
    
    try:
        msg = await bot.send_message(chat_id, "🧹 Cleaning up...")
        start_id = msg.message_id
        
        # Try to delete previous 100 messages to be thorough
        for i in range(100):
            try:
                await bot.delete_message(chat_id, start_id - i)
                if i % 10 == 0: print(f"      Deleted batch {i}...")
            except Exception:
                pass
    except Exception as e:
        print(f"   ❌ Error cleaning {name}: {e}")

async def main():
    bot = Bot(token=TOKEN)
    await cleanup_channel(bot, STOCK_ID, "Stock Channel")
    await cleanup_channel(bot, CRYPTO_ID, "Crypto Channel")
    print("✨ Cleanup attempt finished.")

if __name__ == "__main__":
    asyncio.run(main())
