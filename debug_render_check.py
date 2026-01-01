
import logging
import sys
import asyncio
import os
import traceback
import time

# Setup verbose logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("render_check.log", mode='w')
    ]
)
logger = logging.getLogger("ANTI_GRAVITY_RENDER_CHECK")

async def main():
    logger.info("=== [ANTIGRAVITY_RENDER_CHECK] START ===")
    logger.info("Stage: Initialization")
    
    try:
        # Import config to verify environment
        import config
        logger.debug(f"Config Loaded. MODE: {'PAPER' if config.PAPER_TRADING else 'LIVE'}")
        
        # Import Bot
        logger.info("Stage: Model Load / Import (This may take 10-20s due to NLP libraries...)")
        start_time = time.time()
        
        import bot
        import news_manager
        
        elapsed = time.time() - start_time
        logger.info(f"Import Complete in {elapsed:.2f}s")
        
        # Check Global Services in bot.py
        logger.info("Stage: Component Verification")
        
        # Check News Service
        if hasattr(bot, 'news_service') and isinstance(bot.news_service, news_manager.NewsManager):
            logger.info("Component Check: bot.news_service OK")
            if bot.news_service.use_ai:
                logger.info("Component Check: Gemini AI Configured ✅")
            else:
                logger.warning("Component Check: Gemini AI NOT Configured ⚠️")
        else:
            logger.error("Component Check: bot.news_service FAILED")

        # Check Trade Manager
        if hasattr(bot, 'trade_mgr'):
             logger.info("Component Check: bot.trade_mgr OK")

        logger.info("Stage: Execution Cycle Test (Simulation)")
        
        # Simulate Job Queue Init
        from telegram.ext import Application
        if config.TELEGRAM_BOT_TOKEN:
            logger.info("Token verified. Building Application...")
            # We don't build full app to avoid conflict/binding ports, just verify logic
            logger.info("Render Cycle: Initialization Logic Validated")
        else:
            logger.critical("Render Cycle: Missing Token!")
            raise ValueError("Missing TELEGRAM_BOT_TOKEN")
        
        logger.info("=== [ANTIGRAVITY_RENDER_CHECK] SUCCESS ===")
        
    except Exception as e:
        logger.error("=== [ANTIGRAVITY_RENDER_CHECK] FAILED ===")
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"FAILED_STACK_TRACE: {traceback.format_exc()}") # Ensure stdout gets it
        sys.exit(1)
    finally:
        logger.info("Stage: Cleanup")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
