import asyncio
import logging
import requests
import yfinance as yf
import feedparser
import config
from datetime import datetime, timedelta, timezone
import json
import os
import dateutil.parser
from textblob import TextBlob
import google.generativeai as genai

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(self):
        self.seen_file = 'seen_news.json'
        self.seen_news_ids = self.load_seen_news()
        
        # Configure Gemini
        if config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-pro')
                self.use_ai = True
            except Exception as e:
                logger.error(f"Failed to config Gemini: {e}")
                self.use_ai = False
        else:
            self.use_ai = False

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

    def analyze_sentiment(self, text, description=None, check_cost=False):
        """Analyze title and description sentiment using Gemini AI with TextBlob fallback."""
        result = {
            'sentiment': 'NEUTRAL',
            'score': 0,
            'ai_insight': None,
            'low_cost': True, # Default to True (pass) if not checked
            'requires_premium_x': False, # Default to False (pass)
            'is_telegram_app': False # Default to False
        }
        
        full_text = f"{text}. {description}" if description else text
        if not full_text: return result
        
        # 1. Try Gemini AI
        if self.use_ai:
            try:
                cost_prompt = ""
                if check_cost:
                    cost_prompt = "low_cost (boolean: true if free or < 5 USDT cost), requires_premium_x (boolean: true if X/Twitter Premium is required), is_telegram_app (boolean: true if it is a Telegram Mini App/Bot game), "

                prompt = (
                    f"Analyze this financial news:\nTitle: '{text}'\nDescription: '{description}'\n"
                    f"Return ONLY a JSON object with these keys: "
                    f"sentiment (BULLISH, BEARISH, or NEUTRAL), "
                    f"price_prediction (e.g., '+2.5%', '-1.0%', '0%'), "
                    f"reasoning (concise, max 15 words), "
                    f"{cost_prompt}"
                    f"companies (list of max 2 main company names or tickers mentioned, e.g. ['Reliance', 'TCS']). "
                    f"If no specific company, return empty list."
                )
                response = self.model.generate_content(prompt)
                ai_data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                
                result['sentiment'] = ai_data.get('sentiment', 'NEUTRAL')
                result['ai_insight'] = (
                    f"🤖 AI Prediction: {ai_data.get('price_prediction', 'N/A')}\n"
                    f"💡 Reasoning: {ai_data.get('reasoning', 'No reasoning provided.')}"
                )
                result['companies'] = ai_data.get('companies', [])
                if check_cost:
                    result['low_cost'] = ai_data.get('low_cost', True)
                    result['requires_premium_x'] = ai_data.get('requires_premium_x', False)
                    result['is_telegram_app'] = ai_data.get('is_telegram_app', False)
                return result

            except Exception as e:
                logger.error(f"Gemini Analysis failed: {e}")
                # Fallthrough to TextBlob
 
        # 2. TextBlob Fallback
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        result['score'] = polarity
        
        if polarity > 0.1:
            result['sentiment'] = 'BULLISH'
        elif polarity < -0.1:
            result['sentiment'] = 'BEARISH'
        
        return result

    def is_recent(self, date_str, expiry_hours=24):
        """Checks if news is from the last X hours."""
        try:
            if not date_str: return True 
            
            # Auto-parse various formats
            if isinstance(date_str, (int, float)):
                dt = datetime.fromtimestamp(date_str, tz=timezone.utc)
            else:
                dt = dateutil.parser.parse(date_str)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            is_recent = (now - dt) < timedelta(hours=expiry_hours)
            
            if not is_recent:
                logger.debug(f"Skipping old item: {date_str} ({(now - dt).total_seconds()/3600:.1f}h old)")
                
            return is_recent
        except Exception as e:
            logger.warning(f"Date parsing failed for {date_str}: {e}")
            return True # Fail open to avoid missing news, ID check captures dupes

    async def fetch_stock_news(self):
        """Fetches latest Indian stock market news from Economic Times RSS."""
        news_items = []
        # Economic Times Markets - Very active and live
        url = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
        
        try:
            feed = await asyncio.to_thread(feedparser.parse, url)
            
            # Reduced to Top 2 for "Less News"
            for entry in feed.entries[:2]:
                news_id = entry.get('id', entry.link)
                
                if news_id not in self.seen_news_ids:
                    pub_date = entry.get('published')
                    if self.is_recent(pub_date, expiry_hours=24):
                        self.seen_news_ids.add(news_id)
                        
                        # Try to find a summary or description
                        summary = entry.get('summary') or entry.get('description') or ""
                        
                        # Clean up HTML tags if present (basic)
                        summary = str(TextBlob(summary).string) 

                        # Analyze Sentiment & Extract Tickers
                        analysis_result = self.analyze_sentiment(entry.title, summary)
                        
                        news_items.append({
                            'title': entry.title,
                            'summary': summary[:800] + "..." if len(summary) > 800 else summary, 
                            'link': entry.link,
                            'source': pub_date or "Recently",
                            'publisher': 'Economic Times',
                            'type': 'STOCK',
                            'sentiment': analysis_result,
                            'related_tickers': analysis_result.get('companies', [])
                        })
                        try:
                            self.save_seen_news()
                        except: pass
        except Exception as e:
            logger.error(f"Error fetching Economic Times news: {e}")

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
            "filter": "important", # "Less News" - Reverted to important only
            "kind": "news",
            "public": "true"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            
            # Debug block/invalid response
            if response.status_code != 200:
                logger.error(f"CryptoPanic API Error {response.status_code}: {response.text[:200]}")
                return []

            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse CryptoPanic JSON. Status: {response.status_code}. Content start: {response.text[:200]}")
                return []
            
            if 'results' in data:
                # Check top 2 results only (Was 5)
                for post in data['results'][:2]:
                    news_id = str(post['id'])
                    
                    if news_id not in self.seen_news_ids:
                        pub_date = post.get('published_at')
                        if self.is_recent(pub_date):
                            self.seen_news_ids.add(news_id)
                            
                            # CryptoPanic provides 'domain' but often no full body in 'post' without premium.
                            # We can use the title itself as it's usually descriptive for these aggregated feeds.
                            
                            # Analyze sentiment and extract tickers
                            analysis_result = self.analyze_sentiment(post['title'])
                            
                            news_items.append({
                                'title': post['title'],
                                'summary': post['title'], # CryptoPanic free often just gives titles
                                'link': post['url'], 
                                'source': pub_date,
                                'publisher': post['domain'],
                                'type': 'CRYPTO',
                                'currency': post['currencies'][0]['code'] if post.get('currencies') else 'General',
                                'sentiment': analysis_result,
                                'related_tickers': analysis_result.get('companies', [])
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
                news_id = entry.link
                
                if news_id not in self.seen_news_ids:
                    try:
                        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        pub_date = dt.isoformat()
                    except:
                        pub_date = None

                    if self.is_recent(pub_date):
                        self.seen_news_ids.add(news_id)
                        
                        image_url = None
                        if 'media_content' in entry:
                            image_url = entry.media_content[0]['url']
                        elif 'links' in entry:
                            for link in entry.links:
                                if link.type.startswith('image/'):
                                    image_url = link.href
                                    break
                        
                        # Get summary for experts
                        summary = entry.get('summary') or entry.get('description') or ""
                        
                        news_items.append({
                            'title': entry.title,
                            'summary': summary[:800] + "..." if len(summary) > 800 else summary,
                            'link': entry.link,
                            'source': dt.strftime("%H:%M") if pub_date else "Just Now",
                            'publisher': 'CoinTelegraph Experts',
                            'type': 'CHART',
                            'image_url': image_url,
                            'sentiment': self.analyze_sentiment(entry.title, summary)
                        })
                        try:
                            self.save_seen_news()
                        except: pass
        except Exception as e:
            logger.error(f"Error fetching expert analysis: {e}")
            
        return news_items

    async def fetch_airdrop_opportunities(self):
        """Fetches latest airdrop opportunities from AirdropAlert RSS."""
        airdrops = []
        url = "https://airdropalert.com/feed/rssfeed"
        
        try:
            logger.info("Checking for new airdrops...")
            feed = await asyncio.to_thread(feedparser.parse, url)
            
            for entry in feed.entries[:3]:
                news_id = entry.get('id', entry.link)
                
                if news_id not in self.seen_news_ids:
                    # Parse date
                    try:
                        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        pub_date = dt.isoformat()
                    except:
                        pub_date = datetime.now(timezone.utc).isoformat()

                    if self.is_recent(pub_date, expiry_hours=168): # Relaxed to 7 days
                        self.seen_news_ids.add(news_id)
                        
                        # Extract basic info
                        # Airdrop summary
                        summary = entry.get('summary') or entry.get('description') or ""


                        # Analyze Sentiment & Check Cost
                        analysis_result = self.analyze_sentiment(entry.title, summary, check_cost=True)
                        
                        # Filter out expensive airdrops (> 5 USDT) AND Premium X
                        if not analysis_result.get('low_cost', True):
                             logger.info(f"Skipping expensive airdrop: {entry.title}")
                             continue

                        if analysis_result.get('requires_premium_x', False):
                             logger.info(f"Skipping Premium X airdrop: {entry.title}")
                             continue

                        # Highlight Telegram Apps
                        final_title = entry.title
                        if analysis_result.get('is_telegram_app', False):
                             final_title = f"📱 [TG APP] {entry.title}"

                        airdrops.append({
                            'title': final_title,
                            'summary': summary[:150] + "..." if len(summary) > 150 else summary,
                            'link': entry.link,
                            'source': datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            'publisher': 'AirdropAlert',
                            'type': 'AIRDROP',
                            'sentiment': analysis_result
                        })
                        try:
                            self.save_seen_news()
                        except: pass
        except Exception as e:
            logger.error(f"Error fetching airdrops: {e}")
            
        return airdrops
