from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from core.logger import log
from pyrogram import enums
from utils.file_detector import extract_movie_title, extract_season_series_info
from utils.tmdb_api import tmdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption
from utils.channel_poster import send_to_channel
from database.movie_data import log_movie_request, mark_movie_processed
from config import POST_TO_CHANNEL, DOWNLOAD_BOT_LINK, PRIVATE_SEND_USER_ID

async def handle_channel_message(client, message: Message):
    """Handle messages in the database channel - auto-process movies"""
    try:
        log.info(f"📥 Channel message received in database channel (ID: {message.id})")
        
        # Extract movie title from message
        movie_title = await extract_movie_title(message)
        
        if movie_title:
            log.success(f"🎯 Detected movie in channel: {movie_title}")
            
            # Log the request
            file_size = message.document.file_size if message.document else message.video.file_size if message.video else None
            log_movie_request(movie_title, file_size, "channel")
            
            # Check if it's a series and extract series info
            series_info = extract_season_series_info(movie_title)
            if series_info and series_info['is_series']:
                log.info(f"📺 Series detected in channel: {movie_title}")
                # Process as TV series
                await _process_tv_series(client, series_info, message)
            else:
                # Process as regular movie
                await _process_movie(client, movie_title, message)
            
        else:
            log.warning("⚠️ No movie title detected in channel message")
            
    except Exception as e:
        log.error(f"💥 Error in channel message handler: {e}")

async def _process_movie(client, movie_title: str, original_message: Message):
    """Process regular movie"""
    try:
        # Extract year from title if present
        year = _extract_year_from_title(movie_title)
        clean_title = _remove_year_from_title(movie_title)
        
        # Search for movie
        movie_data = tmdb_api.get_movie_by_title_with_fallback(clean_title, year)
        
        if not movie_data:
            log.warning(f"❌ Movie not found in TMDB: {clean_title}")
            return
        
        log.info(f"✅ Found movie for channel processing: {movie_data['title']}")
        
        # Generate poster
        poster_path = poster_generator.generate_poster(movie_data)
        
        # Build caption
        caption = build_caption(movie_data)
        
        # Create download button
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)
        ]])
        
        # Send based on POST_TO_CHANNEL configuration
        if POST_TO_CHANNEL:
            # Send to movie channel
            await send_to_channel(client, poster_path, caption, download_button)
            log.success(f"✅ Movie sent to MOVIE_CHANNEL: {movie_data['title']}")
        else:
            # When POST_TO_CHANNEL=false, send to specified user privately
            try:
                with open(poster_path, 'rb') as poster_file:
                    await client.send_photo(
                        chat_id=PRIVATE_SEND_USER_ID,
                        photo=poster_file,
                        caption=caption,
                        reply_markup=download_button,
                        parse_mode=enums.ParseMode.HTML
                    )
                log.success(f"✅ Movie sent to user {PRIVATE_SEND_USER_ID}: {movie_data['title']}")
            except Exception as e:
                log.error(f"❌ Could not send to user {PRIVATE_SEND_USER_ID}: {e}")
                # Fallback: send to database channel
                await _send_to_database_channel(client, poster_path, caption, download_button, original_message)
            
            # Clean up the poster file
            poster_generator.cleanup_poster(poster_path)
        
        # Mark as processed
        mark_movie_processed(movie_title)
        
    except Exception as e:
        log.error(f"💥 Error processing movie {movie_title}: {e}")

async def _process_tv_series(client, series_info: dict, original_message: Message):
    """Process TV series episode"""
    try:
        series_name = series_info.get('series_name', '')
        season = series_info.get('season', 1)
        episode = series_info.get('episode')
        
        if not series_name:
            log.warning("❌ Could not extract series name")
            return
        
        log.info(f"🎬 Processing TV series: {series_name} - Season {season}, Episode {episode}")
        
        # Search for TV series on TMDB using the dedicated function
        series_data = tmdb_api.get_tv_series_by_title_with_fallback(series_name)
        
        if not series_data:
            log.warning(f"❌ TV series not found in TMDB: {series_name}")
            return
        
        log.info(f"✅ Found TV series: {series_data['title']}")
        
        # Generate poster for the series
        poster_path = poster_generator.generate_poster(series_data)
        
        # Build caption for TV series
        caption = _build_series_caption(series_data, season, episode)
        
        # Create download button
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)
        ]])
        
        # Send based on POST_TO_CHANNEL configuration
        if POST_TO_CHANNEL:
            # Send to movie channel
            await send_to_channel(client, poster_path, caption, download_button)
            log.success(f"✅ TV series sent to MOVIE_CHANNEL: {series_data['title']} S{season:02d}E{episode:02d}")
        else:
            # When POST_TO_CHANNEL=false, send to specified user privately
            try:
                with open(poster_path, 'rb') as poster_file:
                    await client.send_photo(
                        chat_id=PRIVATE_SEND_USER_ID,
                        photo=poster_file,
                        caption=caption,
                        reply_markup=download_button,
                        parse_mode=enums.ParseMode.HTML
                    )
                log.success(f"✅ TV series sent to user {PRIVATE_SEND_USER_ID}: {series_data['title']} S{season:02d}E{episode:02d}")
            except Exception as e:
                log.error(f"❌ Could not send to user {PRIVATE_SEND_USER_ID}: {e}")
                # Fallback: send to database channel
                await _send_to_database_channel(client, poster_path, caption, download_button, original_message)
            
            # Clean up the poster file
            poster_generator.cleanup_poster(poster_path)
        
        # Mark as processed
        original_title = f"{series_name} S{season:02d}E{episode:02d}"
        mark_movie_processed(original_title)
        
    except Exception as e:
        log.error(f"💥 Error processing TV series: {e}")

async def _search_tv_series(series_name: str):
    """Search for TV series on TMDB using the API"""
    try:
        # Use the TMDB API's TV series search
        log.debug(f"🔍 Searching TMDB for TV series: '{series_name}'")
        series_data = tmdb_api.get_tv_series_by_title(series_name)
        
        if series_data:
            log.info(f"✅ Found TV series via API: {series_data['title']}")
            return series_data
        
        # Try alternative search strategies
        log.info(f"🔄 Trying alternative searches for TV series: '{series_name}'")
        return await _try_alternative_series_searches(series_name)
        
    except Exception as e:
        log.error(f"💥 Error searching TV series via API: {e}")
        return None

async def _try_alternative_series_searches(series_name: str):
    """Try alternative search strategies for TV series"""
    alternatives = [
        series_name,  # Original
        series_name.title(),  # Proper case
        series_name.replace(" and ", " & "),  # Replace "and" with "&"
        series_name + " series",  # Add "series" suffix
        _remove_common_words(series_name),  # Remove common words
        _extract_main_title(series_name),  # Extract main title part
    ]
    
    # Remove duplicates
    alternatives = list(dict.fromkeys(alternatives))
    
    for alt_name in alternatives:
        if alt_name == series_name:
            continue  # Skip if same as original
            
        log.info(f"🔄 Trying alternative TV series search: '{alt_name}'")
        series_data = tmdb_api.get_tv_series_by_title(alt_name)
        if series_data:
            log.info(f"✅ Found via alternative search: '{alt_name}'")
            return series_data
    
    return None

def _remove_common_words(title: str) -> str:
    """Remove common words from title for better searching"""
    common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    words = title.split()
    filtered_words = [word for word in words if word.lower() not in common_words]
    return ' '.join(filtered_words)

def _extract_main_title(title: str) -> str:
    """Extract the main part of the title (first few words)"""
    words = title.split()
    if len(words) > 3:
        return ' '.join(words[:3])  # First 3 words
    return title

def _build_series_caption(series_data: dict, season: int, episode: int):
    """Build caption for TV series"""
    try:
        title = series_data['title']
        rating = series_data.get('tmdb_rating', 0)
        genres = series_data.get('genres', [])
        
        caption_parts = []
        
        # Title with season and episode
        caption_parts.append(f"🍿 {title} - S{season:02d}E{episode:02d}")
        caption_parts.append("")  # Empty line
        
        # Genres with hashtags
        if genres:
            genre_hashtags = " ".join([f"🎭 #{genre.replace(' ', '')}" for genre in genres[:3]])
            caption_parts.append(f"✲ Genre: {genre_hashtags}")
        
        # Rating
        if rating > 0:
            caption_parts.append(f"≛ IMDb : {rating} / 10")
        
        # Series info
        caption_parts.append(f"📺 Series • Season {season} • Episode {episode}")
        
        # Storyline
        overview = series_data.get('overview', '')
        if overview:
            caption_parts.append("")  # Empty line
            caption_parts.append("💬 Storyline:")
            if len(overview) > 200:
                overview = overview[:197] + "..."
            caption_parts.append(overview)
        
        # Footer
        caption_parts.append("")  # Empty line
        caption_parts.append("▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬")
        caption_parts.append(f"              •@Movieshub_101•")
        
        return "\n".join(caption_parts)
        
    except Exception as e:
        log.error(f"💥 Error building series caption: {e}")
        return f"🍿 {series_data.get('title', 'TV Series')} - S{season:02d}E{episode:02d}\n\n▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬\n              •@Movieshub_101•"

async def _send_to_database_channel(client, poster_path: str, caption: str, download_button: InlineKeyboardMarkup, original_message: Message):
    """Send poster back to database channel as fallback"""
    try:
        with open(poster_path, 'rb') as poster_file:
            await client.send_photo(
                chat_id=original_message.chat.id,
                photo=poster_file,
                caption=caption,
                reply_markup=download_button,
                reply_to_message_id=original_message.id,
                parse_mode=enums.ParseMode.HTML
            )
        log.success(f"✅ Sent back to DATABASE_CHANNEL (fallback)")
    except Exception as e:
        log.error(f"❌ Could not send to database channel: {e}")

def _extract_year_from_title(title: str) -> int:
    """Extract year from movie title"""
    import re
    year_match = re.search(r'\b(19|20)\d{2}\b', title)
    return int(year_match.group()) if year_match else None

def _remove_year_from_title(title: str) -> str:
    """Remove year from movie title"""
    import re
    return re.sub(r'\s*(19|20)\d{2}\s*', ' ', title).strip()