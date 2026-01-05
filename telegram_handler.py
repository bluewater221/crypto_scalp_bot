import logging
import os
import asyncio
from telegram import Bot, InputFile
import config
# import chart_generator

logger = logging.getLogger(__name__)

async def send_signal(bot: Bot, signal_data, market_type, balance=None):
    """
    Sends signal to the appropriate Telegram channel.
    """
    channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID if market_type == 'CRYPTO' else config.TELEGRAM_STOCK_CHANNEL_ID
    
    if not channel_id:
        logger.warning(f"No channel ID for {market_type}. Skipping Telegram send.")
        if config.PAPER_TRADING:
            print(f"PAPER SIGNAL ({market_type}): {signal_data}")
        return

    # Generate Chart
    # Chart generation disabled to save memory (512MB limit)
    chart_path = None
    # chart_path = chart_generator.generate_chart(
    #     signal_data['df'], 
    #     signal_data['symbol'], 
    #     config.CRYPTO_TIMEFRAME if market_type == 'CRYPTO' else config.STOCK_TIMEFRAME,
    #     signal_data['side']
    # )
    
    # Format Message
    emoji = "🚀" if signal_data['side'] == 'LONG' else "📉"
    price_fmt = "${:,.6f}" if market_type == 'CRYPTO' else "₹{:,.2f}"
    currency = "$" if market_type == 'CRYPTO' else "₹"
    
    # Calculate Recommended Position Size
    size_str = ""
    if balance:
        risk_pct = signal_data.get('risk_pct', 0.01)
        risk_amt = balance * risk_pct
        entry = signal_data['entry']
        sl = signal_data['stop_loss']
        if entry != sl:
             dist_to_sl_pct = abs(entry - sl) / entry
             raw_pos = risk_amt / dist_to_sl_pct
             # Limit by balance (or leverage if we knew it, but let's keep it simple for now)
             actual_pos = min(raw_pos, balance) 
             size_str = f"Rec. Size: **{currency}{actual_pos:,.2f}**\n"

    # Unified Template Structure
    message = (
        f"{emoji} **{signal_data['symbol']}** ({signal_data['side']})\n"
        f"Entry: {price_fmt.format(signal_data['entry'])}\n"
        f"SL: {price_fmt.format(signal_data['stop_loss'])}\n"
        f"TP: {price_fmt.format(signal_data['take_profit'])}\n"
        f"Risk: {signal_data['risk_pct'] * 100:.1f}%\n"
        f"{size_str}"
        f"Setup: {signal_data['setup']}"
    )
    
    # Add AI Validation if present
    if 'ai_confidence' in signal_data:
        message += (
            f"\n\n🧠 **AI Validation**\n"
            f"Confidence: {signal_data['ai_confidence']}\n"
            f"Reasoning: _{signal_data['ai_reasoning']}_"
        )
        
    message += f"\n\n⚠️ Educational Only. DYOR."
    
    try:
        # Send Photo with Caption (If chart exists)
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, 'rb') as photo:
                await bot.send_photo(chat_id=channel_id, photo=photo, caption=message, parse_mode='Markdown')
            # Cleanup
            try:
                os.remove(chart_path)
            except:
                pass
        else:
            # Text Only (Crypto falls here now)
            await bot.send_message(chat_id=channel_id, text=message, parse_mode='Markdown')

        # Send Poll (Disabled per user request)
        # question = "What's your risk tolerance for this trade?"
        # options = ["conservative (0.5%)", "moderate (1%)", "aggressive (>1%)", "skip"]
        # await bot.send_poll(
        #     chat_id=channel_id,
        #     question=question,
        #     options=options,
        #     is_anonymous=True
        # )
        
        logger.info(f"Signal sent to {market_type} channel for {signal_data['symbol']}")

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")




