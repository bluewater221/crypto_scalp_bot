import asyncio
import logging
import trade_manager
import os

# Setup Dummy Logger
logging.basicConfig(level=logging.ERROR)

async def test_file_separation():
    print("--- Test: File Separation ---")
    
    # 1. Cleanup
    for f in ['trades_spot.json', 'trades_future.json', 'history_spot.json', 'history_future.json']:
        if os.path.exists(f): os.remove(f)
    
    # 2. Init Managers
    spot_mgr = trade_manager.TradeManager(
        market_tag='CRYPTO_SPOT',
        trades_file='trades_spot.json',
        history_file='history_spot.json',
        initial_capital=100
    )
    
    future_mgr = trade_manager.TradeManager(
        market_tag='CRYPTO_FUTURE',
        trades_file='trades_future.json',
        history_file='history_future.json',
        initial_capital=100,
        leverage=5
    )
    
    # 3. Create Dummy Signals
    signal = {
        'symbol': 'BTC/USDT',
        'market': 'CRYPTO', # Base market, but mgr ignores it for tag usually or we pass specific
        'side': 'LONG',
        'entry': 50000,
        'take_profit': 55000,
        'stop_loss': 45000,
        'timestamp': '2025-01-01'
    }
    
    spot_mgr.open_trade(signal)
    future_mgr.open_trade(signal)
    
    # 4. Check Files
    if os.path.exists('trades_spot.json'):
        print("✅ trades_spot.json created.")
        with open('trades_spot.json', 'r') as f:
            print(f"Content: {f.read()}")
    else:
        print("❌ trades_spot.json MISSING.")

    if os.path.exists('trades_future.json'):
        print("✅ trades_future.json created.")
        with open('trades_future.json', 'r') as f:
            print(f"Content: {f.read()}")
    else:
        print("❌ trades_future.json MISSING.")

if __name__ == "__main__":
    asyncio.run(test_file_separation())
