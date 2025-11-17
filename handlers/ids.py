from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from pyrogram import enums
from utils.tmdb_api import tmdb_api
from utils.imdb_api import imdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption
from utils.channel_poster import send_to_channel
from database.movie_data import log_movie_request, mark_movie_processed
from config import POST_TO_CHANNEL, DOWNLOAD_BOT_LINK, LIST_CHANNEL_ID, USE_IMDB_FALLBACK
from core.logger import log

async def id_command(client: Client, message: Message):
    """Handle /id command to search movies by ID"""
    try:
        # Extract ID from command
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.reply_text(
                "❌ <b>Usage:</b> <code>/id [movie_id]</code>\n\n"
                "📝 <b>Examples:</b>\n"
                "<code>/id tt1234567</code> - IMDB ID\n"
                "<code>/id 12345</code> - TMDB ID\n\n"
                "🔍 <b>Note:</b> IMDB IDs start with 'tt', TMDB IDs are numbers",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        movie_id = command_parts[1].strip()
        log.info(f"🔍 ID search requested: {movie_id} by user {message.from_user.id}")
        
        # Show processing message
        processing_msg = await message.reply_text(
            f"🔄 <b>Searching for ID:</b> <code>{movie_id}</code>\n\n"
            "⏳ Please wait...",
            parse_mode=enums.ParseMode.HTML
        )
        
        # Determine ID type and search
        movie_data = await _search_by_id(movie_id)
        
        if not movie_data:
            await processing_msg.edit_text(
                f"❌ <b>Movie not found!</b>\n\n"
                f"ID: <code>{movie_id}</code>\n\n"
                "💡 <b>Tips:</b>\n"
                "• Check if the ID is correct\n"
                "• Try IMDB ID (starts with 'tt')\n"
                "• Try TMDB ID (numbers only)",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        # Show movie found and ask for destination
        await processing_msg.edit_text(
            f"✅ <b>Movie Found!</b>\n\n"
            f"🎬 <b>Title:</b> {movie_data['title']}\n"
            f"📅 <b>Year:</b> {movie_data.get('release_year', 'N/A')}\n"
            f"🎭 <b>Type:</b> {movie_data.get('media_type', 'movie').title()}\n\n"
            f"<i>Where should I send the poster?</i>",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📤 Send to Channel", callback_data=f"id_send:{movie_id}:channel"),
                    InlineKeyboardButton("🤖 Send to Me", callback_data=f"id_send:{movie_id}:bot")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="id_cancel")
                ]
            ]),
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error in /id command: {e}")
        await message.reply_text("❌ An error occurred while processing your request.")

async def _search_by_id(movie_id: str):
    """Search movie by ID (IMDB or TMDB)"""
    try:
        # Check if it's an IMDB ID (starts with tt)
        if movie_id.startswith('tt'):
            log.info(f"🔍 Searching IMDB with ID: {movie_id}")
            return await _search_imdb_by_id(movie_id)
        else:
            # Assume it's a TMDB ID
            log.info(f"🔍 Searching TMDB with ID: {movie_id}")
            return await _search_tmdb_by_id(movie_id)
            
    except Exception as e:
        log.error(f"💥 Error searching by ID {movie_id}: {e}")
        return None

async def _search_imdb_by_id(imdb_id: str):
    """Search movie by IMDB ID"""
    try:
        if USE_IMDB_FALLBACK:
            # Try to use IMDB API if available
            try:
                movie_data = imdb_api.get_movie_details(imdb_id)
                if movie_data:
                    log.success(f"✅ Found via IMDB ID: {movie_data.get('title', 'Unknown')}")
                    return movie_data
            except AttributeError:
                log.warning("⚠️ IMDB API doesn't support get_movie_details with ID, using TMDB fallback")
            except Exception as e:
                log.warning(f"⚠️ IMDB API failed: {e}, using TMDB fallback")
        
        # Fallback to TMDB search by IMDB ID
        log.info(f"🔄 Using TMDB with IMDB ID: {imdb_id}")
        movie_data = tmdb_api.get_media_by_imdb_id(imdb_id)
        if movie_data:
            log.success(f"✅ Found via TMDB with IMDB ID: {movie_data.get('title', 'Unknown')}")
            return movie_data
        
        return None
        
    except Exception as e:
        log.error(f"💥 Error searching IMDB by ID: {e}")
        return None

async def _search_tmdb_by_id(tmdb_id: str):
    """Search movie by TMDB ID"""
    try:
        # First try as movie
        movie_data = tmdb_api.get_movie_details(int(tmdb_id))
        if movie_data:
            log.success(f"✅ Found as movie via TMDB ID: {movie_data.get('title', 'Unknown')}")
            return movie_data
        
        # Then try as TV series
        movie_data = tmdb_api.get_tv_series_details(int(tmdb_id))
        if movie_data:
            log.success(f"✅ Found as TV series via TMDB ID: {movie_data.get('title', 'Unknown')}")
            return movie_data
        
        return None
        
    except ValueError:
        log.error(f"❌ Invalid TMDB ID format: {tmdb_id}")
        return None
    except Exception as e:
        log.error(f"💥 Error searching TMDB by ID: {e}")
        return None

async def _process_id_sending(client, callback_query, movie_id: str, target: str):
    """Process sending movie poster by ID"""
    try:
        await callback_query.answer("🔄 Processing...")
        
        # Search for the movie again to get fresh data
        movie_data = await _search_by_id(movie_id)
        
        if not movie_data:
            await callback_query.message.edit_text(
                "❌ <b>Movie not found!</b>\n\n"
                "The ID might be invalid or the movie data is unavailable.",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        # Generate poster
        poster_path = poster_generator.generate_poster(movie_data)
        
        if not poster_path:
            await callback_query.message.edit_text(
                "❌ <b>Failed to generate poster!</b>\n\n"
                "Could not create the movie poster.",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        # Build caption
        caption = build_caption(movie_data)
        
        # Create download button
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Click to Download", url=DOWNLOAD_BOT_LINK)
        ]])
        
        chat_id = LIST_CHANNEL_ID if target == "channel" else callback_query.from_user.id
        chat_name = "channel" if target == "channel" else "you"
        
        # Send the poster
        if target == "channel":
            await send_to_channel(client, poster_path, caption, download_button)
        else:
            with open(poster_path, 'rb') as poster_file:
                await client.send_photo(
                    chat_id=chat_id,
                    photo=poster_file,
                    caption=caption,
                    reply_markup=download_button,
                    parse_mode=enums.ParseMode.HTML
                )
            # Clean up the poster file for bot sends
            poster_generator.cleanup_poster(poster_path)
        
        # Log the movie request and mark as processed
        log_movie_request(movie_data['title'], None, callback_query.from_user.id)
        mark_movie_processed(movie_data['title'])
        
        # Update the message
        await callback_query.message.edit_text(
            f"✅ <b>Poster successfully sent to {chat_name}!</b>\n\n"
            f"🎬 <b>Title:</b> {movie_data['title']}\n"
            f"📅 <b>Year:</b> {movie_data.get('release_year', 'N/A')}\n"
            f"🎭 <b>Type:</b> {movie_data.get('media_type', 'movie').title()}\n\n"
            f"📍 <b>Added to alphabet lists</b>\n"
            f"🔤 <b>List letter:</b> {movie_data['title'][0].upper()}",
            parse_mode=enums.ParseMode.HTML
        )
        
        log.success(f"✅ Movie by ID sent to {chat_name}: {movie_data['title']} by user {callback_query.from_user.id}")
        
    except Exception as e:
        log.error(f"💥 Error processing ID sending: {e}")
        await callback_query.message.edit_text("❌ Failed to send poster.")

async def handle_id_callback(client, callback_query):
    """Handle callback for ID commands"""
    try:
        data = callback_query.data
        
        if data.startswith("id_send:"):
            _, movie_id, target = data.split(":")
            await _process_id_sending(client, callback_query, movie_id, target)
        elif data == "id_cancel":
            await callback_query.answer("❌ Cancelled")
            await callback_query.message.delete()
        else:
            await callback_query.answer("❌ Unknown action")
            
    except Exception as e:
        log.error(f"💥 Error in ID callback: {e}")
        await callback_query.answer("❌ Error processing your request.")

# Register ID handlers
def register_id_handlers(client: Client):
    client.on_message(filters.command("id") & filters.private)(id_command)
    client.on_callback_query(filters.regex(r"^(id_send:|id_cancel)$"))(handle_id_callback)
    log.info("🎯 ID handlers registered successfully")