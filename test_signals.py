import pandas as pd
import signals
import config
from unittest.mock import MagicMock
import asyncio

def test_logic():
    print("Testing Signal Logic...")
    
    # Mock Exchange
    mock_exchange = MagicMock()
    
    # Case 1: Oversold (Should Buy/Long)
    # RSI < 30
    df_long = pd.DataFrame({
        'timestamp': pd.date_range(start='1/1/2022', periods=100, freq='min'),
        'open': [100]*100,
        'high': [100]*100,
        'low': [100]*100,
        'close': [100]*100,
        'volume': [100]*100
    })
    # Force RSI to be low
    df_long['rsi'] = [25]*100 
    
    # Monkeypatch
    original_fetch = signals.market_data.fetch_crypto_ohlcv
    original_calc = signals.market_data.calculate_indicators_crypto
    
    try:
        # Mock Async Function for fetch
        async def mock_fetch(*args, **kwargs):
            return df_long
            
        signals.market_data.fetch_crypto_ohlcv = mock_fetch
        signals.market_data.calculate_indicators_crypto = MagicMock(return_value=df_long)
        
        # We need to run async function
        result = asyncio.run(signals.analyze_crypto(mock_exchange, "BTC/USDT"))
        
        if result and result['side'] == 'LONG' and result['setup'].startswith('RSI Oversold'):
            print("PASS: Long Signal Generation")
            print(f"Details: {result}")
        else:
            print("FAIL: Long Signal Generation")
            print(f"Got: {result}")
            
        # Case 2: Overbought (Should Sell/Short)
        df_short = df_long.copy()
        df_short['rsi'] = [75]*100
        
        async def mock_fetch_short(*args, **kwargs):
            return df_short
            
        signals.market_data.fetch_crypto_ohlcv = mock_fetch_short
        signals.market_data.calculate_indicators_crypto = MagicMock(return_value=df_short)
        
        result = asyncio.run(signals.analyze_crypto(mock_exchange, "BTC/USDT"))
        
        if result and result['side'] == 'SHORT' and result['setup'].startswith('RSI Overbought'):
            print("PASS: Short Signal Generation")
            print(f"Details: {result}")
        else:
            print("FAIL: Short Signal Generation")
            print(f"Got: {result}")

        # Case 3: Neutral
        df_neutral = df_long.copy()
        df_neutral['rsi'] = [50]*100
        
        async def mock_fetch_neutral(*args, **kwargs):
            return df_neutral

        signals.market_data.fetch_crypto_ohlcv = mock_fetch_neutral
        signals.market_data.calculate_indicators_crypto = MagicMock(return_value=df_neutral)
        
        result = asyncio.run(signals.analyze_crypto(mock_exchange, "BTC/USDT"))
        
        if result is None:
            print("PASS: Neutral Condition")
        else:
            print("FAIL: Neutral Condition")
            print(f"Got: {result}")

    finally:
        # Restore
        signals.market_data.fetch_crypto_ohlcv = original_fetch
        signals.market_data.calculate_indicators_crypto = original_calc

if __name__ == "__main__":
    test_logic()
