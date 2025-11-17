from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from core.logger import log
from utils.file_detector import extract_movie_title, extract_season_series_info
from utils.tmdb_api import tmdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption
from utils.channel_poster import send_to_channel
from database.movie_data import log_movie_request, mark_movie_processed, is_series_processed, mark_series_processed
from config import POST_TO_CHANNEL, DOWNLOAD_BOT_LINK, USE_IMDB_FALLBACK

# Store user sessions temporarily
user_sessions = {}
processed_series_cache = {}

async def handle_private_message(client, message: Message):
    """Handle private messages sent directly to the bot"""
    try:
        log.info(f"👤 Private message from {message.from_user.id} - {message.from_user.first_name}")
        
        movie_title, year = await extract_movie_title_with_caption_fallback(message)
        
        if movie_title:
            log.success(f"🎯 Detected movie title: {movie_title}")
            
            file_size = message.document.file_size if message.document else message.video.file_size if message.video else None
            log_movie_request(movie_title, file_size, message.from_user.id)
            
            series_info = extract_season_series_info(movie_title)
            if series_info and series_info['is_series']:
                if await _should_process_series(series_info, message):
                    await _handle_series_request(client, message, movie_title, series_info)
                else:
                    await message.reply_text(
                        f"📺 <b>Series Already Processed</b>\n\n"
                        f"Series: <b>{series_info.get('series_name', movie_title)}</b>\n"
                        f"Season: <b>{series_info.get('season', 1)}</b>\n\n"
                        "✅ This series season has already been processed.",
                        parse_mode=enums.ParseMode.HTML
                    )
            else:
                await _handle_movie_selection(client, message, movie_title, year)
            
        else:
            await message.reply_text(
                "❌ I couldn't detect a movie title in your message.\n\n"
                "Please send:\n• Movie name as text\n• Movie file with title in filename\n• Poster image with movie name in caption",
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        log.error(f"💥 Error in private message handler: {e}")
        await message.reply_text("❌ An error occurred while processing your request.")

async def extract_movie_title_with_caption_fallback(message: Message):
    """Extract movie title with filename first, then caption as fallback"""
    try:
        movie_title, year = await extract_movie_title(message)
        
        if not movie_title and message.caption:
            log.info("🔄 Filename extraction failed, trying caption fallback...")
            from utils.file_detector import _extract_title_and_year
            movie_title, year = _extract_title_and_year(message.caption)
            
        if not movie_title and hasattr(message, 'text') and message.text:
            log.info("🔄 Trying text content as fallback...")
            from utils.file_detector import _extract_title_and_year
            movie_title, year = _extract_title_and_year(message.text)
        
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
            return True
        
        series_key = f"{series_name}_s{season}"
        
        if is_series_processed(series_name, season):
            log.info(f"⏭️ Series season already processed in database: {series_name} S{season}")
            return False
        
        if series_key in processed_series_cache:
            log.info(f"⏭️ Series season already processed in this session: {series_name} S{season}")
            return False
        
        processed_series_cache[series_key] = True
        log.info(f"✅ First episode of series season: {series_name} S{season}")
        return True
        
    except Exception as e:
        log.error(f"💥 Error checking series processing: {e}")
        return True

async def _handle_movie_selection(client, message: Message, movie_title: str, year: int = None):
    """Show multiple movie options for user to choose from with pagination"""
    try:
        processing_msg = await message.reply_text(
            f"🎬 <b>Searching for:</b> {movie_title}\n\n🔍 Searching IMDB (Primary)...",
            parse_mode=enums.ParseMode.HTML
        )
        
        extracted_year = year
        if not extracted_year:
            extracted_year = _extract_year_from_title(movie_title)
        
        clean_title = _remove_year_from_title(movie_title)
        series_info = extract_season_series_info(movie_title)
        
        all_movies = await _search_with_imdb_primary(clean_title, extracted_year, series_info)
        
        if not all_movies:
            await processing_msg.edit_text(
                f"❌ <b>No movies found for:</b> {clean_title}\n\nTry:\n• Check spelling\n• Use English title\n• Be more specific",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        user_sessions[message.from_user.id] = {
            "all_movies": all_movies,
            "current_page": 0,
            "original_title": movie_title,
            "processing_msg_id": processing_msg.id,
            "total_pages": (len(all_movies) + 4) // 5,
            "year": extracted_year
        }
        
        await _show_movie_page(client, processing_msg, message.from_user.id, 0)
        
    except Exception as e:
        log.error(f"💥 Error in movie selection: {e}")
        await message.reply_text(f"❌ Error: {str(e)}", parse_mode=enums.ParseMode.HTML)

async def _search_with_imdb_primary(clean_title: str, extracted_year: int, series_info: dict = None):
    """Search using IMDB as primary with TMDB fallback"""
    try:
        all_results = []
        
        if USE_IMDB_FALLBACK:
            from utils.imdb_api import imdb_api
            
            if series_info and series_info['is_series']:
                imdb_results = imdb_api.search_tv_series(clean_title, extracted_year, limit=20)
                log.info(f"✅ IMDB TV search found {len(imdb_results)} results")
                all_results.extend(imdb_results)
                
                imdb_movie_results = imdb_api.search_movie(clean_title, extracted_year, limit=10)
                all_results.extend(imdb_movie_results)
            else:
                imdb_results = imdb_api.unified_search(clean_title, extracted_year, limit=30)
                log.info(f"✅ IMDB unified search found {len(imdb_results)} results")
                all_results.extend(imdb_results)
        
        if len(all_results) < 10:
            log.info(f"🔄 IMDB returned few results, trying TMDB fallback for: {clean_title}")
            
            tmdb_tv_count = 0
            tmdb_movie_count = 0
            
            if series_info and series_info['is_series']:
                tmdb_tv_results = tmdb_api.search_tv_series(clean_title, extracted_year, limit=20)
                tmdb_tv_count = len(tmdb_tv_results)
                for result in tmdb_tv_results:
                    all_results.append({
                        'id': result['id'],
                        'title': result.get('name', ''),
                        'release_year': result.get('release_year', 'Unknown'),
                        'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                        'media_type': 'tv',
                        'source': 'tmdb',
                        'vote_average': result.get('vote_average', 0),
                        'vote_count': result.get('vote_count', 0)
                    })
            
            tmdb_movie_results = tmdb_api.search_movies(clean_title, extracted_year, limit=20)
            tmdb_movie_count = len(tmdb_movie_results)
            for result in tmdb_movie_results:
                all_results.append({
                    'id': result['id'],
                    'title': result.get('title', ''),
                    'release_year': result.get('release_year', 'Unknown'),
                    'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                    'media_type': 'movie',
                    'source': 'tmdb',
                    'vote_average': result.get('vote_average', 0),
                    'vote_count': result.get('vote_count', 0)
                })
            
            log.info(f"✅ TMDB fallback found {tmdb_tv_count + tmdb_movie_count} additional results")

        unique_results = _remove_duplicates(all_results)
        log.info(f"🎯 Total unique results: {len(unique_results)}")
        
        return unique_results[:50]
        
    except Exception as e:
        log.error(f"💥 Error in IMDB primary search: {e}")
        return _fallback_to_tmdb_only(clean_title, extracted_year, series_info)

def _fallback_to_tmdb_only(clean_title: str, extracted_year: int, series_info: dict = None):
    """Fallback to TMDB only search"""
    try:
        all_results = []
        
        if series_info and series_info['is_series']:
            tmdb_results = tmdb_api.search_tv_series(clean_title, extracted_year, limit=30)
            for result in tmdb_results:
                all_results.append({
                    'id': result['id'],
                    'title': result.get('name', ''),
                    'release_year': result.get('release_year', 'Unknown'),
                    'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                    'media_type': 'tv',
                    'source': 'tmdb',
                    'vote_average': result.get('vote_average', 0),
                    'vote_count': result.get('vote_count', 0)
                })
        
        tmdb_movie_results = tmdb_api.search_movies(clean_title, extracted_year, limit=30)
        for result in tmdb_movie_results:
            all_results.append({
                'id': result['id'],
                'title': result.get('title', ''),
                'release_year': result.get('release_year', 'Unknown'),
                'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                'media_type': 'movie',
                'source': 'tmdb',
                'vote_average': result.get('vote_average', 0),
                'vote_count': result.get('vote_count', 0)
            })
        
        log.info(f"🔄 TMDB-only fallback found {len(all_results)} results")
        return all_results[:50]
        
    except Exception as e:
        log.error(f"💥 TMDB-only fallback also failed: {e}")
        return []

def _remove_duplicates(results: list) -> list:
    """Remove duplicate results based on title + year"""
    seen = set()
    unique_results = []
    
    for result in results:
        key = f"{result['title'].lower()}_{result.get('release_year', 'unknown')}"
        if key not in seen:
            seen.add(key)
            unique_results.append(result)
    
    return unique_results

async def _show_movie_page(client, message: Message, user_id: int, page: int):
    """Show a page of movie selection (5 movies per page)"""
    try:
        session = user_sessions.get(user_id)
        if not session:
            await message.edit_text("❌ Session expired. Please start over.")
            return
        
        all_movies = session["all_movies"]
        total_pages = session["total_pages"]
        
        start_idx = page * 5
        end_idx = min(start_idx + 5, len(all_movies))
        current_movies = all_movies[start_idx:end_idx]
        
        keyboard = []
        for movie in current_movies:
            title = movie.get('title') or movie.get('name', 'Unknown')
            release_year = movie.get('release_year', 'N/A')
            source = movie.get('source', 'unknown')
            
            button_text = _create_compact_button_text(title, release_year, source)
            callback_data = f"select_movie:{movie['id']}:{message.id}:{movie['media_type']}:{source}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        pagination_buttons = []
        if total_pages > 1:
            if page > 0:
                pagination_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page:{page-1}:{message.id}"))
            
            pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
            
            if page < total_pages - 1:
                pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}:{message.id}"))
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{message.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        session["current_page"] = page
        
        clean_title = _remove_year_from_title(session["original_title"])
        await message.edit_text(
            f"🎬 <b>Multiple results found for:</b> {clean_title}\n"
            f"📄 <b>Page {page+1} of {total_pages}</b> - Showing {start_idx+1}-{end_idx} of {len(all_movies)} results\n\n"
            "Please select the correct movie or TV series:",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error showing movie page: {e}")
        await message.edit_text("❌ Error displaying selection.")

def _create_compact_button_text(title: str, year: str, source: str) -> str:
    """Create compact button text for inline keyboard"""
    try:
        # Clean the title - remove extra metadata that IMDB adds
        clean_title = _clean_imdb_title(title)
        
        # Get first 20 characters of clean title
        short_title = clean_title[:20] + "..." if len(clean_title) > 20 else clean_title
        
        # Source emoji - different for IMDB vs TMDB
        source_emoji = "🎭" if source == 'imdb' else "🎬"
        
        # Format: [Emoji] Title (Year)
        if year and year != 'Unknown' and year != 'N/A' and year.isdigit():
            return f"{source_emoji} {short_title} ({year})"
        else:
            return f"{source_emoji} {short_title}"
            
    except Exception as e:
        log.error(f"💥 Error creating compact button text: {e}")
        return title[:20]

def _clean_imdb_title(title: str) -> str:
    """Clean IMDB title by removing extra metadata"""
    try:
        # Remove common IMDB metadata patterns
        import re
        
        # Patterns to remove (runtime, ratings, etc.)
        patterns_to_remove = [
            r'\s*\d+h\s*\d+m',           # Runtime like "2h 18m"
            r'\s*R\d+',                  # Rating like "R62"
            r'\s*Metascore\s*\d+',       # Metascore
            r'\s*\d+\.\d+\s*\(\d+[KkM]?\)',  # Ratings like "7.2 (661K)"
            r'\s*Rate.*',                # "Rate Mark as watched"
            r'\s*Mark as watched',       # "Mark as watched"
            r'\s*Add to watchlist',      # "Add to watchlist"
        ]
        
        clean_title = title
        for pattern in patterns_to_remove:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        # Remove extra spaces and trim
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        return clean_title
        
    except Exception as e:
        log.error(f"💥 Error cleaning IMDB title: {e}")
        return title
    
async def handle_movie_selection_callback(client, callback_query):
    """Handle movie selection and pagination from inline keyboard"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        log.info(f"🔄 Callback received: {data} from user {user_id}")
        
        # Handle pagination buttons
        if data.startswith("page:"):
            await callback_query.answer("🔄 Loading...")
            _, page_num, original_msg_id = data.split(":")
            page_num = int(page_num)
            
            session = user_sessions.get(user_id)
            if not session:
                await callback_query.message.edit_text("❌ Session expired. Please start over.")
                return
            
            await _show_movie_page(client, callback_query.message, user_id, page_num)
            return
        
        # Handle cancel button
        elif data.startswith("cancel:"):
            await callback_query.answer("❌ Cancelled")
            _, original_msg_id = data.split(":")
            
            # Delete the selection message
            await callback_query.message.delete()
            
            # Clean up user session
            if user_id in user_sessions:
                del user_sessions[user_id]
            
            log.info(f"✅ Selection cancelled by user {user_id}")
            return
        
        # Handle no-op button (page indicator)
        elif data == "noop":
            await callback_query.answer()
            return
        
        # Handle movie selection
        elif data.startswith("select_movie:") or data.startswith("select_tv_series:"):
            if data.startswith("select_movie:"):
                _, movie_id, original_msg_id, media_type, source = data.split(":")
            else:
                _, movie_id, original_msg_id = data.split(":")
                media_type = "tv"
                source = "tmdb"
            
            await callback_query.answer("🔄 Processing your selection...")
            
            session = user_sessions.get(user_id)
            if not session:
                await callback_query.message.edit_text("❌ Session expired. Please start over.")
                return
            
            selected_movie = None
            for movie in session["all_movies"]:
                if str(movie["id"]) == str(movie_id) and movie.get('media_type') == media_type:
                    selected_movie = movie
                    break
            
            if not selected_movie:
                await callback_query.message.edit_text("❌ Selection not found in session.")
                return
            
            await callback_query.message.edit_text(
                f"🎬 <b>Selected:</b> {selected_movie.get('title', selected_movie.get('name', 'Unknown'))}\n\n🔄 Fetching details and generating poster...",
                parse_mode=enums.ParseMode.HTML
            )
            
            movie_data = await _get_media_details(source, movie_id, media_type)
            
            # VALIDATE MOVIE DATA BEFORE GENERATING POSTER
            if not movie_data:
                await callback_query.message.edit_text(
                    "❌ <b>Failed to get movie details</b>\n\n"
                    "The movie information could not be retrieved. Please try another selection.",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            # Check if we have essential data
            if not movie_data.get('title') or movie_data.get('title') == 'Unknown Title':
                await callback_query.message.edit_text(
                    "❌ <b>Incomplete movie information</b>\n\n"
                    "The movie details are incomplete. Please try another selection.",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            # Check if we have a valid poster
            if not movie_data.get('poster_url'):
                log.warning(f"⚠️ No poster URL for: {movie_data.get('title')}")
            
            # Generate poster
            poster_path = poster_generator.generate_poster(movie_data)
            
            # If poster generation failed, don't send
            if not poster_path:
                await callback_query.message.edit_text(
                    "❌ <b>Failed to generate poster</b>\n\n"
                    "Could not create the movie poster. Please try another selection.",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            caption = build_caption(movie_data)
            download_button = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)]])
            
            try:
                if POST_TO_CHANNEL:
                    await send_to_channel(client, poster_path, caption, download_button)
                    await callback_query.message.edit_text(
                        f"✅ <b>Poster generated and sent to channel!</b>\n\n🍿 <b>{movie_data['title']}</b> ({movie_data.get('release_year', 'N/A')})",
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    with open(poster_path, 'rb') as poster_file:
                        await client.send_photo(
                            chat_id=user_id,
                            photo=poster_file,
                            caption=caption,
                            reply_markup=download_button,
                            parse_mode=enums.ParseMode.HTML
                        )
                    
                    await callback_query.message.edit_text(
                        f"✅ <b>Poster generated successfully!</b>\n\n🍿 <b>{movie_data['title']}</b> ({movie_data.get('release_year', 'N/A')})",
                        parse_mode=enums.ParseMode.HTML
                    )
                
                poster_generator.cleanup_poster(poster_path)
                
            except Exception as e:
                poster_generator.cleanup_poster(poster_path)
                raise e
            
            if user_id in user_sessions:
                del user_sessions[user_id]
            
            mark_movie_processed(session["original_title"])
            
        else:
            log.warning(f"⚠️ Unknown callback data: {data}")
            await callback_query.answer("❌ Unknown action")
            
    except Exception as e:
        log.error(f"💥 Error in movie selection callback: {e}")
        await callback_query.message.edit_text("❌ Error processing your selection.")
        
async def _get_media_details(source: str, media_id: str, media_type: str) -> dict:
    """Get media details based on source"""
    try:
        if source == 'imdb':
            from utils.imdb_api import imdb_api
            return imdb_api.get_movie_details(media_id)
        elif source == 'tmdb':
            if media_type == 'tv':
                return tmdb_api.get_tv_series_details(int(media_id))
            else:
                return tmdb_api.get_movie_details(int(media_id))
        else:
            if media_type == 'tv':
                return tmdb_api.get_tv_series_details(int(media_id))
            else:
                return tmdb_api.get_movie_details(int(media_id))
    except Exception as e:
        log.error(f"💥 Error getting media details: {e}")
        return None

def _extract_year_from_title(title: str) -> int:
    """Extract year from movie title"""
    import re
    year_match = re.search(r'\b(19|20)\d{2}\b', title)
    return int(year_match.group()) if year_match else None

def _remove_year_from_title(title: str) -> str:
    """Remove year from movie title"""
    import re
    return re.sub(r'\s*(19|20)\d{2}\s*', ' ', title).strip()

async def _handle_series_request(client, message: Message, movie_title: str, series_info: dict):
    """Handle TV series request"""
    try:
        series_name = series_info.get('series_name', movie_title)
        season = series_info.get('season', 1)
        
        processing_msg = await message.reply_text(
            f"📺 <b>Processing TV Series:</b> {series_name}\nSeason: <b>{season}</b>\n\n🔄 Searching and generating poster...",
            parse_mode=enums.ParseMode.HTML
        )
        
        series_data = await _search_tv_series_with_imdb_primary(series_name)
        
        if not series_data or series_data.get('media_type') != 'tv':
            await processing_msg.edit_text(
                f"❌ <b>TV Series Not Found</b>\n\nCould not find: <b>{series_name}</b>\nPlease check the series name and try again.",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        poster_path = poster_generator.generate_poster(series_data)
        caption = _build_series_caption(series_data, season)
        download_button = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)]])
        
        try:
            if POST_TO_CHANNEL:
                await send_to_channel(client, poster_path, caption, download_button)
                await processing_msg.edit_text(
                    f"✅ <b>TV Series Poster Sent to Channel!</b>\n\n📺 <b>{series_data['title']}</b> - Season {season}",
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                with open(poster_path, 'rb') as poster_file:
                    await client.send_photo(
                        chat_id=message.from_user.id,
                        photo=poster_file,
                        caption=caption,
                        reply_markup=download_button,
                        parse_mode=enums.ParseMode.HTML
                    )
                
                await processing_msg.edit_text(
                    f"✅ <b>TV Series Poster Generated!</b>\n\n📺 <b>{series_data['title']}</b> - Season {season}",
                    parse_mode=enums.ParseMode.HTML
                )
            
            poster_generator.cleanup_poster(poster_path)
            
        except Exception as e:
            poster_generator.cleanup_poster(poster_path)
            raise e
        
        mark_series_processed(series_name, season)
        mark_movie_processed(movie_title)
        
    except Exception as e:
        log.error(f"💥 Error processing TV series: {e}")
        await message.reply_text("❌ Error processing TV series request.")

async def _search_tv_series_with_imdb_primary(series_name: str):
    """Search TV series with IMDB primary"""
    try:
        if USE_IMDB_FALLBACK:
            from utils.imdb_api import imdb_api
            imdb_data = imdb_api.get_movie_by_title(series_name)
            if imdb_data and imdb_data.get('media_type') == 'tv':
                log.info(f"✅ Found TV series via IMDB: {imdb_data['title']}")
                return imdb_data
        
        log.info(f"🔄 IMDB failed, trying TMDB for TV series: {series_name}")
        return tmdb_api.get_media_by_title(series_name)
        
    except Exception as e:
        log.error(f"💥 Error searching TV series: {e}")
        return None

def _build_series_caption(series_data: dict, season: int):
    """Build caption for TV series (generic season caption)"""
    try:
        title = series_data['title']
        rating = series_data.get('tmdb_rating', 0)
        genres = series_data.get('genres', [])
        
        caption_parts = [
            f"🍿 {title} - Season {season}",
            ""
        ]
        
        if genres:
            genre_hashtags = " ".join([f"🎭 #{genre.replace(' ', '')}" for genre in genres[:3]])
            caption_parts.append(f"✲ Genre: {genre_hashtags}")
        
        if rating > 0:
            caption_parts.append(f"≛ IMDb : {rating} / 10")
        
        caption_parts.append(f"📺 TV Series • Complete Season {season}")
        
        overview = series_data.get('overview', '')
        if overview:
            caption_parts.extend(["", "💬 Storyline:", overview[:200] + "..." if len(overview) > 200 else overview])
        
        caption_parts.extend(["", "▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬", "              •@Movieshub_101•"])
        
        return "\n".join(caption_parts)
        
    except Exception as e:
        log.error(f"💥 Error building series caption: {e}")
        return f"🍿 {series_data.get('title', 'TV Series')} - Season {season}\n\n▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬\n              •@Movieshub_101•"
