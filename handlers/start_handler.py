from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from config import WELCOME_IMAGE_URL
from loguru import logger

# Start command handler
async def start_command(client: Client, message: Message):
    try:
        logger.info(f"🚀 Start command received from user {message.from_user.id} (@{message.from_user.username})")
        
        # Welcome caption
        welcome_caption = """
🎬 **Welcome to Movie Poster Bot!**

I can generate beautiful 1280×720 movie posters automatically using TMDB/IMDB data.

**Features:**
• Auto-detect movies from messages
• Generate HD posters (1280×720)
• TMDB/IMDB integration
• Series deduplication
• Channel posting support

Use /help to see all commands!
        """
        
        # Create inline keyboard with buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 How to Use", callback_data="help_guide"),
                InlineKeyboardButton("🔍 Search Movie", callback_data="search_movie")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close_message")
            ]
        ])
        
        # Send welcome message with photo and buttons
        logger.debug(f"🖼️ Sending welcome image to user {message.from_user.id}")
        await message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=welcome_caption,
            reply_markup=keyboard
        )
        logger.success(f"✅ Welcome message sent successfully to user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"💥 Failed to send start message to user {message.from_user.id}: {str(e)}")
        await message.reply_text("❌ Failed to load welcome message. Please try again.")

# Callback query handler for start menu buttons
async def start_callback_handler(client: Client, callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        logger.info(f"🔄 Callback received from user {user_id}: {data}")
        
        if data == "close_message":
            # Delete the message when close is clicked
            logger.debug(f"🗑️ Closing welcome message for user {user_id}")
            await callback_query.message.delete()
            await callback_query.answer("👋 Welcome message closed")
            logger.success(f"✅ Message closed for user {user_id}")
        
        elif data == "help_guide":
            logger.debug(f"📚 Showing help guide to user {user_id}")
            help_text = """
**How to Use Movie Poster Bot:**

1. **Send a movie name** - I'll automatically detect and generate a poster
2. **Forward a movie message** - From any channel or chat
3. **Use /search command** - To search for specific movies

I'll create a beautiful 1280×720 poster with movie details, ratings, and genres!
            """
            await callback_query.message.edit_caption(
                caption=help_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
                    [InlineKeyboardButton("❌ Close", callback_data="close_message")]
                ])
            )
            await callback_query.answer()
            logger.success(f"✅ Help guide displayed for user {user_id}")
        
        elif data == "search_movie":
            logger.debug(f"🔍 Showing search instructions to user {user_id}")
            search_text = """
**Search for a Movie:**

Simply type the movie name and send it to me, or use:
`/search <movie_name>`

I'll search TMDB/IMDB and generate a poster for you!
            """
            await callback_query.message.edit_caption(
                caption=search_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
                    [InlineKeyboardButton("❌ Close", callback_data="close_message")]
                ])
            )
            await callback_query.answer()
            logger.success(f"✅ Search instructions shown to user {user_id}")
        
        elif data == "back_to_start":
            logger.debug(f"🔙 Returning to start menu for user {user_id}")
            welcome_caption = """
🎬 **Welcome to Movie Poster Bot!**

I can generate beautiful 1280×720 movie posters automatically using TMDB/IMDB data.

**Features:**
• Auto-detect movies from messages
• Generate HD posters (1280×720)
• TMDB/IMDB integration
• Series deduplication
• Channel posting support

Use /help to see all commands!
            """
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📖 How to Use", callback_data="help_guide"),
                    InlineKeyboardButton("🔍 Search Movie", callback_data="search_movie")
                ],
                [
                    InlineKeyboardButton("❌ Close", callback_data="close_message")
                ]
            ])
            await callback_query.message.edit_caption(
                caption=welcome_caption,
                reply_markup=keyboard
            )
            await callback_query.answer()
            logger.success(f"✅ Returned to start menu for user {user_id}")
            
    except Exception as e:
        logger.error(f"💥 Callback handler error for user {callback_query.from_user.id}: {str(e)}")
        await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)

# Register start handlers
def register_start_handlers(client: Client):
    client.on_message(filters.command("start") & filters.private)(start_command)
    client.on_callback_query(filters.regex(r"^(help_guide|search_movie|close_message|back_to_start)$"))(start_callback_handler)
    logger.info("🎯 Start handlers registered successfully")