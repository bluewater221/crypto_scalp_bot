
def generate_demo():
    # Mock Signal Data
    signal_data = {
        'symbol': 'BTC/USDT',
        'side': 'LONG',
        'entry': 67250.50,
        'stop_loss': 66914.20,
        'take_profit': 67832.80,
        'risk_pct': 0.005,
        'setup': 'RSI Reversal (w/ 5m Trend)',
        'ai_confidence': '88%',
        'ai_reasoning': 'Bullish divergence detected on 1m timeframe with increasing volume.'
    }
    market_type = 'CRYPTO'

    # --- Formatting Logic from telegram_handler.py ---
    emoji = "🚀" if signal_data['side'] == 'LONG' else "📉"
    price_fmt = "${:,.2f}" if market_type == 'CRYPTO' else "₹{:,.2f}"
    
    message = (
        f"{emoji} **{signal_data['symbol']}** ({signal_data['side']})\n"
        f"Entry: {price_fmt.format(signal_data['entry'])}\n"
        f"SL: {price_fmt.format(signal_data['stop_loss'])}\n"
        f"TP: {price_fmt.format(signal_data['take_profit'])}\n"
        f"Risk: {signal_data['risk_pct'] * 100}%\n"
        f"Setup: {signal_data['setup']}"
    )
    
    if 'ai_confidence' in signal_data:
        message += (
            f"\n\n🧠 **AI Validation**\n"
            f"Confidence: {signal_data['ai_confidence']}\n"
            f"Reasoning: _{signal_data['ai_reasoning']}_"
        )
        
    message += f"\n\n⚠️ Educational Only. DYOR."
    # ------------------------------------------------

    print("--- [PREVIEW: CRYPTO SIGNAL] ---")
    print(message)
    print("--------------------------------")
    print("(Plus a Chart Image 📸)")

if __name__ == "__main__":
    generate_demo()
