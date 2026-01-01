
import asyncio
import pandas as pd
import ccxt.async_support as ccxt
import yfinance as yf
import config
import signals
import logging
from datetime import datetime, timedelta

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
BACKTEST_DAYS = 30
CRYPTO_TIMEFRAME = '1m'
STOCK_TIMEFRAME = '5m'

async def fetch_historical_crypto(symbol, limit_days=BACKTEST_DAYS):
    """Fetches historical OHLCV data for Crypto from Kraken."""
    exchange = ccxt.kraken()
    try:
        since = exchange.parse8601((datetime.utcnow() - timedelta(days=limit_days)).isoformat())
        ohlcv = await exchange.fetch_ohlcv(symbol, CRYPTO_TIMEFRAME, since)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching crypto history for {symbol}: {e}")
        return None
    finally:
        await exchange.close()

def fetch_historical_stock(symbol, limit_days=BACKTEST_DAYS):
    """Fetches historical OHLCV data for Stock from Yahoo Finance."""
    try:
        # yfinance 5m data is limited to 60 days, so 30 is fine
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{limit_days}d", interval=STOCK_TIMEFRAME)
        if df.empty:
            return None
        df = df.reset_index()
        # Normalize columns
        df = df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        # Ensure UTC timezone for consistency or remove tz to prevent mismatch issues
        if df['timestamp'].dt.tz is not None:
             df['timestamp'] = df['timestamp'].dt.tz_convert(None)
        return df
    except Exception as e:
        logger.error(f"Error fetching stock history for {symbol}: {e}")
        return None

def resample_to_5m(df_1m):
    """Resamples 1m dataframe to 5m for Crypto HTF analysis."""
    df_5m = df_1m.set_index('timestamp').resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    return df_5m

async def simulate_trades(df, symbol, asset_type):
    """Replays the signals logic over the dataframe."""
    trades = []
    active_trade = None
    
    logger.info(f"Simulating {symbol} ({len(df)} candles)...")
    
    # Start after 200 candles to allow EMA 50 (on 5m) to warmup if calculating on the fly
    start_index = 200 
    
    for i in range(start_index, len(df)):
        # Create a window of data simulatin "live" state
        window = df.iloc[:i+1].copy()
        current_candle = window.iloc[-1]
        
        # Check Entry
        if active_trade is None:
            signal_data = None
            
            if asset_type == 'CRYPTO':
                # Generate 5m Data from current 1m window
                # We perform resampling on the available window to mimic live state
                # Optimally we should have pre-resampled, but this ensures no lookahead bias
                window_5m = resample_to_5m(window)
                if len(window_5m) > 50:
                    signal_data = await signals.analyze_crypto(None, symbol, df_1m=window, df_5m=window_5m)
            else:
                # Stock (already 5m)
                signal_data = await signals.analyze_stock(symbol, df=window)
                
            if signal_data:
                active_trade = {
                    'entry_time': current_candle['timestamp'],
                    'symbol': symbol,
                    'side': signal_data['side'],
                    'entry_price': signal_data['entry'],
                    'sl': signal_data['stop_loss'],
                    'tp': signal_data['take_profit'],
                    'setup': signal_data['setup']
                }
        
        # Check Exit (if active)
        else:
            outcome = None
            pnl_pct = 0
            
            # BUY Trade Logic
            if active_trade['side'] == 'LONG' or active_trade['side'] == 'BUY': # Normalize
                if current_candle['low'] <= active_trade['sl']:
                    outcome = 'STOP_LOSS'
                    pnl_pct = (active_trade['sl'] - active_trade['entry_price']) / active_trade['entry_price']
                elif current_candle['high'] >= active_trade['tp']:
                    outcome = 'TAKE_PROFIT'
                    pnl_pct = (active_trade['tp'] - active_trade['entry_price']) / active_trade['entry_price']
                    
            # SELL Trade Logic
            elif active_trade['side'] == 'SHORT' or active_trade['side'] == 'SELL':
                if current_candle['high'] >= active_trade['sl']:
                    outcome = 'STOP_LOSS'
                    pnl_pct = (active_trade['entry_price'] - active_trade['sl']) / active_trade['entry_price']
                elif current_candle['low'] <= active_trade['tp']:
                    outcome = 'TAKE_PROFIT'
                    pnl_pct = (active_trade['entry_price'] - active_trade['tp']) / active_trade['entry_price']

            if outcome:
                active_trade['exit_time'] = current_candle['timestamp']
                active_trade['outcome'] = outcome
                active_trade['pnl_pct'] = pnl_pct * 100 # In Percent
                active_trade['exit_price'] = active_trade['sl'] if outcome == 'STOP_LOSS' else active_trade['tp']
                
                trades.append(active_trade)
                active_trade = None

    return trades

async def run_backtest():
    all_trades = []
    
    # 1. Backtest Crypto (High Volume Pair)
    # Using BTC and SOL for diversity
    chk_pairs = ['BTC/USDT', 'SOL/USDT']
    for pair in chk_pairs: 
        logger.info(f"Fetching data for {pair}...")
        df = await fetch_historical_crypto(pair, limit_days=7) # 7 days for speed in demo, update to 30 for full
        if df is not None:
            trades = await simulate_trades(df, pair, 'CRYPTO')
            all_trades.extend(trades)
            
    # 2. Backtest Stocks (High Liquidity)
    chk_stocks = ['RELIANCE.NS', 'TCS.NS'] 
    for symbol in chk_stocks:
        logger.info(f"Fetching data for {symbol}...")
        df = fetch_historical_stock(symbol, limit_days=7) # 7 days
        if df is not None:
            trades = await simulate_trades(df, symbol, 'STOCK')
            all_trades.extend(trades)

    # 3. Report
    if not all_trades:
        print("No trades generated.")
        return

    df_res = pd.DataFrame(all_trades)
    print("\n--- 📊 BACKTEST REPORT (Last 7 Days) ---")
    print(f"Total Trades: {len(df_res)}")
    print(f"Wins: {len(df_res[df_res['outcome'] == 'TAKE_PROFIT'])}")
    print(f"Losses: {len(df_res[df_res['outcome'] == 'STOP_LOSS'])}")
    
    if len(df_res) > 0:
        win_rate = (len(df_res[df_res['outcome'] == 'TAKE_PROFIT']) / len(df_res)) * 100
        total_pnl = df_res['pnl_pct'].sum()
        
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Net PnL (Without Fees): {total_pnl:.2f}%")
        print(f"Avg PnL per Trade: {df_res['pnl_pct'].mean():.2f}%")
        
        print("\n--- Recent Trades ---")
        print(df_res[['symbol', 'side', 'outcome', 'pnl_pct']].tail())
        
        # Save to CSV
        df_res.to_csv("backtest_results.csv", index=False)
        print("\nSaved detailed results to backtest_results.csv")

if __name__ == "__main__":
    asyncio.run(run_backtest())
