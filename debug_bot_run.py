import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# Load Token
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# QUIET LOGGING
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    
    if chat:
        msg = f"CAPTURED|{chat.title}|{chat.id}"
        print(msg)
        
        # Write to file for reliability
        with open("ids.txt", "a", encoding="utf-8") as f:
            f.write(f"{chat.title}={chat.id}\n")
            
        try:
            await update.effective_message.reply_text(f"✅ ID Saved: {chat.id}")
        except:
            pass

def main():
    if not TOKEN:
        return

    print("🚀 Bot Started. Waiting...")
    # Clear file
    with open("ids.txt", "w") as f: f.write("")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, log_update))
    application.run_polling()

if __name__ == '__main__':
    main()
