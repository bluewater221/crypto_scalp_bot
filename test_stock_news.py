import yfinance as yf
import config

def test_stock_news():
    print("Testing Stock News Fetching...")
    
    # Test configured symbols
    symbols = config.STOCK_SYMBOLS[:3]
    print(f"Checking symbols: {symbols}")
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            print(f"Raw News Count: {len(news)}")
            if news:
                item = news[0]
                print(f"Top Keys: {list(item.keys())}")
                if 'content' in item:
                    print(f"Content Keys: {list(item['content'].keys())}")
                    print(f"Title: {item['content'].get('title')}")
                    print(f"PubDate: {item['content'].get('pubDate')}") # Guessing
                else:
                    print(f"Title (Top): {item.get('title')}")
            else:
                print("No news found via .news attribute.")
                
            # Try search fallback if possible (yfinance doesn't have direct search, but let's see if there are other attributes)
            # Some versions use .get_news()
            try:
                if hasattr(ticker, 'get_news'):
                    alt_news = ticker.get_news()
                    print(f"get_news() Count: {len(alt_news)}")
            except Exception as e:
                print(f"get_news() failed: {e}")
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    test_stock_news()
