import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot

# Load env to get Token
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def get_updates():
    if not TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    bot = Bot(token=TOKEN)
    print(f"🤖 Connecting to bot...")
    
    try:
        # Get Updates (last 24 hours effectively)
        updates = await bot.get_updates()
        
        if not updates:
            print("📭 No updates found. Make sure you sent a message like /id in the group!")
            return

        print("\n🔍 Found Chats:")
        found_ids = set()
        
        for u in updates:
            if u.effective_chat:
                chat = u.effective_chat
                # We only care about Groups/Channels
                chat_type = chat.type
                chat_title = chat.title or "Private"
                chat_id = chat.id
                
                identifier = f"{chat_title} ({chat_id})"
                
                if identifier not in found_ids:
                    print(f"   • Type: {chat_type} | Title: {chat_title} | ID: {chat_id}")
                    found_ids.add(identifier)
                    
    except Exception as e:
        print(f"❌ Error fetching updates: {e}")

if __name__ == "__main__":
    asyncio.run(get_updates())
