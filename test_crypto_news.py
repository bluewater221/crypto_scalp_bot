import asyncio
from news_manager import NewsManager
import logging
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)

async def test_crypto_news():
    print("🚀 Testing Crypto News Coin Mentions...")
    news_mgr = NewsManager()
    
    # Mocking a response with currency
    news = news_mgr.fetch_crypto_news()
    
    if not news:
        print("ℹ️ No new crypto items found.")
    else:
        print(f"✅ Found {len(news)} items:")
        for item in news:
            coin = item.get('currency', 'N/A')
            print(f"- {item['title']} (Coin: {coin})")
            print(f"  Sentiment: {item['sentiment']['sentiment']}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_crypto_news())
