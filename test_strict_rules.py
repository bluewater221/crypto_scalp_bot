import pandas as pd
import signals
import config
import logging
import asyncio
import pandas_ta as ta

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Testing Strict Rules
# We mock dataframes that represent specific market states

async def test_strict_stock_logic():
    print("\n🛡️ Testing STOCK 5-Shield Logic...")
    
    # Base "Perfect" DataFrame
    # Need > 20 rows
    data = {
        'close': [100] * 30,
        'volume': [1000] * 30,
        'high': [105] * 30,
        'low': [95] * 30
    }
    df = pd.DataFrame(data)
    
    # Mock Indicators for the LAST row to trigger signal
    # 1. EMA Cross: Fast > Slow (Now), Fast <= Slow (Prev)
    df.loc[29, 'ema_fast'] = 102
    df.loc[29, 'ema_slow'] = 100
    df.loc[28, 'ema_fast'] = 100
    df.loc[28, 'ema_slow'] = 100
    
    # 2. Trend: Price > EMA 50, Slope > 0
    df.loc[29, 'close'] = 105 # Above 50
    df.loc[29, 'ema_trend'] = 98 
    df.loc[19, 'ema_trend'] = 97 # Slope = (98-97)/97 > 0
    # Calculate Slope manually for mock
    df['ema_trend_slope'] = 0.0
    df.loc[29, 'ema_trend_slope'] = 1.0 # Positive
    
    # 3. Strength: ADX > 20, < 40, Rising
    df.loc[29, 'adx'] = 25
    df.loc[28, 'adx'] = 24 # Rising
    
    # 4. Momentum: RSI 45-65
    df.loc[29, 'rsi'] = 55
    
    # 5. Volume: > 1.2x Avg, > Prev
    df.loc[29, 'volume'] = 2000
    df.loc[28, 'volume'] = 1000
    df.loc[29, 'vol_avg'] = 1000 # 2000 > 1.2*1000
    
    # We need to monkeypath market_data.fetch and calculate...
    # Or better, we just extract the logic we want to test?
    # signals.analyze_stock calls fetch then calculate. 
    # To test logic properly without mocking fetch, we should have separated logic.
    # But since we are integrating, let's create a temporary Helper that mocks `market_data` behavior.
    
    # HACK: We will inject our DF into `market_data.fetch_stock_data` by mocking it
    import market_data
    original_fetch = market_data.fetch_stock_data
    original_calc = market_data.calculate_indicators_stock
    
    market_data.fetch_stock_data =  lambda s: asyncio.sleep(0.01, result=df)
    # Validation uses calculated indicators, but our mock DF has them pre-filled? 
    # analyze_stock calls calculate_indicators_stock. We need that to NOT overwrite our mocks.
    market_data.calculate_indicators_stock = lambda d: d
    
    # Run Test 1: Perfect Setup
    print("Test 1: Perfect Setup -> Expect LONG")
    res = await signals.analyze_stock("TEST.NS")
    if res and res['side'] == 'LONG':
        print("✅ PASS")
    else:
        print(f"❌ FAIL: Got {res}")

    # Test 2: Fails ADX (Choppy)
    df.loc[29, 'adx'] = 15
    print("Test 2: Low < 20 -> Expect None")
    res = await signals.analyze_stock("TEST.NS")
    if res is None: print("✅ PASS")
    else: print("❌ FAIL (Should Reject)")
    
    # Reset ADX
    df.loc[29, 'adx'] = 25
    
    # Test 3: Fails Trend (Slope Negative)
    df.loc[29, 'ema_trend_slope'] = -1.0
    print("Test 3: Negative Slope -> Expect None")
    res = await signals.analyze_stock("TEST.NS")
    if res is None: print("✅ PASS")
    else: print("❌ FAIL (Should Reject)")
    
    # Restore
    market_data.fetch_stock_data = original_fetch
    market_data.calculate_indicators_stock = original_calc

async def test_strict_crypto_logic():
    print("\n🛡️ Testing CRYPTO HTF Logic...")
    
    # Mock DF 1m
    df_1m = pd.DataFrame({'close': [100]*50})
    df_1m['rsi'] = 50
    df_1m['ema_20'] = 90
    df_1m.loc[49, 'close'] = 95 # Price > EMA20? No 95 > 90 Yes.
    
    # Valid Long Setup 1m:
    # 1. RSI Cross > 30
    df_1m.loc[48, 'rsi'] = 25
    df_1m.loc[49, 'rsi'] = 35
    
    # Mock DF 5m (HTF)
    # Give it different length to distinguish in mock_ema
    df_5m = pd.DataFrame({'close': [100]*60})
    df_5m['ema_20'] = 100
    df_5m['ema_50'] = 90 
    # Trend 5m = Bullish (20 > 50)
    
    # Mock Methods
    import market_data
    original_fetch = market_data.fetch_crypto_ohlcv
    original_calc = market_data.calculate_indicators_crypto
    
    async def mock_fetch(exch, sym, timeframe='1m', limit=100):
        if timeframe == '1m': return df_1m
        if timeframe == '5m': return df_5m
        return None
        
    market_data.fetch_crypto_ohlcv = mock_fetch
    market_data.calculate_indicators_crypto = lambda d: d # Don't recalc
    
    # Mock pandas_ta.ema to return our pre-set columns or custom values
    # signal.py calls: ta.ema(df['close'], length=20)
    # We want it to basically return df['ema_20'] if length=20
    
    original_ema = ta.ema
    
    def mock_ema(series, length=None):
        # We need to return a Series with matching index
        # We can't easily access the DF from here unless we inspect stack or use a closure.
        # But we know what we want.
        # For df_1m (length=20), we want the values we set in df_1m['ema_20']
        # But wait, ta.ema takes a SERIES (close), not DF.
        print(f"DEBUG: mock_ema called. Len Series: {len(series)} | Len df_1m: {len(df_1m)}")
        if len(series) == len(df_1m):
            # Verify values
            val = df_1m['ema_20'].iloc[-1]
            print(f"DEBUG: Returning 1m EMA. Last val: {val}")
            return df_1m['ema_20']
        if len(series) == len(df_5m):
            # length 20 or 50
            if length == 20: return df_5m['ema_20']
            if length == 50: return df_5m['ema_50']
        print("DEBUG: mock_ema mismatch return 0s")
        return pd.Series([0]*len(series))

    ta.ema = mock_ema

    # Test 1: Aligned Trend (Bullish 5m + Bullish 1m RSI)
    print("Test 1: Aligned Trend -> Expect LONG")
    res = await signals.analyze_crypto(None, "BTC/USDT")
    if res and res['side'] == 'LONG': print("✅ PASS")
    else: print(f"❌ FAIL: {res}")
    
    # Test 2: Counter Trend (Bearish 5m + Bullish 1m RSI)
    # Set 5m to Bearish
    # We need to update the source df_5m because our mock_ema reads from it
    df_5m['ema_20'] = 80 # < 90 (ema_50 is 90)
    print("Test 2: Counter Trend -> Expect None")
    res = await signals.analyze_crypto(None, "BTC/USDT")
    if res is None: print("✅ PASS")
    else: print("❌ FAIL: Should Reject Counter-Trend")

    # Restore
    market_data.fetch_crypto_ohlcv = original_fetch
    market_data.calculate_indicators_crypto = original_calc
    ta.ema = original_ema

if __name__ == "__main__":
    asyncio.run(test_strict_stock_logic())
    asyncio.run(test_strict_crypto_logic())
