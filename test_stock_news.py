import asyncio
from news_manager import NewsManager
import logging

logging.basicConfig(level=logging.INFO)

async def test_stock_news():
    print("🚀 Testing Stock News Fetcher (Economic Times)...")
    news_mgr = NewsManager()
    
    # Manually fetch
    news = await news_mgr.fetch_stock_news()
    
    if not news:
        print("ℹ️ No new items found in Economic Times feed.")
    else:
        print(f"✅ Found {len(news)} items:")
        for item in news:

            print(f"- {item['title']} ({item['publisher']})")
            print(f"  Summary: {item.get('summary', 'N/A')}")
            print(f"  Link: {item['link']}")
            print(f"  Sentiment: {item['sentiment']['sentiment']}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_stock_news())
