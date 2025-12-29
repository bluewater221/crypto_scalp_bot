import pandas as pd
import signals
import config
from unittest.mock import MagicMock

def test_logic():
    print("Testing Signal Logic...")
    
    # Mock Exchange
    mock_exchange = MagicMock()
    
    # Case 1: Oversold (Should Buy/Long)
    # RSI < 30
    df_long = pd.DataFrame({
        'timestamp': pd.date_range(start='1/1/2022', periods=100, freq='T'),
        'open': [100]*100,
        'high': [100]*100,
        'low': [100]*100,
        'close': [100]*100,
        'volume': [100]*100
    })
    # Force RSI to be low
    # We can just manually set the RSI column to mock the calculation result
    df_long['rsi'] = [25]*100 
    
    # We need to mock fetch_ohlcv to return this DF
    # But analyze_symbol calls fetch_ohlcv AND calculate_rsi.
    # We should mock market_data.fetch_ohlcv and market_data.calculate_rsi to control inputs.
    
    # For simplicity, let's just test signals.analyze_symbol logic if we mock the internal calls.
    # However, signals.py imports market_data directly.
    # Let's monkeypatch market_data for this test.
    
    original_fetch = signals.market_data.fetch_ohlcv
    original_calc = signals.market_data.calculate_rsi
    
    try:
        signals.market_data.fetch_ohlcv = MagicMock(return_value=df_long)
        signals.market_data.calculate_rsi = MagicMock(return_value=df_long)
        
        result = signals.analyze_symbol(mock_exchange, "BTC/USDT")
        
        if result and result['side'] == 'LONG' and result['setup'] == 'RSI Oversold (<30)':
            print("PASS: Long Signal Generation")
            print(f"Details: {result}")
        else:
            print("FAIL: Long Signal Generation")
            print(f"Got: {result}")
            
        # Case 2: Overbought (Should Sell/Short)
        df_short = df_long.copy()
        df_short['rsi'] = [75]*100
        signals.market_data.fetch_ohlcv = MagicMock(return_value=df_short)
        signals.market_data.calculate_rsi = MagicMock(return_value=df_short)
        
        result = signals.analyze_symbol(mock_exchange, "BTC/USDT")
        
        if result and result['side'] == 'SHORT' and result['setup'] == 'RSI Overbought (>70)':
            print("PASS: Short Signal Generation")
            print(f"Details: {result}")
        else:
            print("FAIL: Short Signal Generation")
            print(f"Got: {result}")

        # Case 3: Neutral
        df_neutral = df_long.copy()
        df_neutral['rsi'] = [50]*100
        signals.market_data.fetch_ohlcv = MagicMock(return_value=df_neutral)
        signals.market_data.calculate_rsi = MagicMock(return_value=df_neutral)
        
        result = signals.analyze_symbol(mock_exchange, "BTC/USDT")
        
        if result is None:
            print("PASS: Neutral Condition")
        else:
            print("FAIL: Neutral Condition")
            print(f"Got: {result}")

    finally:
        # Restore
        signals.market_data.fetch_ohlcv = original_fetch
        signals.market_data.calculate_rsi = original_calc

if __name__ == "__main__":
    test_logic()
