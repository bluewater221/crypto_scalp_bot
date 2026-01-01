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
        # Custom style lines removed to prevent keyword error. Using built-in style directly.
        
        filename = f"{CHART_DIR}/{symbol.replace('/', '_')}_{signal_side}.png"
        
        # Add Plots (Indicators)
        addplots = []
        
        # 1. EMAs (Main Panel)
        if 'ema_fast' in chart_df.columns and 'ema_slow' in chart_df.columns:
            addplots.append(mpf.make_addplot(chart_df['ema_fast'], color='cyan', width=1))
            addplots.append(mpf.make_addplot(chart_df['ema_slow'], color='orange', width=1))

        # 2. Support/Resistance (Main Panel - Simple rolling lookback)
        # Calculate recent high/low for lines
        if len(chart_df) > 20:
             recent_high = chart_df['high'].rolling(window=20).max()
             recent_low = chart_df['low'].rolling(window=20).min()
             addplots.append(mpf.make_addplot(recent_high, color='green', linestyle='dashed', width=0.8, alpha=0.6))
             addplots.append(mpf.make_addplot(recent_low, color='red', linestyle='dashed', width=0.8, alpha=0.6))

        # 3. RSI (New Panel)
        if 'rsi' in chart_df.columns:
            addplots.append(mpf.make_addplot(chart_df['rsi'], panel=1, color='purple', width=1.5, ylabel='RSI'))
            # Overbought/Oversold fill/lines handled in plot args or extra plots? 
            # Simple lines:
            line_30 = [30] * len(chart_df)
            line_70 = [70] * len(chart_df)
            addplots.append(mpf.make_addplot(line_30, panel=1, color='gray', linestyle='dotted', width=0.8))
            addplots.append(mpf.make_addplot(line_70, panel=1, color='gray', linestyle='dotted', width=0.8))

        # 4. Signal Marker (Arrow)
        # We place a marker on the LAST candle because that's where the signal was generated
        if len(chart_df) > 0:
            last_idx = chart_df.index[-1]
            
            # Create a Series relative to the dataframe index, full of NaNs
            marker_series = [float('nan')] * len(chart_df)
            
            if signal_side == 'LONG':
                # Green Arrow UP below the Low
                marker_price = chart_df.iloc[-1]['low'] * 0.999
                marker_series[-1] = marker_price
                addplots.append(mpf.make_addplot(marker_series, type='scatter', markersize=200, marker='^', color='lime'))
                
            elif signal_side == 'SHORT':
                # Red Arrow DOWN above the High
                marker_price = chart_df.iloc[-1]['high'] * 1.001
                marker_series[-1] = marker_price
                addplots.append(mpf.make_addplot(marker_series, type='scatter', markersize=200, marker='v', color='red'))

        title = f"{symbol} ({timeframe}) - {signal_side} Setup"
        
        mpf.plot(
            chart_df,
            type='candle',
            style='nightclouds', # Use standard style name directly to avoid custom object errors
            title=title,
            volume=True,
            addplot=addplots,
            savefig=filename,
            tight_layout=True,
            panel_ratios=(3, 1) # 3 parts Price, 1 part RSI/Volume
        )
        
        return filename
    except Exception as e:
        logger.error(f"Error generating chart for {symbol}: {e}")
        return None
