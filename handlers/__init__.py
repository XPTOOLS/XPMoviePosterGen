from pyrogram import filters
from core.logger import log
from handlers.user_handler import handle_private_message, handle_movie_selection_callback

async def setup_handlers(client):
    """Register all message handlers"""
    
    # Private message handler
    @client.on_message(filters.private & filters.incoming)
    async def private_message_handler(client, message):
        await handle_private_message(client, message)
    
    # Callback query handler for movie selection
    @client.on_callback_query()
    async def callback_query_handler(client, callback_query):
        await handle_movie_selection_callback(client, callback_query)
    
    # Channel message handler
    from config import DATABASE_CHANNEL_ID
    @client.on_message(filters.chat(DATABASE_CHANNEL_ID) & filters.incoming)
    async def channel_message_handler(client, message):
        from handlers.channel_handler import handle_channel_message
        await handle_channel_message(client, message)
    
    log.success("🎯 All handlers registered successfully!")