import asyncio
from news_manager import NewsManager
import config
import logging

logging.basicConfig(level=logging.INFO)

async def test_airdrops():
    print("🚀 Testing Airdrop Fetcher...")
    news_mgr = NewsManager()
    
    # Manually fetch
    airdrops = await news_mgr.fetch_airdrop_opportunities()
    
    if not airdrops:
        print("ℹ️ No new airdrops found (or RSS feed empty).")
    else:
        print(f"✅ Found {len(airdrops)} airdrops:")
        for item in airdrops:
            print(f"- {item['title']} ({item['publisher']})")
            print(f"  Link: {item['link']}")
            print(f"  Sentiment: {item['sentiment'].get('sentiment', 'N/A')}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_airdrops())
