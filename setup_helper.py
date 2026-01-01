import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import Conflict

# Load env to get Token
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def setup_bot():
    if not TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    bot = Bot(token=TOKEN)
    print(f"🤖 Connecting to bot ({TOKEN[:5]}...)...")
    
    # Check Webhook Section
    try:
        wh_info = await bot.get_webhook_info()
        print(f"📡 Webhook Status: URL='{wh_info.url}' (Has Custom Cert: {wh_info.has_custom_certificate})")
        if wh_info.url:
            print("⚠️ WARNING: Webhook is active! getUpdates will NOT work.")
            print("   Attempting to delete webhook...")
            await bot.delete_webhook()
            print("   ✅ Webhook deleted. Retrying getUpdates...")
    except Exception as e:
        print(f"⚠️ Webhook check failed: {e}")

    try:
        updates = []
        try:
            updates = await bot.get_updates()
        except Conflict:
            print("⚠️ Conflict detected. Retrying...")
            await asyncio.sleep(2)
            updates = await bot.get_updates()
        
        if not updates:
            print("📭 No updates found.")
            return

        print(f"\n🔍 Found {len(updates)} Updates. Processing...")
        found_chats = {}
        
        for u in updates:
            chat = u.effective_chat
            
            if chat and chat.type in ['group', 'supergroup', 'channel']:
                chat_title = chat.title or "Private"
                chat_id = chat.id
                found_chats[chat_title] = chat_id
                
                # Cleanup if message exists
                if u.effective_message:
                    msg = u.effective_message
                    try:
                        print(f"   🗑️ Deleting message '{msg.text}' from {chat_title}...")
                        await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                    except Exception as e:
                        pass # Ignore delete errors

        print("\n✅ Found Group IDs:")
        for title, cid in found_chats.items():
            print(f"   👉 {title}: {cid}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(setup_bot())
