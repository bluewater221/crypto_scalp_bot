# Unified Crypto & Stock Scalping Bot

A Telegram bot that scans:
- **Crypto**: Binance Futures (BTC/USDT, ETH/USDT) via RSI Scalping Strategy (9AM-11PM IST).
- **Stocks**: Indian Markets (NSE/BSE) via EMA Crossover Strategy (9:15AM-3:30PM IST).

**Features:**
- Dual Channel Posting (`@cryptoscalp`, `@stockscalp`).
- Automated Chart Generation (Candlesticks with indicators).
- Risk Management (0.5% Rule).
- Google Sheets Logging.
- Render.com Ready (Web Service with Keep-Alive).

## Deployment

### 1. Render.com (One-Click)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Env Vars Required:**
- `TELEGRAM_BOT_TOKEN`: Your Bot Token
- `TELEGRAM_CRYPTO_CHANNEL_ID`: Channel ID (e.g. @cryptoscalp)
- `TELEGRAM_STOCK_CHANNEL_ID`: Channel ID (e.g. @stockscalp)
- `BINANCE_API_KEY` & `BINANCE_SECRET_KEY`: (Optional for Paper Trading, Required for Real)
- `PAPER_TRADING`: `True`

### 2. Local Run
```bash
pip install -r requirements.txt
python bot.py
```
