import pandas as pd
import signals
import config
import logging
import asyncio
import pandas_ta as ta
import numpy as np

# Configure Logging to catch 'reasons'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_final")

# --- MOCKING INFRASTRUCTURE ---
# We mock market_data to return controlled DataFrames

original_fetch_stock = signals.market_data.fetch_stock_data
original_calc_stock = signals.market_data.calculate_indicators_stock
original_fetch_crypto = signals.market_data.fetch_crypto_ohlcv
original_calc_crypto = signals.market_data.calculate_indicators_crypto

# Global Mock Containers
MOCK_STOCK_DF = None
MOCK_CRYPTO_1M = None
MOCK_CRYPTO_5M = None

async def mock_fetch_stock(symbol, timeframe=None, period=None):
    return MOCK_STOCK_DF.copy() if MOCK_STOCK_DF is not None else None

def mock_calc_stock(df):
    return df # Assumes input DF already has indicators/logic set

async def mock_fetch_crypto(exchange, symbol, timeframe='1m', limit=100):
    if timeframe == '1m': return MOCK_CRYPTO_1M.copy() if MOCK_CRYPTO_1M is not None else None
    if timeframe == '5m': return MOCK_CRYPTO_5M.copy() if MOCK_CRYPTO_5M is not None else None
    return None

def mock_calc_crypto(df):
    return df # Indicators pre-set

# Apply Mocks
signals.market_data.fetch_stock_data = mock_fetch_stock
signals.market_data.calculate_indicators_stock = mock_calc_stock
signals.market_data.fetch_crypto_ohlcv = mock_fetch_crypto
signals.market_data.calculate_indicators_crypto = mock_calc_crypto

# Mock Monkeypatching for Signals.py if it uses ta.ema directly
# But wait, signals.py code calculates indicators AGAIN inside analyze_crypto/stock?
# analyze_stock: logic is "df = calculate_indicators_stock(df)". If our mock returns DF with indicators, and check reuse, it works.
# BUT Signals.py DOES use ta.ema/ta.rsi inside calculate functions if we didn't mock them?
# We mocked `calculate_indicators_stock` to just return `df`. So `signals.py` won't recalc.
# EXCEPT for `analyze_crypto`:
# It explicitly calls:
#   df_1m['ema_20'] = ta.ema(df_1m['close'], length=20)
#   df_5m['ema_20'] = ...
# So we MUST mock `ta.ema` for Crypto tests to respect our mock values.

# Mock Monkeypatching for Signals.py if it uses ta.ema directly
original_ta_ema = ta.ema
def mock_ta_ema(series, length=None):
    # Mapping for Crypto Test
    # If len series matches our mock DF len
    print(f"DEBUG: mock_ta_ema called. Len Series: {len(series)}")
    if MOCK_CRYPTO_1M is not None:
        print(f"DEBUG: Expect 1M Len: {len(MOCK_CRYPTO_1M)}")
        if len(series) == len(MOCK_CRYPTO_1M):
            print("DEBUG: Match 1M")
            return MOCK_CRYPTO_1M['ema_20']
            
    if MOCK_CRYPTO_5M is not None:
         print(f"DEBUG: Expect 5M Len: {len(MOCK_CRYPTO_5M)}")
         if len(series) == len(MOCK_CRYPTO_5M):
            print(f"DEBUG: Match 5M Length {length}")
            if length == 20: return MOCK_CRYPTO_5M['ema_20']
            if length == 50: return MOCK_CRYPTO_5M['ema_50']
            
    print("DEBUG: No Match - Return 0s")
    return pd.Series([0.0]*len(series))
ta.ema = mock_ta_ema


# --- TEST HELPERS ---
def create_base_stock_df(rows=30):
    df = pd.DataFrame()
    df['close'] = [105.0] * rows # Fix: Must be > EMA (102)
    df['high'] = [106.0] * rows
    df['low'] = [95.0] * rows
    df['open'] = [100.0] * rows
    df['volume'] = [1000] * rows
    
    # Pre-fill passing indicators (Shields UP)
    # Shield 1: Momentum (Crossed)
    df['ema_fast'] = [102.0] * rows # 9
    df['ema_slow'] = [100.0] * rows # 21
    # Trigger cross on last row
    df.loc[rows-2, 'ema_fast'] = 100.0 # Prev: Flat
    df.loc[rows-2, 'ema_slow'] = 100.0
    
    # Shield 2: Trend (Price > 50, Slope > 0)
    df['ema_trend'] = [98.0] * rows # 50
    df['ema_trend_slope'] = [1.0] * rows # Positive
    
    # Shield 3: Strength (ADX > 20, Rising, < 40)
    df['adx'] = [25.0] * rows
    df.loc[rows-2, 'adx'] = 24.0 # Rising
    
    # Shield 4: Safety (RSI 45-65)
    df['rsi'] = [55.0] * rows
    
    # Shield 5: Volume (>1.2x Avg, >Prev)
    df['vol_avg'] = [1000.0] * rows
    df.loc[rows-1, 'volume'] = 2000 # > 1.2*1000
    df.loc[rows-2, 'volume'] = 1000 # > Prev
    
    return df

# --- TESTS ---

async def test_1_stock_volume_integrity():
    print("🧪 TEST 1: Stock Volume Integrity")
    global MOCK_STOCK_DF
    # 1. Base Case (Pass)
    MOCK_STOCK_DF = create_base_stock_df()
    res = await signals.analyze_stock("TEST")
    msg = "Pass Base Case"
    if res and res['side'] == 'LONG': print(f"✅ {msg}")
    else: print(f"❌ {msg} - Failed: {res}")
    
    # 2. Vol <= 1.2x Avg (Fail)
    MOCK_STOCK_DF = create_base_stock_df()
    MOCK_STOCK_DF.loc[29, 'volume'] = 1100 # 1.1x
    # vol_avg is 1000
    res = await signals.analyze_stock("TEST")
    msg = "Reject Low Volume vs Avg"
    if res is None: print(f"✅ {msg}")
    else: print(f"❌ {msg} - Leaked!")

    # 3. Vol <= Prev (Fail) - Stock specific rule
    MOCK_STOCK_DF = create_base_stock_df()
    MOCK_STOCK_DF.loc[29, 'volume'] = 2000
    MOCK_STOCK_DF.loc[28, 'volume'] = 2100 # Prev was higher
    # Avg is still 1000, 2000 > 1200 ok. But 2000 < 2100.
    res = await signals.analyze_stock("TEST")
    msg = "Reject Volume < Prev"
    if res is None: print(f"✅ {msg}")
    else: print(f"❌ {msg} - Leaked!")

async def test_2_stock_sl_logic():
    print("\n🧪 TEST 2: Stock Stop-Loss Logic (Tighter-Of)")
    global MOCK_STOCK_DF
    MOCK_STOCK_DF = create_base_stock_df()
    
    # Entry = 100.0
    # Fixed SL = 0.5% -> 99.5
    # EMA 21 SL = EMA21 * (1 - 0.0005) -> 100.0 * 0.9995 = 99.95
    # Tighter SL should be 99.95 (Higher Price)
    
    MOCK_STOCK_DF.loc[29, 'close'] = 100.0
    MOCK_STOCK_DF.loc[29, 'ema_slow'] = 100.0 # EMA 21
    
    res = await signals.analyze_stock("TEST")
    if res:
        sl = res['stop_loss']
        expected_sl = 100.0 * (1 - 0.0005) # ~99.95
        print(f"   Calculated SL: {sl:.4f} | Expected (EMA): {expected_sl:.4f}")
        if abs(sl - expected_sl) < 0.001: print(f"✅ Case A: EMA SL Chosen (Tighter)")
        else: print(f"❌ Case A Fail: Got {sl}")
        
    # Case B: EMA is far away (Wide), Fixed is tighter
    # Entry 100.
    # EMA 21 = 90.0.
    # EMA SL = 90 * 0.9995 = 89.955
    # Fixed SL = 100 * 0.995 = 99.5
    # Expect 99.5
    MOCK_STOCK_DF = create_base_stock_df()
    MOCK_STOCK_DF.loc[29, 'close'] = 100.0
    MOCK_STOCK_DF.loc[29, 'ema_slow'] = 90.0
    
    res = await signals.analyze_stock("TEST")
    if res:
        sl = res['stop_loss']
        expected_sl = 99.5
        print(f"   Calculated SL: {sl:.4f} | Expected (Fixed): {expected_sl:.4f}")
        if abs(sl - expected_sl) < 0.001: print(f"✅ Case B: Fixed SL Chosen (Tighter)")
        else: print(f"❌ Case B Fail: Got {sl}")

async def test_3_shield_gating():
    print("\n🧪 TEST 3: Shield Gating (Zero Leakage)")
    global MOCK_STOCK_DF
    
    # 1. Fail ADX (< 20)
    df = create_base_stock_df()
    df.loc[29, 'adx'] = 19.0
    MOCK_STOCK_DF = df
    res = await signals.analyze_stock("TEST")
    if res is None: print("✅ Reject ADX < 20")
    else: print("❌ Leak ADX < 20")

    # 2. Fail ADX (> 40)
    df = create_base_stock_df()
    df.loc[29, 'adx'] = 41.0
    MOCK_STOCK_DF = df
    res = await signals.analyze_stock("TEST")
    if res is None: print("✅ Reject ADX > 40")
    else: print("❌ Leak ADX > 40")
    
    # 3. Fail RSI (> 65)
    df = create_base_stock_df()
    df.loc[29, 'rsi'] = 66.0
    MOCK_STOCK_DF = df
    res = await signals.analyze_stock("TEST")
    if res is None: print("✅ Reject RSI > 65")
    else: print("❌ Leak RSI > 65")
    
    # 4. Fail EMA Sep
    df = create_base_stock_df()
    # Close 100. EMA Fast 100.05, EMA Slow 100.0.
    # Diff 0.05. % = 0.05% < 0.1% Threshold.
    df.loc[29, 'ema_fast'] = 100.05
    df.loc[29, 'ema_slow'] = 100.00
    MOCK_STOCK_DF = df
    res = await signals.analyze_stock("TEST")
    if res is None: print("✅ Reject Tight Separation")
    else: print("❌ Leak Separation")

async def test_4_crypto_logic():
    print("\n🧪 TEST 4: Crypto Logic Integrity")
    global MOCK_CRYPTO_1M, MOCK_CRYPTO_5M
    
    # Setup Passing Case
    # 1m: RSI Crossing Up (25->35), Price > EMA20, Vol > 1.2x Avg
    df_1m = pd.DataFrame({'close': [100.0]*60, 'volume': [1000.0]*60})
    df_1m['ema_20'] = 90.0
    df_1m['rsi'] = [50.0]*60
    df_1m.loc[58, 'rsi'] = 25.0
    df_1m.loc[59, 'rsi'] = 35.0
    df_1m.loc[59, 'volume'] = 2000.0 # > 1.2*1000
    
    MOCK_CRYPTO_1M = df_1m
    
    # 5m: Bullish (20 > 50)
    # Set Length 70 to distinguish from 1m (60)
    df_5m = pd.DataFrame({'close': [100.0]*70})
    df_5m['ema_20'] = 100.0
    df_5m['ema_50'] = 90.0
    MOCK_CRYPTO_5M = df_5m
    
    # 1. Base Case
    res = await signals.analyze_crypto(None, "BTC/USDT")
    if res and res['side'] == 'LONG': print("✅ Crypto Base Pass")
    else: print(f"❌ Crypto Base Fail: {res}")
    
    # 2. Fail HTF Trend
    # Set 5m to Bearish
    df_5m_bear = df_5m.copy()
    df_5m_bear['ema_20'] = 80.0
    MOCK_CRYPTO_5M = df_5m_bear
    res = await signals.analyze_crypto(None, "BTC/USDT")
    if res is None: print("✅ Crypto Reject Counter-Trend")
    else: print("❌ Crypto Leak Counter-Trend")
    
    # Restore 5m
    MOCK_CRYPTO_5M = df_5m
    
    # 3. Fail Volume
    MOCK_CRYPTO_1M.loc[59, 'volume'] = 1100.0 # 1.1x (Fail)
    res = await signals.analyze_crypto(None, "BTC/USDT")
    if res is None: print("✅ Crypto Reject Low Vol")
    else: print("❌ Crypto Leak Low Vol")


async def main():
    print("🚀 STARTING FINAL VALIDATION")
    await test_1_stock_volume_integrity()
    await test_2_stock_sl_logic()
    await test_3_shield_gating()
    await test_4_crypto_logic()
    
    # Restore
    signals.market_data.fetch_stock_data = original_fetch_stock
    signals.market_data.calculate_indicators_stock = original_calc_stock
    signals.market_data.fetch_crypto_ohlcv = original_fetch_crypto
    signals.market_data.calculate_indicators_crypto = original_calc_crypto
    ta.ema = original_ta_ema
    print("\n🏁 VALIDATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())
