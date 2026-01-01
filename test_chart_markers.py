import pandas as pd
import chart_generator
import os
import logging

logging.basicConfig(level=logging.INFO)

def test_chart_markers():
    print("🚀 Testing Chart Markers...")
    
    # Create dummy data
    data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='1h'),
        'open': [100 + i for i in range(50)],
        'high': [105 + i for i in range(50)],
        'low': [95 + i for i in range(50)],
        'close': [102 + i for i in range(50)],
        'volume': [1000] * 50,
        'ema_fast': [100 + i for i in range(50)],
        'ema_slow': [98 + i for i in range(50)],
        'rsi': [60] * 50
    }
    df = pd.DataFrame(data)
    
    # Test LONG market
    filename_long = chart_generator.generate_chart(df, 'TEST_LONG', '1h', 'LONG')
    if filename_long and os.path.exists(filename_long):
        print(f"✅ Generated LONG chart with markers: {filename_long}")
    else:
        print("❌ Failed to generate LONG chart")

    # Test SHORT market
    filename_short = chart_generator.generate_chart(df, 'TEST_SHORT', '1h', 'SHORT')
    if filename_short and os.path.exists(filename_short):
        print(f"✅ Generated SHORT chart with markers: {filename_short}")
    else:
        print("❌ Failed to generate SHORT chart")

if __name__ == "__main__":
    test_chart_markers()
