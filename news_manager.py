import logging
import requests
import yfinance as yf
import config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(self):
        self.seen_news_ids = set()

    def fetch_stock_news(self):
        """Fetches latest news for configured stock symbols using yfinance."""
        news_items = []
        try:
            # We can check news for a major index or just the top stocks in our list
            # Checking top 3 stocks to avoid too many requests/spam
            top_stocks = config.STOCK_SYMBOLS[:3] 
            
            for symbol in top_stocks:
                ticker = yf.Ticker(symbol)
                ticker_news = ticker.news
                
                if ticker_news:
                    # Get the most recent article
                    article = ticker_news[0]
                    news_id = article.get('uuid')
                    
                    if news_id and news_id not in self.seen_news_ids:
                        self.seen_news_ids.add(news_id)
                        news_items.append({
                            'title': article.get('title'),
                            'link': article.get('link'),
                            'source': article.get('providerPublishTime'), # Timestamp
                            'publisher': article.get('provider', {}).get('displayName', 'Yahoo Finance'),
                            'type': 'STOCK',
                            'related_tickers': [symbol]
                        })
        except Exception as e:
            logger.error(f"Error fetching stock news: {e}")
            
        return news_items

    def fetch_crypto_news(self):
        """Fetches important crypto news from CryptoPanic API."""
        if not config.CRYPTOPANIC_API_KEY:
            logger.warning("CryptoPanic API Key missing. Skipping crypto news.")
            return []

        news_items = []
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": config.CRYPTOPANIC_API_KEY,
            "filter": "important", # Only important news
            "kind": "news",
            "public": "true"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'results' in data:
                # Check top 3 results
                for post in data['results'][:3]:
                    news_id = str(post['id'])
                    
                    if news_id not in self.seen_news_ids:
                        self.seen_news_ids.add(news_id)
                        
                        # Parse date for potential filtering? (Skipping for now, trust API order)
                        
                        news_items.append({
                            'title': post['title'],
                            'link': post['url'], # This is CryptoPanic link, usually redirects to source
                            'source': post['published_at'],
                            'publisher': post['domain'],
                            'type': 'CRYPTO',
                            'currency': post['currencies'][0]['code'] if post.get('currencies') else 'General'
                        })
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")

        return news_items
