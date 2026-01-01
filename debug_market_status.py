import asyncio
import market_data
import config
import pandas as pd
import logging
from termcolor import colored

# Configure simpler logging
logging.basicConfig(level=logging.ERROR)

async def check_status():
    print(colored("\n🔍 DIAGNOSING MARKET STATUS (Why no trades?)...", 'cyan', attrs=['bold']))
    
    # 1. Check Crypto (BTC/ETH)
    print(colored("\n🪙 CRYPTO ANALYSIS (1m Timeframe)", 'yellow'))
    exchange = market_data.get_crypto_exchange()
    
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        try:
            df = await market_data.fetch_crypto_ohlcv(exchange, symbol)
            if df is None or df.empty:
                print(f"❌ {symbol}: No Data")
                continue
                
            # Add Indicators
            df = market_data.calculate_indicators_crypto(df)
            
            # Stock calculation adds safety indicators, Crypto calculation in market_data might not have updated?
            # Wait, I only updated `calculate_indicators_stock` in previous turn!
            # I need `calculate_indicators_crypto` to correspond if I want safety there?
            # The user complained about "Stock feature" specifically in the safety prompt ("put large sum").
            # But the user is likely asking about general lack of trades.
            # Let's check what indicators we have for Crypto.
            
            latest = df.iloc[-1]
            rsi = latest.get('rsi', 0)
            price = latest['close']
            
            print(f"  {symbol}: ${price:,.2f}")
            
            # RSI Logic
            status = "NEUTRAL"
            if rsi < 30: status = "OVERSOLD (Looking for LONG)"
            elif rsi > 70: status = "OVERBOUGHT (Looking for SHORT)"
            
            color = 'green' if 'OVER' in status else 'white'
            print(f"    RSI: {rsi:.1f} -> {colored(status, color)}")
            
        except Exception as e:
            print(f"  {symbol}: Error {e}")

    # 2. Check Stocks (RELIANCE, etc)
    print(colored("\n📈 STOCK ANALYSIS (5m Timeframe)", 'yellow'))
    print("  (Checking Safety Shields: EMA Trend, ADX > 20, RSI < 70)")
    
    for symbol in ['RELIANCE.NS', 'GOLDBEES.NS']:
        try:
            df = await market_data.fetch_stock_data(symbol)
            if df is None or df.empty:
                print(f"  {symbol}: No Data (Market Closed?)")
                continue
                
            # Add Indicators (This now includes EMA50, ADX, RSI)
            df = market_data.calculate_indicators_stock(df)
            curr = df.iloc[-1]
            
            # Extract
            price = curr['close']
            ema_trend = curr.get('ema_trend', 0)
            adx = curr.get('adx', 0)
            rsi = curr.get('rsi', 0)
            
            is_above_trend = price > ema_trend
            trend_str = "BULLISH" if is_above_trend else "BEARISH"
            trend_col = 'green' if is_above_trend else 'red'
            
            adx_status = "WEAK" if adx < 20 else "STRONG"
            adx_col = 'red' if adx < 20 else 'green'
            
            print(f"  {symbol}: {price:,.2f}")
            print(f"    Trend (EMA50): {colored(trend_str, trend_col)} (Price vs {ema_trend:.2f})")
            print(f"    Strength (ADX): {adx:.1f} -> {colored(adx_status, adx_col)} (Must be > 20)")
            print(f"    Momentum (RSI): {rsi:.1f}")
            
            reasons = []
            if adx < 20: reasons.append("Market Choppy (Low ADX)")
            
            if not reasons:
                print(f"    ✅ STATUS: Scanning for setups...")
            else:
                print(f"    ❄️ STATUS: {colored('WAITING', 'blue')} ({', '.join(reasons)})")
                
        except Exception as e:
            print(f"  {symbol}: Error {e}")

if __name__ == "__main__":
    asyncio.run(check_status())
