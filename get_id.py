import asyncio
from telegram import Bot
import config

async def get_updates():
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    updates = await bot.get_updates()
    print(f"Found {len(updates)} updates.")
    for u in updates:
        if u.channel_post:
            print(f"Channel: {u.channel_post.chat.title} | ID: {u.channel_post.chat.id}")
        elif u.message:
            print(f"Message: {u.message.text} | Chat ID: {u.message.chat_id} | Type: {u.message.chat.type}")
        elif u.my_chat_member:
            print(f"Chat Member Update: {u.my_chat_member.chat.title} | ID: {u.my_chat_member.chat.id}")

if __name__ == "__main__":
    asyncio.run(get_updates())
