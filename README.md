# 🤖 Crypto & Stock Scalping Bot

An AI-powered trading bot that scans Indian stocks (NSE) and Crypto markets for scalping opportunities.

## Features
- **Multi-Market**: NSE Stocks (5-minute) and Crypto (1-minute) scalping
- **AI Validation**: Uses Google Gemini for signal confidence scoring
- **News Intelligence**: Curated news with sentiment analysis
- **Airdrop Alerts**: Smart filtering for quality crypto airdrops
- **Charts**: Auto-generated technical analysis charts
- **Persistent Memory**: Google Sheets for trade history

## Architecture
| Component | Platform | Duty |
|---|---|---|
| **Trader** | Render | 24/7 Signal Scanning, Commands |
| **Analyst** | GitHub Actions | Periodic News, Airdrops, Market Pulse |

## Quick Start
1. Clone this repository
2. Copy `.env.example` to `.env` and fill in credentials
3. `pip install -r requirements.txt`
4. `python bot.py`

## Commands
| Command | Description |
|---|---|
| `/stats` | Show trading statistics and balance |
| `/market` | Show market sentiment (Fear & Greed, Nifty trend) |
| `/news` | Manually trigger news fetch |
| `/airdrops` | Manually trigger airdrop fetch |

## Environment Variables
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CRYPTO_CHANNEL_ID=-100xxxxxxxxxx
TELEGRAM_STOCK_CHANNEL_ID=-100xxxxxxxxxx
GEMINI_API_KEY=your_gemini_key
CRYPTOPANIC_API_KEY=your_cryptopanic_key
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account"...}
```

## License
MIT
