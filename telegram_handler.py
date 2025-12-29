import logging
import os
import asyncio
from telegram import Bot, InputFile
import config
import chart_generator

logger = logging.getLogger(__name__)

async def send_signal(bot: Bot, signal_data, market_type):
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
    chart_path = chart_generator.generate_chart(
        signal_data['df'], 
        signal_data['symbol'], 
        config.CRYPTO_TIMEFRAME if market_type == 'CRYPTO' else config.STOCK_TIMEFRAME,
        signal_data['side']
    )
    
    # Format Message
    # 🚀 BTC/USDT LONG | Entry: $67,250 | SL: $66,914 | TP: $67,832 | Risk: 0.5% | RSI: 28 📉
    emoji = "🚀" if signal_data['side'] == 'LONG' else "📉"
    price_fmt = "${:,.2f}" if market_type == 'CRYPTO' else "₹{:,.2f}"
    
    message = (
        f"{emoji} {signal_data['symbol']} {signal_data['side']} | "
        f"Entry: {price_fmt.format(signal_data['entry'])} | "
        f"SL: {price_fmt.format(signal_data['stop_loss'])} | "
        f"TP: {price_fmt.format(signal_data['take_profit'])} | "
        f"Risk: {signal_data['risk_pct']}% | "
        f"Setup: {signal_data['setup']}"
        f"\n\n⚠️ Educational Only. DYOR."
    )
    
    try:
        # Send Photo with Caption
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, 'rb') as photo:
                await bot.send_photo(chat_id=channel_id, photo=photo, caption=message)
            # Cleanup
            try:
                os.remove(chart_path)
            except:
                pass
        else:
            await bot.send_message(chat_id=channel_id, text=message)

        # Send Poll
        question = "What's your risk tolerance for this trade?"
        options = ["conservative (0.5%)", "moderate (1%)", "aggressive (>1%)", "skip"]
        await bot.send_poll(
            chat_id=channel_id,
            question=question,
            options=options,
            is_anonymous=True
        )
        
        logger.info(f"Signal sent to {market_type} channel for {signal_data['symbol']}")

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
