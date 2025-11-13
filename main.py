#!/usr/bin/env python3
import asyncio
import signal
import sys
from core.logger import log
from core.client import bot_client
from database.mongo_client import mongo_client
from utils.asset_manager import asset_manager
from handlers import setup_handlers

class MoviePosterBot:
    def __init__(self):
        self.is_running = False
        log.info("🎬 Movie Poster Bot Initializing...")
    
    async def startup(self):
        """Initialize bot components"""
        try:
            # Check essential configurations
            from config import BOT_TOKEN, API_ID, API_HASH, TMDB_API_KEY
            if not all([BOT_TOKEN, API_ID, API_HASH, TMDB_API_KEY]):
                log.error("❌ Missing essential configuration. Please check your .env file")
                return False
            
            log.success("✅ Configurations loaded successfully")
            
            # Check assets
            asset_manager.check_assets()
            
            # Start Pyrogram client
            if not await bot_client.start_client():
                return False
            
            # Setup handlers
            await setup_handlers(bot_client.client)
            log.success("✅ All handlers registered successfully")
            
            # Test MongoDB connection
            if mongo_client.db is not None:
                try:
                    # Test connection with a simple command
                    await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: mongo_client.db.command('ping')
                    )
                    log.success("✅ MongoDB connection verified")
                except Exception as e:
                    log.warning(f"⚠️ MongoDB ping failed: {e}")
            else:
                log.warning("⚠️ MongoDB not connected - running in limited mode")
            
            self.is_running = True
            log.success("🎉 Movie Poster Bot started successfully!")
            return True
            
        except Exception as e:
            log.error(f"💥 Startup failed: {e}")
            return False
    
    async def shutdown(self):
        """Clean shutdown"""
        log.info("🛑 Shutting down bot...")
        self.is_running = False
        await bot_client.stop_client()
        mongo_client.close()
        log.success("👋 Bot shutdown completed")

# Global bot instance
bot = MoviePosterBot()

async def main():
    """Main application entry point"""
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        log.warning(f"📡 Received signal {signum}, shutting down...")
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the bot
    if await bot.startup():
        log.info("🚀 Bot is now running. Press Ctrl+C to stop.")
        # Keep the bot running
        while bot.is_running:
            await asyncio.sleep(1)
    else:
        log.error("💥 Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Bot stopped by user")
    except Exception as e:
        log.error(f"💥 Fatal error: {e}")
        sys.exit(1)