import asyncio
import logging
from datetime import datetime
import config
import trade_manager
import json
import os

# Setup Dummy Logger
logging.basicConfig(level=logging.ERROR)

async def test_spot_future_split():
    print("--- Test: Spot vs Future Split & Balance Tracking ---")
    
    # 1. Reset/Mock Data
    if os.path.exists("test_trades.json"): os.remove("test_trades.json")
    if os.path.exists("test_history.json"): os.remove("test_history.json")
    
    # Override Config for Test
    config.INITIAL_CAPITAL_CRYPTO_SPOT = 100.0
    config.INITIAL_CAPITAL_CRYPTO_FUTURE = 100.0
    config.CRYPTO_RISK_PER_TRADE = 0.5 # 50% risk for bold moves
    
    # Mock Manager
    mgr = trade_manager.TradeManager()
    mgr.load_trades = lambda x: [] # mock load
    mgr.save_trades = lambda: None # mock save
    trade_manager.TRADES_FILE = "test_trades.json"
    trade_manager.HISTORY_FILE = "test_history.json"
    mgr.active_trades = []
    mgr.history = []
    
    # Mock Bot
    class MockBot:
        async def send_message(self, chat_id, text, parse_mode):
            print(f"\n[MockBot] Msg to {chat_id}:\n{text}\n")
            return
    
    mock_bot = MockBot()
    
    # 2. Open Long Trade (Should be SPOT)
    signal_long = {
        'market': 'CRYPTO',
        'symbol': 'BTC/USDT',
        'side': 'LONG',
        'entry': 50000,
        'take_profit': 55000,
        'stop_loss': 45000,
        'timestamp': '2025-01-01 10:00:00'
    }
    mgr.open_trade(signal_long)
    trade_long = mgr.active_trades[0]
    print(f"Long Trade Market Type: {trade_long['market']} [{'✅' if trade_long['market'] == 'CRYPTO_SPOT' else '❌'}]")
    
    # 3. Open Short Trade (Should be FUTURE)
    signal_short = {
        'market': 'CRYPTO',
        'symbol': 'ETH/USDT',
        'side': 'SHORT',
        'entry': 3000,
        'take_profit': 2000,
        'stop_loss': 4000,
        'timestamp': '2025-01-01 10:00:00'
    }
    mgr.open_trade(signal_short)
    trade_short = mgr.active_trades[1]
    print(f"Short Trade Market Type: {trade_short['market']} [{'✅' if trade_short['market'] == 'CRYPTO_FUTURE' else '❌'}]")

    # 4. Close Long Trade (WIN)
    # Risk = 50% of $100 = $50
    # Entry=50k, SL=45k (10% diff) -> Position Size = $50 / 0.10 = $500 (But capped at Balance $100) -> $100 Position
    # PnL = (55k - 50k) * ($100/50k) = 5000 * 0.002 = $10
    print("\nClosing Long Trade (WIN)...")
    mgr.close_trade(trade_long, 'WIN', 55000, 0.1, mock_bot)
    
    bal_spot, _ = mgr.calculate_balance('CRYPTO_SPOT')
    print(f"Spot Balance: ${bal_spot:.2f} (Expected ~$110.00)")
    
    # 5. Close Short Trade (LOSS)
    # Risk = 50% of $100 = $50
    # Entry=3000, SL=4000 (33% diff) -> Pos = 50 / 0.33 = $150 (Capped at $100)
    # PnL (Short) = (3000 - 3500) * (100/3000) = -500 * 0.0333 = -$16.66
    print("\nClosing Short Trade (LOSS at 3500)...")
    mgr.close_trade(trade_short, 'LOSS', 3500, -0.1, mock_bot)
    
    bal_future, _ = mgr.calculate_balance('CRYPTO_FUTURE')
    print(f"Future Balance: ${bal_future:.2f} (Expected ~$83.33)") 
    
    # 6. Verify Checks in Stats
    stats = mgr.get_stats()
    print("\n--- Generated Stats ---")
    print(stats)
    
    if "Crypto Spot" in stats and "Crypto Future" in stats:
        print("\n✅ Verification SUCCESS: Separate Stats shown.")
    else:
        print("\n❌ Verification FAILED: Stats missing separation.")

if __name__ == "__main__":
    asyncio.run(test_spot_future_split())
