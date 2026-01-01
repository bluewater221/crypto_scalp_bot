
def generate_demo_airdrop_final():
    # Mock Airdrop Data
    airdrop_item = {
        'title': 'SuperNova Protocol Testnet',
        'link': 'https://supernova.io/airdrop',
        'sentiment': {
            'sentiment': 'BULLISH',
            'ai_insight': 'Confirmed 5M token allocation for testnet users.',
            'estimated_value': '$50-$200',
            'requirements': 'Connect Wallet, Bridge Sepolia ETH, Mint NFT'
        }
    }

    # --- Formatting Logic from telegram_handler.py ---
    sentiment = airdrop_item.get('sentiment', {})
    sentiment_val = sentiment.get('sentiment', 'NEUTRAL')
    insight = sentiment.get('ai_insight')
    
    s_emoji = "⚪"
    if sentiment_val == 'BULLISH': s_emoji = "🟢"
    elif sentiment_val == 'BEARISH': s_emoji = "🔴"

    message = (
        f"🪂 *NEW AIRDROP OPPORTUNITY* 🪂\n"
        f"Potential: {s_emoji} {sentiment_val}\n"
        f"Value: 💰 **{sentiment.get('estimated_value', 'Unknown')}**\n"
        f"Requirements: 📋 **{sentiment.get('requirements', 'None')}**\n\n"
        f"**{airdrop_item['title']}**\n"
    )

    if insight:
        message += f"{insight}\n\n"
        
    message += f"🔗 [Airdrop Details & Steps]({airdrop_item['link']})\n\n"
    message += "⚠️ DyOR. Never share private keys or seed phrases."
    # ------------------------------------------------

    print("--- [PREVIEW: AIRDROP ALERT (FINAL)] ---")
    print(message)
    print("----------------------------------------")

if __name__ == "__main__":
    generate_demo_airdrop_final()
