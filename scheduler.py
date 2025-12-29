import schedule
import time
import threading
import logging
import asyncio
from telegram.ext import Application
import config
import bot  # Circular import risk? We will pass the application or func instead.

logger = logging.getLogger(__name__)

# We need a way to run async jobs from sync schedule
def run_async_job(func, *args):
    """Runs an async function in a new loop (or existing if managed carefully)."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(func(*args))
        loop.close()
    except Exception as e:
        logger.error(f"Error running async job: {e}")

def start_scheduler(app):
    """
    Starts the scheduler loop in a separate thread.
    app: Telegram Application object (to pass to jobs if needed)
    """
    # Import here to avoid circular dependency at top level if possible
    from bot import scan_crypto, scan_stocks
    
    # Schedule Crypto: Every 15 mins (09:00 - 23:00)
    # Schedule check is continuous, the job function itself checks is_market_open.
    schedule.every(15).minutes.do(lambda: run_async_job(scan_crypto, app))
    
    # Schedule Stocks: Every 10 mins (09:15 - 15:30)
    schedule.every(10).minutes.do(lambda: run_async_job(scan_stocks, app))
    
    logger.info("Scheduler started.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def run_scheduler_thread(app):
    t = threading.Thread(target=start_scheduler, args=(app,))
    t.daemon = True
    t.start()
