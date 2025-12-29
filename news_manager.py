import logging
import requests
import yfinance as yf
import feedparser
import config
from datetime import datetime, timedelta, timezone
import json
import os
import dateutil.parser

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(self):
        self.seen_file = 'seen_news.json'
        self.seen_news_ids = self.load_seen_news()

    def load_seen_news(self):
        if os.path.exists(self.seen_file):
            try:
                with open(self.seen_file, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load seen news: {e}")
        return set()

    def save_seen_news(self):
        try:
            with open(self.seen_file, 'w') as f:
                json.dump(list(self.seen_news_ids), f)
        except Exception as e:
            logger.error(f"Failed to save seen news: {e}")

    def is_recent(self, date_str):
        """Checks if news is from the last 24 hours."""
        try:
            if not date_str: return True # Default to True if no date, but rely on ID check
            
            # Auto-parse various formats
            dt = dateutil.parser.parse(date_str)
            
            # Make sure dt is offset-aware usually (or compare naive)
            # best way: ensure both are UTC if possible
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            # Reduce window to 4 hours to minimize duplicates on server restart (ephemeral FS)
            return (now - dt) < timedelta(hours=4)
        except Exception as e:
            logger.warning(f"Date parsing failed for {date_str}: {e}")
            return True # Fail open to avoid missing news, ID check captures dupes

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
                    item = ticker_news[0]
                    
                    # Handle Nested Structure (New yfinance)
                    if 'content' in item:
                        content = item['content']
                        news_id = item.get('id')
                        title = content.get('title')
                        pub_date = content.get('pubDate')
                        
                        # Link extraction
                        link = content.get('canonicalUrl', {}).get('url')
                        if not link and 'clickThroughUrl' in content:
                            ctu = content['clickThroughUrl']
                            if isinstance(ctu, dict):
                                link = ctu.get('url')
                            else:
                                link = ctu
                                
                        publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')
                        
                    else:
                        # Fallback / Old Structure
                        news_id = item.get('uuid')
                        title = item.get('title')
                        link = item.get('link')
                        pub_date = item.get('providerPublishTime')
                        publisher = item.get('provider', {}).get('displayName', 'Yahoo Finance')

                    if news_id and news_id not in self.seen_news_ids:
                        if self.is_recent(pub_date):
                            self.seen_news_ids.add(news_id)
                            news_items.append({
                                'title': title,
                                'link': link,
                                'source': pub_date,
                                'publisher': publisher,
                                'type': 'STOCK',
                                'related_tickers': [symbol]
                            })
                            try:
                                self.save_seen_news()
                            except: pass
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
                        pub_date = post.get('published_at')
                        if self.is_recent(pub_date):
                            self.seen_news_ids.add(news_id)
                            
                            news_items.append({
                                'title': post['title'],
                                'link': post['url'], 
                                'source': pub_date,
                                'publisher': post['domain'],
                                'type': 'CRYPTO',
                                'currency': post['currencies'][0]['code'] if post.get('currencies') else 'General'
                            })
                            try:
                                self.save_seen_news()
                            except: pass
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")

        return news_items

    def fetch_expert_analysis(self):
        """Fetches 'Price Analysis' from CoinTelegraph RSS."""
        news_items = []
        url = "https://cointelegraph.com/rss/tag/price-analysis"
        
        try:
            feed = feedparser.parse(url)
            
            # Check top 2 entries
            for entry in feed.entries[:2]:
                news_id = entry.id
                
                if news_id not in self.seen_news_ids:
                    # Convert struct_time to datetime string for checking
                    try:
                        dt = datetime(*entry.published_parsed[:6])
                        pub_date = dt.isoformat()
                    except:
                        pub_date = None

                    if self.is_recent(pub_date):
                        self.seen_news_ids.add(news_id)
                        
                        # Extract image ... (unchanged logic)
                        image_url = None
                        if 'media_content' in entry:
                            image_url = entry.media_content[0]['url']
                        elif 'links' in entry:
                            for link in entry.links:
                                if link.type.startswith('image/'):
                                    image_url = link.href
                                    break
                        
                        news_items.append({
                            'title': entry.title,
                            'link': entry.link,
                            'source': dt.strftime("%H:%M") if pub_date else "Just Now",
                            'publisher': 'CoinTelegraph Experts',
                            'type': 'CHART',
                            'image_url': image_url
                        })
                        try:
                            self.save_seen_news()
                        except: pass
        except Exception as e:
            logger.error(f"Error fetching expert analysis: {e}")
            
        return news_items

