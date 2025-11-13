from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH, DATABASE_NAME
from core.logger import log

class BotClient:
    def __init__(self):
        self.client = None
        self.is_running = False
    
    def create_client(self):
        """Create and configure Pyrogram Client"""
        try:
            self.client = Client(
                name=DATABASE_NAME,
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True
            )
            log.success("✅ Pyrogram client created successfully")
            return self.client
        except Exception as e:
            log.error(f"❌ Failed to create Pyrogram client: {e}")
            return None
    
    async def start_client(self):
        """Start the Pyrogram client"""
        if not self.client:
            self.create_client()
        
        if self.client:
            try:
                await self.client.start()
                self.is_running = True
                
                me = await self.client.get_me()
                log.success(f"✅ Bot started successfully: @{me.username} (ID: {me.id})")
                return True
                
            except Exception as e:
                log.error(f"❌ Failed to start bot client: {e}")
                return False
        return False
    
    async def stop_client(self):
        """Stop the Pyrogram client"""
        if self.client and self.is_running:
            try:
                await self.client.stop()
                self.is_running = False
                log.info("🛑 Bot client stopped successfully")
            except Exception as e:
                log.error(f"💥 Error stopping bot client: {e}")

# Global bot client instance
bot_client = BotClient()