
import asyncio
import market_data
import logging

logging.basicConfig(level=logging.INFO)

async def test_market_pulse():
    print("--- Testing Market Pulse APIs ---")
    
    # 1. Crypto Fear & Greed
    print("\n1. Fetching Fear & Greed...")
    fng = market_data.get_fear_and_greed_index()
    print(f"Result: {fng}")
    
    # 2. Stock Market Status
    print("\n2. Fetching Nifty 50 Trend...")
    nifty = await market_data.get_market_status()
    print(f"Result: {nifty}")
    
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_market_pulse())
