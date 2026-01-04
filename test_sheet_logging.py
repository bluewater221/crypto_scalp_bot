import logging
import asyncio
import sheets
import config
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_logging():
    print("📝 Testing Google Sheets Logging...")
    
    # 1. Test log_signal
    test_signal = {
        'symbol': 'BTC/USDT',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'side': 'LONG',
        'entry': 95000.0,
        'stop_loss': 94000.0,
        'take_profit': 97000.0,
        'setup': 'Test Signal'
    }
    print(f"🚀 Logging test signal for {test_signal['symbol']}...")
    sheets.log_signal(test_signal)
    
    # 2. Test log_closed_trade
    test_trade = {
        'id': 'test-123',
        'symbol': 'BTC/USDT',
        'market': 'CRYPTO_SPOT',
        'side': 'LONG',
        'outcome': 'WIN',
        'pnl_pct': 0.02,
        'entry': 95000.0,
        'sl': 94000.0,
        'tp': 97000.0,
        'close_price': 96900.0,
        'risk_pct': 0.01,
        'open_time': '2026-01-01 10:00:00',
        'close_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    print(f"💰 Logging test closed trade for {test_trade['symbol']}...")
    sheets.log_closed_trade(test_trade)
    
    # 3. Test News Persistence
    test_news_id = "test-news-" + datetime.now().strftime('%H%M%S')
    print(f"📰 Logging test seen news ID: {test_news_id}...")
    sheets.log_seen_news(test_news_id)
    
    seen_ids = sheets.fetch_seen_news()
    if test_news_id in seen_ids:
        print("✅ News ID persistence verified!")
    else:
        print("❌ News ID persistence failed!")

    print("\n✅ Sheet testing complete. Please check your Google Sheet for 'Signals', 'History', and 'Seen_News' tabs.")

if __name__ == "__main__":
    asyncio.run(test_logging())
