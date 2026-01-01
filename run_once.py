import asyncio
import logging
from datetime import datetime

# Setup Logging first to capture import errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    import bot
    import config
except ImportError as e:
    logger.critical(f"❌ Critical Import Error: {e}")
    # We might want to exit here or let it fail later
    raise e
except Exception as e:
    logger.critical(f"❌ Unexpected Error during imports: {e}")
    raise e

async def run_once():
    """Run a single scan cycle for Stocks and Crypto."""
    logger.info("🚀 Starting Single Scan Cycle...")
    
    # 1. Initialize Bot Resources (if needed)
    # bot.py functions are mostly independent, but let's check
    
    # 2. Scan Crypto
    logger.info("--- Scanning Crypto ---")
    await bot.scan_crypto()
    
    # 3. Scan Stocks
    # Check Market Hours first? Or just run it?
    # Logic inside scan_stocks might check hours.
    # config.STOCK_MARKET_OPEN_HOUR etc.
    # Let's run it.
    logger.info("--- Scanning Stocks ---")
    await bot.scan_stocks()
    
    logger.info("✅ Scan Cycle Complete. Exiting.")

if __name__ == '__main__':
    try:
        asyncio.run(run_once())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Run Error: {e}")
