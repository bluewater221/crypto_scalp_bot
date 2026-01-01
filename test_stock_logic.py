import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio

async def test_stocks(symbol="RELIANCE.NS"):
    print(f"\n🚀 Testing Stock Fetch for {symbol}...")
    try:
        df = yf.download(tickers=symbol, period='5d', interval='15m', progress=False)
        if df.empty:
            print(f"❌ No data found for {symbol}.")
            return

        # Flatten multi-index columns if present (common in new yfinance versions)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.reset_index(inplace=True)
        # Standardize columns to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        if 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        
        # Calculate EMA
        df['ema_fast'] = ta.ema(df['close'], length=9)
        df['ema_slow'] = ta.ema(df['close'], length=21)
        df['vol_avg'] = ta.sma(df['volume'], length=20)
        
        # We need at least 21 rows for EMA and 20 for vol_avg
        if len(df) < 22:
            print(f"⚠️ Not enough data for indicators ({len(df)} rows). Indicators might be None.")
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        print(f"Latest Close: {latest['close']:.2f}")
        print(f"EMA Fast: {latest['ema_fast']}, EMA Slow: {latest['ema_slow']}")
        print(f"Volume: {latest['volume']}, Avg Vol: {latest['vol_avg']}")
        
        # Logic check
        if latest['volume'] > (1.2 * (latest['vol_avg'] or 0)):
            print("💎 Volume condition met (1.2x)!")
        
        if latest['ema_fast'] > latest['ema_slow']:
            print("📈 Price is above fast EMA.")

    except Exception as e:
        print(f"❌ Stock test failed for {symbol}: {e}")

async def run_all_tests():
    symbols = ["RELIANCE.NS", "GOLDBEES.NS", "NIFTYBEES.NS"]
    for s in symbols:
        await test_stocks(s)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
