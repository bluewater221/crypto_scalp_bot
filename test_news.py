import yfinance as yf
import json

def test_stock_news():
    print("Fetching news for RELIANCE.NS...")
    ticker = yf.Ticker("RELIANCE.NS")
    try:
        news = ticker.news
        if news:
            print(f"Found {len(news)} articles.")
            print(json.dumps(news[0], indent=2))
        else:
            print("No news found via yfinance.")
    except Exception as e:
        print(f"Error fetching news: {e}")

if __name__ == "__main__":
    test_stock_news()
