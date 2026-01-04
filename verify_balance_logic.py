import logging
import asyncio
import trade_manager
import config

# Setup logging
logging.basicConfig(level=logging.INFO)

async def verify_balance():
    print("📈 Verifying Portfolio Balance Calculation Logic...")
    
    # Initialize Crypto Spot Manager
    spot_mgr = trade_manager.TradeManager(
        market_tag='CRYPTO_SPOT',
        trades_file='trades_spot.json',
        history_file='history_spot.json',
        initial_capital=config.INITIAL_CAPITAL_CRYPTO_SPOT,
        leverage=1
    )
    
    print("\n" + "="*40)
    print(f"Manager: {spot_mgr.market_tag}")
    print(f"Initial Capital: ${spot_mgr.initial_capital}")
    print(f"History Records: {len(spot_mgr.history)}")
    
    balance = spot_mgr.calculate_balance()
    print(f"Calculated Balance: ${balance:,.2f}")
    
    if balance > 0:
        print("✅ Balance is positive and properly restored.")
    else:
        print("❌ Balance is still zero or negative. Checking why...")
        if not spot_mgr.history:
            print("💡 Reason: No history records found for this market tag in the sheet.")
            
    print("="*40 + "\n")

if __name__ == "__main__":
    asyncio.run(verify_balance())
