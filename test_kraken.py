import ccxt
import asyncio

async def test_kraken():
    print("Testing Kraken connection...")
    exchange = ccxt.kraken()
    try:
        # Load markets
        markets = await asyncio.to_thread(exchange.load_markets)
        print(f"Kraken loaded {len(markets)} markets.")
        
        # Fetch BTC ticker
        ticker = await asyncio.to_thread(exchange.fetch_ticker, 'BTC/USDT')
        print(f"BTC Price on Kraken: {ticker['last']}")
        print("Kraken connection SUCCESSFUL.")
    except Exception as e:
        print(f"Kraken connection FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_kraken())
