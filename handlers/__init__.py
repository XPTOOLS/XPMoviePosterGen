from pyrogram import filters
from core.logger import log
from handlers.user_handler import handle_private_message, handle_movie_selection_callback
from handlers.start_handler import start_command, start_callback_handler
from handlers.list_handler import register_list_handlers, handle_list_callback
from handlers.ids import register_id_handlers, handle_id_callback

async def setup_handlers(client):
    """Register all message handlers"""
    
    # Register all handlers
    register_list_handlers(client)
    register_id_handlers(client)
    
    # Start command handler
    @client.on_message(filters.command("start") & filters.private)
    async def start_handler(client, message):
        await start_command(client, message)
    
    # Private message handler
    @client.on_message(filters.private & filters.incoming)
    async def private_message_handler(client, message):
        await handle_private_message(client, message)
    
    # Callback query handler - ORDER MATTERS!
    @client.on_callback_query()
    async def callback_query_handler(client, callback_query):
        data = callback_query.data
        
        # Handle ID callbacks first
        if data.startswith("id_send:") or data == "id_cancel":
            await handle_id_callback(client, callback_query)
        # Handle list callbacks
        elif data.startswith(("list_letter:", "send_letter:", "send_single:", "send_all:", "back_to_lists", "cancel_list")) or data in ["send_all_letters", "list_all", "list_back", "list_cancel"]:
            await handle_list_callback(client, callback_query)
        # Handle start callbacks
        elif data in ["help_guide", "search_movie", "close_message", "back_to_start"]:
            await start_callback_handler(client, callback_query)
        # Handle movie selection callbacks (catch-all for other callbacks)
        else:
            await handle_movie_selection_callback(client, callback_query)
    
    # Channel message handler
    from config import DATABASE_CHANNEL_ID
    @client.on_message(filters.chat(DATABASE_CHANNEL_ID) & filters.incoming)
    async def channel_message_handler(client, message):
        from handlers.channel_handler import handle_channel_message
        await handle_channel_message(client, message)
    
    log.success("🎯 All handlers registered successfully!")
