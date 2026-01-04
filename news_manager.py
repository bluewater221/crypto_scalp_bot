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
from google import genai
try:
    from groq import Groq
except ImportError:
    Groq = None
from openai import OpenAI
import market_data

logger = logging.getLogger(__name__)

# Smart Filter: Only use AI for high-impact news to save quota
HIGH_IMPACT_KEYWORDS = [
    "earnings", "profit", "loss", "revenue", "quarter", "q1", "q2", "q3", "q4",
    "acquisition", "merger", "deal", "partnership",
    "sec", "rbi", "fed", "rate", "inflation", "cpi", "gdp",
    "breakout", "ath", "all time high", "crash", "correction",
    "listing", "delisting", "binance", "coinbase", "mainnet", "airdrop"
]

class NewsManager:
    def __init__(self):
        self.seen_file = 'seen_news.json'
        self.seen_news_ids = self.load_seen_news()
        
        # Sync with Google Sheets (Persistence across environments like GitHub Actions)
        try:
            remote_ids = sheets.fetch_seen_news()
            if remote_ids:
                logger.info(f"🔄 Synced {len(remote_ids)} seen news IDs from Google Sheets")
                self.seen_news_ids.update(remote_ids)
        except Exception as e:
            logger.warning(f"Failed to sync seen news from Sheets: {e}")
        

        # Configure Gemini (New SDK)
        self.client = None
        self.use_ai = False
        if config.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=config.GEMINI_API_KEY)
                self.use_ai = True
                logger.info("✅ Gemini AI Initialized")
            except Exception as e:
                logger.error(f"Failed to config Gemini: {e}")
        else:
             logger.warning("ℹ️ Gemini API Key missing. Skipping AI analysis.")

        # Configure Groq (Fallback 1)
        self.groq_client = None
        if config.GROQ_API_KEY and Groq:
            try:
                self.groq_client = Groq(api_key=config.GROQ_API_KEY)
                logger.info("✅ Groq AI Initialized")
            except Exception as e:
                logger.error(f"Failed to config Groq: {e}")
        elif not config.GROQ_API_KEY:
             logger.warning("ℹ️ Groq API Key missing.")

        # Configure OpenRouter (Fallback 2 - DeepSeek/Qwen)
        self.openrouter_client = None
        if config.OPENROUTER_API_KEY:
            try:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=config.OPENROUTER_API_KEY,
                )
                logger.info("✅ OpenRouter AI Initialized")
            except Exception as e:
                logger.error(f"Failed to config OpenRouter: {e}")

        # Configure OpenRouter (Fallback 2 - DeepSeek/Qwen)
        self.openrouter_client = None
        if config.OPENROUTER_API_KEY:
            try:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=config.OPENROUTER_API_KEY,
                )
                logger.info("✅ OpenRouter AI Initialized")
            except Exception as e:
                logger.error(f"Failed to config OpenRouter: {e}")

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

    async def analyze_sentiment(self, text, description="", check_cost=False, market_type='CRYPTO'):
        """Asks AI to analyze news sentiment and impact with localized prompts."""
        result = {
            'sentiment': 'NEUTRAL',
            'ai_insight': None,
            'companies': [],
            'is_india_macro': False,
            'low_cost': True,
            'estimated_reward': 'Unknown',
            'requirements': 'None'
        }

        should_use_ai = self.use_ai
        # Quota Saver Logic
        if not should_use_ai:
            if any(k in text.lower() for k in ['break', 'surge', 'crash', 'warn', 'launch', 'airdrop']):
                should_use_ai = True
            else:
                return result

        # Tailor Prompt by Market
        india_hint = "is_india_macro (boolean: true if about Indian Economy, bonds, RBI, Rupee. False for specific tickers)." if market_type == 'STOCK' else ""
        
        # User Feedback: "potential USDT doesn't seem right"
        # Instruction: DO NOT use the word "Potential" in the result. 
        # Capture the actual value/reward as mentioned (e.g. '$10', '500 Points', '1 ETH').
        prompt = (
            f"Analyze this {market_type} news and return JSON ONLY:\nTitle: {text}\n"
            f"Keys: sentiment(BULLISH/BEARISH/NEUTRAL), price_prediction(e.g. '+2%'), reasoning(max 10 words), "
            f"estimated_reward (Expected value/reward. Use symbols like $, ₹ or units like Points/Tokens. DO NOT use 'Potential' and don't force 'USDT' unless explicitly stated), "
            f"requirements (steps needed), companies(list of tickers), {india_hint}"
        )

        # 1. Try Groq (Fast & Reliable)
        if self.groq_client:
            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                ai_data = json.loads(chat_completion.choices[0].message.content)
                
                result['sentiment'] = ai_data.get('sentiment', 'NEUTRAL')
                result['ai_insight'] = (
                    f"🤖 AI Prediction: {ai_data.get('price_prediction', 'N/A')}\n"
                    f"💡 Reasoning: {ai_data.get('reasoning', 'No reasoning provided.')}"
                )
                result['companies'] = ai_data.get('companies', [])
                result['is_india_macro'] = ai_data.get('is_india_macro', False)
                result['estimated_reward'] = ai_data.get('estimated_reward', 'Unknown')
                result['requirements'] = ai_data.get('requirements', 'None')
                return result
            except Exception as e:
                logger.warning(f"Groq Sentiment failed: {e}")

        # 2. Try Gemini (Fallback)
        if self.client:
            try:
                response = self.client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                ai_data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                
                result['sentiment'] = ai_data.get('sentiment', 'NEUTRAL')
                result['ai_insight'] = (
                    f"🤖 AI Prediction: {ai_data.get('price_prediction', 'N/A')}\n"
                    f"💡 Reasoning: {ai_data.get('reasoning', 'No reasoning.')}"
                )
                result['estimated_reward'] = ai_data.get('estimated_reward', 'Unknown')
                return result
            except Exception as e:
                logger.warning(f"Gemini Sentiment failed: {e}")

        # 4. Try Hugging Face (Tertiary Fallback)
        if self.hf_api_key:
            try:
                # Using meta-llama/Meta-Llama-3-8B-Instruct
                hf_url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                payload = {
                    "inputs": prompt + "\nReturn ONLY valid JSON.",
                    "parameters": {"max_new_tokens": 512, "return_full_text": False}
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(hf_url, headers=headers, json=payload, timeout=20) as response:
                        if response.status == 200:
                            hf_data = await response.json()
                            content = hf_data[0]['generated_text']
                            # Extract JSON
                            start_idx = content.find('{')
                            end_idx = content.rfind('}') + 1
                            if start_idx != -1 and end_idx != -1:
                                ai_data = json.loads(content[start_idx:end_idx])
                                result['sentiment'] = ai_data.get('sentiment', 'NEUTRAL')
                                result['ai_insight'] = f"🤖 AI Prediction: {ai_data.get('price_prediction', 'N/A')}"
                                result['estimated_reward'] = ai_data.get('estimated_reward', 'Unknown')
                                return result
            except Exception as e:
                logger.warning(f"Hugging Face Sentiment failed: {e}")

        return result

         # 3. Try OpenRouter (DeepSeek/Qwen Fallback)
        if self.openrouter_client and should_use_ai:
            try:
                # Simplified prompt for DeepSeek/Qwen via OpenRouter
                prompt_content = f"Analyze this news and return JSON ONLY. Text: {text}. Keys: sentiment(BULLISH/BEARISH/NEUTRAL), price_prediction, reasoning."
                
                completion = self.openrouter_client.chat.completions.create(
                    model="deepseek/deepseek-chat", # Cheap & Powerful
                    messages=[{"role": "user", "content": prompt_content}]
                )
                
                raw_content = completion.choices[0].message.content
                if "```json" in raw_content:
                    raw_content = raw_content.split("```json")[1].split("```")[0]
                
                ai_data = json.loads(raw_content)
                result['sentiment'] = ai_data.get('sentiment', 'NEUTRAL')
                result['ai_insight'] = f"🧠 AI (DeepSeek): {ai_data.get('reasoning', 'Analyzed')}"
                return result

            except Exception as e:
                logger.warning(f"OpenRouter Analysis failed: {e}")
 
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
                        
                        news_item = {
                            'title': entry.title,
                            'summary': summary[:800] + "..." if len(summary) > 800 else summary, 
                            'link': entry.link,
                            'source': pub_date or "Recently",
                            'publisher': 'Economic Times',
                            'type': 'STOCK',
                            'sentiment': analysis_result,
                            'related_tickers': analysis_result.get('companies', [])
                        }
                        
                        # Add Forex Context if India Macro News
                        if analysis_result.get('is_india_macro', False):
                            usdinr = await market_data.get_usdinr_status()
                            if usdinr:
                                news_item['usdinr_data'] = usdinr
                                
                        news_items.append(news_item)
                        try:
                            self.save_seen_news()
                            sheets.log_seen_news(news_id)
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
                                sheets.log_seen_news(news_id)
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
                            'sentiment': analysis_result
                        })
                        try:
                            self.save_seen_news()
                            sheets.log_seen_news(news_id)
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
                        analysis_result = await self.analyze_sentiment(entry.title, summary, check_cost=True, market_type='CRYPTO')
                        
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
                            sheets.log_seen_news(news_id)
                        except: pass
        except Exception as e:
            logger.error(f"Error fetching airdrops: {e}")
            
        return airdrops
