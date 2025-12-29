import mplfinance as mpf
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

CHART_DIR = "charts"
if not os.path.exists(CHART_DIR):
    os.makedirs(CHART_DIR)

def generate_chart(df, symbol, timeframe, signal_side):
    """
    Generates a candlestick chart and saves it.
    df: DataFrame with OHLCV data and indicators
    """
    try:
        # Prepare DataFrame for mplfinance (needs DatetimeIndex)
        chart_df = df.copy()
        if 'timestamp' in chart_df.columns:
            chart_df.set_index('timestamp', inplace=True)
        
        # Slice last 50 candles for clarity
        chart_df = chart_df.tail(200) # Increased to 200
        
        # Setup Style
        mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, style='nightclouds')
        
        filename = f"{CHART_DIR}/{symbol.replace('/', '_')}_{signal_side}.png"
        
        # Add Plots (Indicators)
        addplots = []
        if 'ema_fast' in chart_df.columns and 'ema_slow' in chart_df.columns:
            addplots.append(mpf.make_addplot(chart_df['ema_fast'], color='cyan', width=1))
            addplots.append(mpf.make_addplot(chart_df['ema_slow'], color='orange', width=1))
        
        # RSI Panel if available? Maybe too complex for simple scalping chart.
        # Let's stick to Price + MA for Stocks, Price for Crypto (maybe Bollinger or just nothing for now, minimal)
        
        title = f"{symbol} ({timeframe}) - {signal_side}"
        
        mpf.plot(
            chart_df,
            type='candle',
            style=s,
            title=title,
            volume=True,
            addplot=addplots,
            savefig=filename,
            tight_layout=True
        )
        
        return filename
    except Exception as e:
        logger.error(f"Error generating chart for {symbol}: {e}")
        return None
