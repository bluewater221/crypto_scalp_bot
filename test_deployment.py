import asyncio
import logging
import os
import shutil
import pandas as pd
import market_data
import signals
import chart_generator
import utils
import sheets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestDeployment")

async def test_deployment():
    logger.info("--- Starting Deployment Verification ---")
    
    # 1. Check Utils
    logger.info(f"IST Time: {utils.get_ist_time()}")
    logger.info(f"Is Crypto Market Open? {utils.is_market_open('CRYPTO')}")
    logger.info(f"Is Stock Market Open? {utils.is_market_open('STOCK')}")
    
    # 2. Check Sheets
    # Check if creds file exists, if not, mock logic should warn but not crash
    if not os.path.exists('credentials.json') and not os.environ.get('GOOGLE_SHEETS_CREDENTIALS_JSON'):
        logger.warning("No Google Sheets credentials found. Expect logging to be skipped.")
    
    # 3. Check Crypto Data (Binance)
    logger.info("Checking Crypto Data...")
    exchange = market_data.get_crypto_exchange()
    if exchange:
        df_crypto = await market_data.fetch_crypto_ohlcv(exchange, 'BTC/USDT', limit=50)
        if df_crypto is not None and not df_crypto.empty:
            logger.info(f"Crypto Data Fetched: {len(df_crypto)} rows.")
            df_crypto = market_data.calculate_indicators_crypto(df_crypto)
            logger.info(f"Verified Indicators (RSI): {df_crypto['rsi'].iloc[-1]}")
            
            # Generate Chart Test
            path = chart_generator.generate_chart(df_crypto, 'BTC/USDT', '1m', 'TEST')
            if path and os.path.exists(path):
                logger.info(f"Chart Generated at: {path}")
                # Cleanup
                # os.remove(path)
            else:
                logger.error("Chart generation failed.")
        else:
            logger.error("Failed to fetch Crypto data.")
    else:
        logger.error("Exchange initialization failed.")

    # 4. Check Stock Data (YFinance)
    logger.info("Checking Stock Data...")
    try:
        # Use a reliable symbol
        symbol = 'RELIANCE.NS'
        df_stock = await market_data.fetch_stock_data(symbol)
        if df_stock is not None and not df_stock.empty:
            logger.info(f"Stock Data Fetched for {symbol}: {len(df_stock)} rows.")
            df_stock = market_data.calculate_indicators_stock(df_stock)
            logger.info(f"Verified Indicators (EMA/Vol): {df_stock.columns}")
        else:
            logger.error(f"Failed to fetch Stock data for {symbol}.")
    except Exception as e:
        logger.error(f"Stock Data Error: {e}")

    logger.info("--- Verification Complete ---")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_deployment())
