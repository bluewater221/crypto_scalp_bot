import asyncio
import logging
import market_data
import signals
import config

# Configure logging to print to console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# Suppress noisy checks
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("ccxt").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def test_signals():
    print("--- Starting Diagnostic Run ---")
    exchange = market_data.get_crypto_exchange()
    if not exchange:
        print("Failed to init exchange")
        return

    # specific_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    # specific_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    specific_pairs = config.CRYPTO_PAIRS # Test ALL configured pairs

    for symbol in specific_pairs:
        print(f"\nAnalyzing {symbol}...")
        try:
            # We call analyze_crypto directly. 
            # The modified signals.py should log DEBUG messages explaining rejections.
            print(f"  > Fetching data and analyzing...")
            result = await signals.analyze_crypto(exchange, symbol)
            
            if result:
                print(f"✅ SIGNAL FOUND: {result['side']} at {result['entry']}")
            else:
                print(f"❌ No Signal")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_signals())
