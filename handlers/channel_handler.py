from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from core.logger import log
from pyrogram import enums
import time
from utils.file_detector import extract_movie_title, extract_season_series_info
from utils.tmdb_api import tmdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption
from utils.channel_poster import send_to_channel
from database.movie_data import log_movie_request, mark_movie_processed, is_series_processed, mark_series_processed
from config import (
    POST_TO_CHANNEL, DOWNLOAD_BOT_LINK, PRIVATE_SEND_USER_ID, USE_IMDB_FALLBACK,
    COMMON_WORDS_TO_REMOVE, TITLE_CLEANING_PATTERNS, QUALITY_PATTERNS,
    SERIES_SEARCH_ALTERNATIVES, CACHE_CONFIG
)

# Cache to track processed series (to avoid duplicates within same session)
processed_series_cache = {}
# Cache to track recently processed movies/series to prevent duplicates
recently_processed = {}

async def handle_channel_message(client, message: Message):
    """Handle messages in the database channel - auto-process movies"""
    try:
        log.info(f"📥 Channel message received in database channel (ID: {message.id})")
        
        # Extract movie title from message with caption fallback
        movie_title, year = await extract_movie_title_with_caption_fallback(message)
        
        if movie_title:
            log.success(f"🎯 Detected movie in channel: {movie_title}")
            
            # Log the request
            file_size = message.document.file_size if message.document else message.video.file_size if message.video else None
            log_movie_request(movie_title, file_size, "channel")
            
            # Check if it's a series and extract series info
            series_info = extract_season_series_info(movie_title)
            if series_info and series_info['is_series']:
                log.info(f"📺 Series detected in channel: {movie_title}")
                
                # Check if we should process this series (deduplication)
                if await _should_process_series(series_info, message):
                    # Process as TV series (only one poster per season)
                    await _process_tv_series(client, series_info, message, year)
                else:
                    log.info(f"⏭️ Skipping duplicate series episode: {movie_title}")
            else:
                # Process as regular movie (check for duplicates)
                if await _should_process_movie(movie_title, message):
                    await _process_movie(client, movie_title, year, message)
                else:
                    log.info(f"⏭️ Skipping duplicate movie: {movie_title}")
            
        else:
            log.warning("⚠️ No movie title detected in channel message")
            
    except Exception as e:
        log.error(f"💥 Error in channel message handler: {e}")

async def _should_process_movie(movie_title: str, message: Message) -> bool:
    """Check if we should process this movie (prevent duplicates)"""
    try:
        # Clean the movie title for comparison
        clean_title = _clean_title_for_comparison(movie_title)
        
        # Create a unique key for this movie
        movie_key = f"movie_{clean_title}"
        
        # Check if this movie was recently processed (within cooldown period)
        current_time = time.time()
        if movie_key in recently_processed:
            last_processed = recently_processed[movie_key]
            if current_time - last_processed < CACHE_CONFIG['movie_cooldown']:
                log.info(f"⏭️ Movie recently processed: {movie_title}")
                return False
        
        # Mark this movie as processed
        recently_processed[movie_key] = current_time
        
        # Clean up old entries
        if len(recently_processed) > CACHE_CONFIG['max_cache_entries']:
            # Remove oldest entries
            oldest_keys = sorted(recently_processed.keys(), key=lambda k: recently_processed[k])[:CACHE_CONFIG['cleanup_batch_size']]
            for key in oldest_keys:
                del recently_processed[key]
        
        return True
        
    except Exception as e:
        log.error(f"💥 Error checking movie processing: {e}")
        return True  # Default to processing if there's an error

def _clean_title_for_comparison(title: str) -> str:
    """Clean title for duplicate comparison"""
    import re
    
    clean_title = title
    
    # Apply cleaning patterns from config
    for pattern in TITLE_CLEANING_PATTERNS:
        clean_title = re.sub(pattern, ' ', clean_title)
    
    # Remove quality/resolution patterns from config
    for pattern in QUALITY_PATTERNS:
        clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
    
    # Also use the common indicators pattern from list handler
    from config import COMMON_INDICATORS_PATTERN
    clean_title = re.sub(COMMON_INDICATORS_PATTERN, '', clean_title, flags=re.IGNORECASE)
    
    clean_title = re.sub(r'\s+', ' ', clean_title).strip().lower()
    return clean_title

async def extract_movie_title_with_caption_fallback(message: Message):
    """Extract movie title with filename first, then caption as fallback"""
    try:
        # First try: Extract from filename/document
        movie_title, year = await extract_movie_title(message)
        
        # If filename extraction failed or returned empty, try caption as fallback
        if not movie_title and message.caption:
            log.info("🔄 Filename extraction failed, trying caption fallback...")
            from utils.file_detector import _extract_title_and_year
            movie_title, year = _extract_title_and_year(message.caption)
            
            if movie_title:
                log.success(f"✅ Found movie title from caption: {movie_title}")
        
        # If still no title, try to extract from text content if available
        if not movie_title and hasattr(message, 'text') and message.text:
            log.info("🔄 Trying text content as fallback...")
            from utils.file_detector import _extract_title_and_year
            movie_title, year = _extract_title_and_year(message.text)
            
            if movie_title:
                log.success(f"✅ Found movie title from text: {movie_title}")
        
        return movie_title, year
        
    except Exception as e:
        log.error(f"💥 Error in caption fallback extraction: {e}")
        return None, None

async def _should_process_series(series_info: dict, message: Message) -> bool:
    """Check if we should process this series episode (deduplication logic)"""
    try:
        series_name = series_info.get('series_name', '').lower().strip()
        season = series_info.get('season', 1)
        
        if not series_name:
            return True  # Process if we can't extract series name
        
        # Create a unique key for this series + season
        series_key = f"{series_name}_s{season}"
        
        # Check database if this series season was already processed
        if is_series_processed(series_name, season):
            log.info(f"⏭️ Series season already processed in database: {series_name} S{season}")
            return False
        
        # Check in-memory cache (for same session duplicates)
        if series_key in processed_series_cache:
            log.info(f"⏭️ Series season already processed in this session: {series_name} S{season}")
            return False
        
        # Check recently processed cache
        current_time = time.time()
        if series_key in recently_processed:
            last_processed = recently_processed[series_key]
            if current_time - last_processed < CACHE_CONFIG['series_cooldown']:
                log.info(f"⏭️ Series season recently processed: {series_name} S{season}")
                return False
        
        # Mark this series season as processed in caches
        processed_series_cache[series_key] = True
        recently_processed[series_key] = current_time
        
        log.info(f"✅ First episode of series season: {series_name} S{season}")
        return True
        
    except Exception as e:
        log.error(f"💥 Error checking series processing: {e}")
        return True  # Default to processing if there's an error

async def _process_movie(client, movie_title: str, year: int, original_message: Message):
    """Process regular movie with IMDB primary search"""
    try:
        log.info(f"🎬 Processing movie: '{movie_title}' (year: {year})")
        
        # Search for movie using IMDB primary + TMDB fallback
        movie_data = await _search_movie_with_imdb_primary(movie_title, year)
        
        if not movie_data:
            log.warning(f"❌ Movie not found in IMDB or TMDB: {movie_title}")
            return
        
        log.info(f"✅ Found movie for channel processing: {movie_data['title']} ({movie_data.get('release_year', 'N/A')})")
        
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

async def _search_movie_with_imdb_primary(movie_title: str, year: int = None):
    """Search movie with IMDB as primary and TMDB as fallback"""
    try:
        # Step 1: Try IMDB first (PRIMARY)
        if USE_IMDB_FALLBACK:
            from utils.imdb_api import imdb_api
            imdb_data = imdb_api.get_movie_by_title(movie_title, year)
            if imdb_data:
                log.info(f"✅ Found via IMDB primary: {imdb_data['title']}")
                return imdb_data
        
        # Step 2: Fallback to TMDB
        log.info(f"🔄 IMDB failed, trying TMDB fallback for: {movie_title}")
        movie_data = tmdb_api.get_media_by_title(movie_title, year)
        if movie_data:
            log.info(f"✅ Found via TMDB fallback: {movie_data['title']}")
            return movie_data
        
        # Step 3: Try TMDB with IMDB fallback (original method)
        log.info(f"🔄 Trying TMDB with IMDB fallback for: {movie_title}")
        return tmdb_api.get_media_by_title_with_fallback(movie_title, year)
        
    except Exception as e:
        log.error(f"💥 Error in IMDB primary search: {e}")
        # Final fallback to original TMDB method
        return tmdb_api.get_media_by_title(movie_title, year)

async def _process_tv_series(client, series_info: dict, original_message: Message, year: int = None):
    """Process TV series episode with IMDB primary search - ONLY ONE PER SEASON"""
    try:
        series_name = series_info.get('series_name', '')
        season = series_info.get('season', 1)
        
        if not series_name:
            log.warning("❌ Could not extract series name")
            return
        
        log.info(f"🎬 Processing TV series: {series_name} - Season {season}")
        
        # Search for TV series with IMDB primary
        series_data = await _search_tv_series_with_imdb_primary(series_name, year)
        
        if not series_data:
            log.warning(f"❌ TV series not found in IMDB or TMDB: {series_name}")
            return
        
        # Check if it's actually a TV series
        if series_data.get('media_type') != 'tv':
            log.warning(f"⚠️ Found media is not a TV series: {series_data.get('media_type')}")
            # Try to search specifically for TV series
            tv_results = tmdb_api.search_tv_series(series_name, year, limit=1)
            if tv_results:
                series_data = tmdb_api.get_tv_series_details(tv_results[0]['id'])
        
        log.info(f"✅ Found TV series: {series_data['title']}")
        
        # Generate poster for the series (season poster, not episode-specific)
        poster_path = poster_generator.generate_poster(series_data)
        
        # Build caption for TV series (generic season caption, not episode-specific)
        caption = _build_series_caption(series_data, season)
        
        # Create download button
        download_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)
        ]])
        
        # Send based on POST_TO_CHANNEL configuration
        if POST_TO_CHANNEL:
            # Send to movie channel
            await send_to_channel(client, poster_path, caption, download_button)
            log.success(f"✅ TV series sent to MOVIE_CHANNEL: {series_data['title']} Season {season}")
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
                log.success(f"✅ TV series sent to user {PRIVATE_SEND_USER_ID}: {series_data['title']} Season {season}")
            except Exception as e:
                log.error(f"❌ Could not send to user {PRIVATE_SEND_USER_ID}: {e}")
                # Fallback: send to database channel
                await _send_to_database_channel(client, poster_path, caption, download_button, original_message)
            
            # Clean up the poster file
            poster_generator.cleanup_poster(poster_path)
        
        # Mark series season as processed in database
        mark_series_processed(series_name, season)
        
    except Exception as e:
        log.error(f"💥 Error processing TV series: {e}")

async def _search_tv_series_with_imdb_primary(series_name: str, year: int = None):
    """Search TV series with IMDB as primary and TMDB as fallback"""
    try:
        # Step 1: Try IMDB first (PRIMARY)
        if USE_IMDB_FALLBACK:
            from utils.imdb_api import imdb_api
            # Search specifically for TV series on IMDB
            imdb_results = imdb_api.search_tv_series(series_name, year, limit=1)
            if imdb_results:
                imdb_id = imdb_results[0]['id']
                imdb_data = imdb_api.get_movie_details(imdb_id)
                if imdb_data and imdb_data.get('media_type') == 'tv':
                    log.info(f"✅ Found TV series via IMDB primary: {imdb_data['title']}")
                    return imdb_data
        
        # Step 2: Fallback to TMDB
        log.info(f"🔄 IMDB failed, trying TMDB fallback for TV series: {series_name}")
        series_data = tmdb_api.get_media_by_title(series_name, year)
        if series_data and series_data.get('media_type') == 'tv':
            log.info(f"✅ Found via TMDB fallback: {series_data['title']}")
            return series_data
        
        # Step 3: Try TMDB TV series search specifically
        log.info(f"🔄 Trying TMDB TV series specific search for: {series_name}")
        tv_results = tmdb_api.search_tv_series(series_name, year, limit=1)
        if tv_results:
            series_data = tmdb_api.get_tv_series_details(tv_results[0]['id'])
            if series_data:
                log.info(f"✅ Found via TMDB TV search: {series_data['title']}")
                return series_data
        
        return None
        
    except Exception as e:
        log.error(f"💥 Error in IMDB primary TV search: {e}")
        # Final fallback to original TMDB method
        return tmdb_api.get_media_by_title(series_name, year)

def _mark_series_processed(series_name: str, season: int):
    """Mark a series season as processed in the database"""
    try:
        # This would be implemented in your movie_data.py
        # For now, we'll just log it
        log.info(f"📝 Marking series as processed: {series_name} Season {season}")
        # You would implement database storage here
    except Exception as e:
        log.error(f"💥 Error marking series as processed: {e}")


async def _search_tv_series(series_name: str, year: int = None):
    """Search for TV series on TMDB using the API"""
    try:
        # Use the TMDB API's TV series search
        log.debug(f"🔍 Searching TMDB for TV series: '{series_name}'")
        tv_results = tmdb_api.search_tv_series(series_name, year, limit=1)
        
        if tv_results:
            series_data = tmdb_api.get_tv_series_details(tv_results[0]['id'])
            if series_data:
                log.info(f"✅ Found TV series via API: {series_data['title']}")
                return series_data
        
        # Try alternative search strategies
        log.info(f"🔄 Trying alternative searches for TV series: '{series_name}'")
        return await _try_alternative_series_searches(series_name, year)
        
    except Exception as e:
        log.error(f"💥 Error searching TV series via API: {e}")
        return None

async def _try_alternative_series_searches(series_name: str, year: int = None):
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
        tv_results = tmdb_api.search_tv_series(alt_name, year, limit=1)
        if tv_results:
            series_data = tmdb_api.get_tv_series_details(tv_results[0]['id'])
            if series_data:
                log.info(f"✅ Found via alternative search: '{alt_name}'")
                return series_data
    
    return None

def _remove_common_words(title: str) -> str:
    """Remove common words from title for better searching"""
    words = title.split()
    filtered_words = [word for word in words if word.lower() not in COMMON_WORDS_TO_REMOVE]
    return ' '.join(filtered_words)

async def _try_alternative_series_searches(series_name: str, year: int = None):
    """Try alternative search strategies for TV series using config"""
    alternatives = []
    
    for alternative_template in SERIES_SEARCH_ALTERNATIVES:
        if alternative_template == "{original}":
            alt_name = series_name
        elif alternative_template == "{title_case}":
            alt_name = series_name.title()
        elif alternative_template == "{and_to_ampersand}":
            alt_name = series_name.replace(" and ", " & ")
        elif alternative_template == "{series_suffix}":
            alt_name = series_name + " series"
        elif alternative_template == "{remove_common_words}":
            alt_name = _remove_common_words(series_name)
        elif alternative_template == "{extract_main_title}":
            alt_name = _extract_main_title(series_name)
        else:
            alt_name = alternative_template
        
        if alt_name not in alternatives:
            alternatives.append(alt_name)
    
    for alt_name in alternatives:
        if alt_name == series_name:
            continue  # Skip if same as original
            
        log.info(f"🔄 Trying alternative TV series search: '{alt_name}'")
        tv_results = tmdb_api.search_tv_series(alt_name, year, limit=1)
        if tv_results:
            series_data = tmdb_api.get_tv_series_details(tv_results[0]['id'])
            if series_data:
                log.info(f"✅ Found via alternative search: '{alt_name}'")
                return series_data
    
    return None

def _extract_main_title(title: str) -> str:
    """Extract the main part of the title (first few words)"""
    words = title.split()
    if len(words) > 3:
        return ' '.join(words[:3])  # First 3 words
    return title

def _build_series_caption(series_data: dict, season: int):
    """Build caption for TV series (generic season caption)"""
    try:
        title = series_data['title']
        rating = series_data.get('tmdb_rating', 0)
        genres = series_data.get('genres', [])
        
        caption_parts = []
        
        # Title with season (no specific episode)
        caption_parts.append(f"🍿 {title} - Season {season}")
        caption_parts.append("")  # Empty line
        
        # Genres with hashtags
        if genres:
            genre_hashtags = " ".join([f"🎭 #{genre.replace(' ', '')}" for genre in genres[:3]])
            caption_parts.append(f"✲ Genre: {genre_hashtags}")
        
        # Rating
        if rating > 0:
            caption_parts.append(f"≛ IMDb : {rating} / 10")
        
        # Series info (generic, not episode-specific)
        caption_parts.append(f"📺 TV Series • Complete Season {season}")
        
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
        return f"🍿 {series_data.get('title', 'TV Series')} - Season {season}\n\n▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬\n              •@Movieshub_101•"

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
