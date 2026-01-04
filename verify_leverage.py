import asyncio
import logging
import config
import trade_manager
import json
import os

# Setup Dummy Logger
logging.basicConfig(level=logging.ERROR)

async def test_leverage_and_routing():
    print("--- Test: Leverage & Routing ---")
    
    # 1. Reset/Mock Data
    if os.path.exists("test_trades.json"): os.remove("test_trades.json")
    if os.path.exists("test_history.json"): os.remove("test_history.json")
    
    # Override Config
    config.INITIAL_CAPITAL_CRYPTO_SPOT = 100.0
    config.INITIAL_CAPITAL_CRYPTO_FUTURE = 100.0
    config.CRYPTO_RISK_PER_TRADE = 0.5 # 50% risk
    
    # Enable Both
    config.ENABLE_SPOT_TRADING = True
    config.ENABLE_FUTURES_TRADING = True
    config.FUTURE_LEVERAGE = 10 # x10 Leverage
    
    # Mock Manager
    mgr = trade_manager.TradeManager()
    mgr.load_trades = lambda x: []
    mgr.save_trades = lambda: None
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

    # 2. Open Long Trade (Should be SPOT AND FUTURE)
    signal_long = {
        'market': 'CRYPTO',
        'symbol': 'BTC/USDT',
        'side': 'LONG',
        'entry': 50000,
        'take_profit': 55000,
        'stop_loss': 45000,
        'timestamp': '2025-01-01 10:00:00'
    }
    print(f"\nOpening LONG Signal (Entry: {signal_long['entry']}, SL: {signal_long['stop_loss']})...")
    mgr.open_trade(signal_long)
    
    open_trades = mgr.active_trades
    print(f"Active Trades Count: {len(open_trades)} (Expected 2)")
    
    spot_trade = next((t for t in open_trades if t['market'] == 'CRYPTO_SPOT'), None)
    fut_trade = next((t for t in open_trades if t['market'] == 'CRYPTO_FUTURE'), None)
    
    if spot_trade: print("✅ Spot Trade Created")
    else: print("❌ Spot Trade Missing")
        
    if fut_trade: print("✅ Future Trade Created")
    else: print("❌ Future Trade Missing")
    
    # 3. Verify Position Sizes via Close
    # Risk Amount = $50 (50% of 100)
    # SL Dist = 10%
    # Raw Pos = 50 / 0.10 = $500
    
    # Spot: Limited to Balance ($100)
    # Future: Limited to Balance * Lev (100 * 10 = $1000). So full $500 fits.
    
    print("\n--- Verifying Size Limit ---")
    
    # Close Spot
    mgr.close_trade(spot_trade, 'WIN', 55000, 0.1, mock_bot)
    # Expected Spot PnL: Position $100. Gain 10%. = $10. Balance -> $110.
    bal_spot, _ = mgr.calculate_balance('CRYPTO_SPOT')
    print(f"Spot Balance: {bal_spot} (Expected ~110.0)")
    
    # Close Future
    mgr.close_trade(fut_trade, 'WIN', 55000, 0.1, mock_bot)
    # Expected Future PnL: Position $500. Gain 10%. = $50. Balance -> $150.
    bal_fut, _ = mgr.calculate_balance('CRYPTO_FUTURE')
    print(f"Future Balance: {bal_fut} (Expected ~150.0)")
    
    if bal_fut > bal_spot:
        print("✅ SUCCESS: Future made more profit (Leverage Working)")
    else:
        print(f"❌ FAIL: Future did not outperform Spot. Future: {bal_fut}, Spot: {bal_spot}")

if __name__ == "__main__":
    asyncio.run(test_leverage_and_routing())
