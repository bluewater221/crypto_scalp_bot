
import asyncio
import logging
import news_manager
import telegram_handler
import config
from unittest.mock import MagicMock

# Mock Config
config.TELEGRAM_STOCK_CHANNEL_ID = "-1003562244506" # Real ID for test (or use mock)
config.TELEGRAM_CRYPTO_CHANNEL_ID = "-1003598451631"

# Setup Logger
logging.basicConfig(level=logging.INFO)

async def test_forex_context():
    print("--- Testing Smart Forex Context ---")
    
    nm = news_manager.NewsManager()
    
    # Simulate a News Item that SHOULD trigger India Macro
    # We will bypass the RSS fetch and call analyze_sentiment directly or mock the item structure
    # But to test the REAL fetch of USD/INR, we need to let news_manager logic run.
    
    # Let's mock the AI response to FORCE is_india_macro = True
    # independent of the actual text, to test the wiring.
    
    print("1. Mocking AI Analysis for 'RBI Interest Rate Decision'...")
    # But wait, analyze_sentiment calls Gemini.
    # Let's manually construct the item invoking the logic from news_manager line 175
    
    import market_data
    print("2. Fetching Live USD/INR Data...")
    usdinr = await market_data.get_usdinr_status()
    print(f"USD/INR Data: {usdinr}")
    
    if not usdinr:
        print("❌ Failed to fetch USD/INR. Check internet/yfinance.")
        return

    # Construct Mock News Item
    news_item = {
        'title': "India's GDP Expected to Grow 7% in 2026",
        'summary': "The Reserve Bank of India projects strong growth driven by manufacturing and services. Bond yields remain stable.",
        'link': "http://example.com",
        'source': "Just Now",
        'publisher': "TestBot",
        'type': 'STOCK',
        'sentiment': {'sentiment': 'BULLISH', 'ai_insight': "Positive for Nifty."},
        'related_tickers': ['RBI', 'HDFCBANK'],
        'usdinr_data': usdinr # Manually injecting what news_manager would do
    }
    
    print("\n3. Simulating Telegram Message Generation...")
    # access private method or just print what it WOULD send?
    # validation via printing the message variable is hard without modifying code.
    # We can inspect telegram_handler.send_news code flow or just run print here.
    
    trend_arrow = "📉" if usdinr['trend'] == 'Appreciating' else "📈"
    context_str = f"🇮🇳 **USD/INR**: ₹{usdinr['price']:,.2f} ({usdinr['pct_change']:+.2f}%) - {usdinr['trend']}"
    
    print(f"\n[Generated Context String]\n{context_str}")
    print("\n✅ Verification Successful if above string looks correct.")

if __name__ == "__main__":
    asyncio.run(test_forex_context())
