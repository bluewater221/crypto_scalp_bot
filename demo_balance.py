
def generate_demo_stats():
    # Mock Config
    INITIAL_CAPITAL_STOCK = 10000
    INITIAL_CAPITAL_CRYPTO = 100
    
    # Mock Calculated Values (Simulating some trades)
    stock_bal = 10150.50 # +1.5%
    stock_growth = 1.50
    
    crypto_bal = 98.50 # -1.5%
    crypto_growth = -1.50
    
    wins = 3
    total = 5
    win_rate = 60.0

    stats_msg = (
        f"📊 **Portfolio Performance**\n\n"
        f"📈 **Stocks**\n"
        f"Balance: ₹{stock_bal:,.2f}\n"
        f"Growth: {stock_growth:+.2f}%\n\n"
        f"💰 **Crypto**\n"
        f"Balance: ${crypto_bal:,.2f}\n"
        f"Growth: {crypto_growth:+.2f}%\n\n"
        f"🏆 **Trade Stats**\n"
        f"Win Rate: {win_rate:.1f}% ({wins}/{total})\n"
        f"Total Trades: {total}"
    )

    print("--- [PREVIEW: /stats COMMAND OUTPUT] ---")
    print(stats_msg)
    print("----------------------------------------")

if __name__ == "__main__":
    generate_demo_stats()
