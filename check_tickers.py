import yfinance as yf
import config

print("Checking Stock Symbols...")
valid_symbols = []
invalid_symbols = []

for symbol in config.STOCK_SYMBOLS:
    try:
        ticker = yf.Ticker(symbol)
        # Fast info is faster than fetching history
        info = ticker.fast_info
        if info.last_price is not None:
            print(f"✅ {symbol}: {info.last_price}")
            valid_symbols.append(symbol)
        else:
            print(f"❌ {symbol}: No price found")
            invalid_symbols.append(symbol)
    except Exception as e:
        print(f"❌ {symbol}: Error {e}")
        invalid_symbols.append(symbol)

print("\n--- Summary ---")
print(f"Valid: {len(valid_symbols)}")
print(f"Invalid: {invalid_symbols}")
