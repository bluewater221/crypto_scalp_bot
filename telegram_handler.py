import logging
import os
import asyncio
from telegram import Bot, InputFile
import config
import chart_generator

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
    chart_path = chart_generator.generate_chart(
        signal_data['df'], 
        signal_data['symbol'], 
        config.CRYPTO_TIMEFRAME if market_type == 'CRYPTO' else config.STOCK_TIMEFRAME,
        signal_data['side']
    )
    
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

async def send_news(bot: Bot, news_item, market_type):
    """
    Sends a formatted news message to the channel.
    """
    channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID if market_type == 'CRYPTO' else config.TELEGRAM_STOCK_CHANNEL_ID
    
    if not channel_id:
        return

    # News Formatting
    # 📰 MARKET NEWS
    # Title
    # Source - Time
    
    # Sentiment Emoji Map
    sentiment = news_item.get('sentiment', {})
    # Handle if sentiment is a dict (Gemini/TextBlob V2) or string (Legacy)
    if isinstance(sentiment, dict):
        sentiment_val = sentiment.get('sentiment', 'NEUTRAL')
        insight = sentiment.get('ai_insight')
    else:
        # Fallback if somehow string
        sentiment_val = str(sentiment)
        insight = None
        
    s_emoji = "⚪"
    if sentiment_val == 'BULLISH': s_emoji = "🟢"
    elif sentiment_val == 'BEARISH': s_emoji = "🔴"

    emoji = "₿" if market_type == 'CRYPTO' else "📈"
    
    # Add coin symbol to header if crypto
    coin_header = ""
    if market_type == 'CRYPTO' and news_item.get('currency'):
        coin_header = f" [{news_item['currency'].upper()}]"
    
    if news_item.get('type') == 'CHART':
         emoji = "📊"
         message = (
            f"📊 *EXPERT CHART ANALYSIS*{coin_header}\n"
            f"Sentiment: {s_emoji} {sentiment_val}\n\n"
            f"**{news_item['title']}**\n"
        )
    else:
        tickers = news_item.get('related_tickers', [])
        ticker_str = f"[{', '.join(tickers)}]" if tickers else ""
        
        # User Request: Use Stock/Crypto Name in header instead of generic "NEWS"
        # Logic: If we have tickers (e.g. [BTC], [RELIANCE]), use them.
        if ticker_str:
             header_text = f"{ticker_str} NEWS"
        else:
             # Fallback
             coin_header = f" [{news_item['currency'].upper()}]" if market_type == 'CRYPTO' and news_item.get('currency') else ""
             header_text = f"{market_type} NEWS{coin_header}"

        message = (
            f"{emoji} *{header_text}*\n"
            f"Sentiment: {s_emoji} {sentiment_val}\n\n"
            f"**{news_item['title']}**\n"
            f"{news_item.get('summary', '')}\n\n"
        )

        # Add Forex Context if present (Smart Context)
        if 'usdinr_data' in news_item:
            usdinr = news_item['usdinr_data']
            # USD/INR: Up means INR Weakens (Red for INR holder typically, but standard Green for price up)
            # Let's keep it neutral/descriptive
            message += (
                f"🇮🇳 **USD/INR**: ₹{usdinr['price']:,.2f} ({usdinr['pct_change']:+.2f}%) - {usdinr['trend']}\n\n"
            )

    # Add AI Insight if available
    if insight:
        message += f"{insight}\n\n"
        
    # message += f"[Read More]({news_item['link']})" # Removed per user request
    
    try:
        # Check if there is an image to send
        # Check if there is an image to send
        # User Request: "remove image feature only for charts and imp"
        # Since 'imp' (Important) is subjective and not flagged, we restrict to CHART type for now.
        show_image = False
        if news_item.get('type') == 'CHART':
             show_image = True

        if show_image and news_item.get('image_url'):
             await bot.send_photo(
                chat_id=channel_id,
                photo=news_item['image_url'],
                caption=message,
                parse_mode='Markdown'
            )
        else:
            await bot.send_message(
                chat_id=channel_id, 
                text=message, 
                parse_mode='Markdown'
            )
        logger.info(f"News sent to {market_type}: {news_item['title']}")
    except Exception as e:
        logger.error(f"Failed to send news: {e}")

async def send_airdrop(bot: Bot, airdrop_item):
    """
    Sends a formatted airdrop alert to the crypto channel.
    """
    channel_id = config.TELEGRAM_CRYPTO_CHANNEL_ID
    
    if not channel_id:
        return

    # Airdrop Formatting
    # 🪂 NEW AIRDROP OPPORTUNITY 🪂
    # Title
    # Source
    
    sentiment = airdrop_item.get('sentiment', {})
    sentiment_val = sentiment.get('sentiment', 'NEUTRAL') if isinstance(sentiment, dict) else 'NEUTRAL'
    insight = sentiment.get('ai_insight') if isinstance(sentiment, dict) else None
    
    s_emoji = "⚪"
    if sentiment_val == 'BULLISH': s_emoji = "🟢"
    elif sentiment_val == 'BEARISH': s_emoji = "🔴"

    message = (
        f"🪂 *NEW AIRDROP OPPORTUNITY* 🪂\n"
        f"Sentiment: {s_emoji} {sentiment_val}\n"
        f"Estimated Reward: 💰 **{sentiment.get('estimated_reward', 'Unknown')}**\n"
        f"Requirements: 📋 **{sentiment.get('requirements', 'None')}**\n\n"
        f"**{airdrop_item['title']}**\n"
    )

    if insight:
        message += f"{insight}\n\n"
        
    message += f"🔗 [Airdrop Details & Steps]({airdrop_item['link']})\n\n"
    message += "⚠️ DyOR. Never share private keys or seed phrases."
    
    try:
        await bot.send_message(
            chat_id=channel_id, 
            text=message, 
            parse_mode='Markdown'
        )
        logger.info(f"Airdrop alert sent: {airdrop_item['title']}")
    except Exception as e:
        logger.error(f"Failed to send airdrop alert: {e}")


