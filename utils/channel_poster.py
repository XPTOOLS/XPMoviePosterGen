from pyrogram.types import InlineKeyboardMarkup
from core.logger import log
from pyrogram import enums
from config import MOVIE_CHANNEL_ID
from utils.image_generator import poster_generator

async def send_to_channel(client, poster_path: str, caption: str, reply_markup: InlineKeyboardMarkup):
    """Send generated poster to movie channel and cleanup"""
    try:
        log.info(f"📤 Sending poster to channel: {MOVIE_CHANNEL_ID}")
        
        with open(poster_path, 'rb') as poster_file:
            message = await client.send_photo(
                chat_id=MOVIE_CHANNEL_ID,
                photo=poster_file,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        
        log.success(f"✅ Poster sent to channel successfully! Message ID: {message.id}")
        
        # Clean up poster file after sending
        poster_generator.cleanup_poster(poster_path)
        
        return message
        
    except Exception as e:
        # Clean up poster file even if sending fails
        poster_generator.cleanup_poster(poster_path)
        log.error(f"💥 Failed to send poster to channel: {e}")
        raise
