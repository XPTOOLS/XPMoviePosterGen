from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from core.logger import log
from utils.file_detector import extract_movie_title, extract_season_series_info
from utils.tmdb_api import tmdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption, build_compact_caption
from utils.channel_poster import send_to_channel
from database.movie_data import log_movie_request, mark_movie_processed
from config import POST_TO_CHANNEL, DOWNLOAD_BOT_LINK

# Store user sessions temporarily
user_sessions = {}

async def handle_private_message(client, message: Message):
    """Handle private messages sent directly to the bot"""
    try:
        log.info(f"👤 Private message from {message.from_user.id} - {message.from_user.first_name}")
        
        # Extract movie title from message
        movie_title = await extract_movie_title(message)
        
        if movie_title:
            log.success(f"🎯 Detected movie title: {movie_title}")
            
            # Log the request
            file_size = message.document.file_size if message.document else message.video.file_size if message.video else None
            log_movie_request(movie_title, file_size, message.from_user.id)
            
            # Check if it's a series
            series_info = extract_season_series_info(movie_title)
            if series_info and series_info['is_series']:
                await _handle_series_request(client, message, movie_title, series_info)
            else:
                await _handle_movie_selection(client, message, movie_title)
            
        else:
            await message.reply_text(
                "❌ I couldn't detect a movie title in your message.\n\n"
                "Please send:\n"
                "• Movie name as text\n"
                "• Movie file with title in filename\n"
                "• Poster image with movie name in caption",
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        log.error(f"💥 Error in private message handler: {e}")
        await message.reply_text("❌ An error occurred while processing your request.")

async def _handle_movie_selection(client, message: Message, movie_title: str):
    """Show multiple movie options for user to choose from with pagination"""
    try:
        processing_msg = await message.reply_text(
            f"🎬 <b>Searching for:</b> {movie_title}\n\n"
            "🔍 Searching TMDB...",
            parse_mode=enums.ParseMode.HTML
        )
        
        # Extract year from title if present
        year = _extract_year_from_title(movie_title)
        clean_title = _remove_year_from_title(movie_title)
        
        # Check if it might be a TV series
        series_info = extract_season_series_info(movie_title)
        if series_info and series_info['is_series']:
            # Search for TV series with OMDb fallback
            series_data = tmdb_api.get_tv_series_by_title_with_fallback(series_info['series_name'])
            if series_data:
                # Show TV series option
                keyboard = [
                    [InlineKeyboardButton(f"📺 {series_data['title']} (TV Series) ⭐ {series_data.get('tmdb_rating', 'N/A')}", 
                                        callback_data=f"select_tv_series:{series_data['movie_id']}:{message.id}")],
                    [InlineKeyboardButton("🔍 Search as Movie Instead", callback_data=f"search_movie:{clean_title}:{message.id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{message.id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(
                    f"🎬 <b>TV Series Detected:</b> {clean_title}\n\n"
                    "Found a TV series match. Would you like to proceed with this?",
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return
        
        # Search for multiple movies (get 10 results for pagination)
        all_movies = tmdb_api.search_multiple_movies(clean_title, year, limit=10)
        
        # If no TMDB results, try OMDb fallback
        if not all_movies:
            log.info(f"🔄 TMDB failed, trying OMDb fallback for: {clean_title}")
            from utils.omdb_api import omdb_api
            omdb_movie = omdb_api.search_movie(clean_title, year)
            if omdb_movie:
                # Convert OMDb result to our movie format
                all_movies = [{
                    'id': omdb_movie['movie_id'],
                    'title': omdb_movie['title'],
                    'release_year': omdb_movie.get('release_year', 'Unknown'),
                    'vote_average': omdb_movie.get('tmdb_rating', 0),
                    'vote_count': omdb_movie.get('vote_count', 0),
                    'display_title': f"{omdb_movie['title']} ({omdb_movie.get('release_year', 'Unknown')})"
                }]
                log.info(f"✅ OMDb found movie: {omdb_movie['title']}")
        
        if not all_movies:
            await processing_msg.edit_text(
                f"❌ <b>No movies found for:</b> {clean_title}\n\n"
                "Try:\n"
                "• Check spelling\n"
                "• Use English title\n"
                "• Be more specific",
                parse_mode=enums.ParseMode.HTML
            )
            return
        
        # Store all movies in user session for pagination
        user_sessions[message.from_user.id] = {
            "all_movies": all_movies,
            "current_page": 0,
            "original_title": movie_title,
            "processing_msg_id": processing_msg.id,
            "total_pages": (len(all_movies) + 4) // 5  # 5 movies per page
        }
        
        # Show first page
        await _show_movie_page(client, processing_msg, message.from_user.id, 0)
        
    except Exception as e:
        log.error(f"💥 Error in movie selection: {e}")
        await message.reply_text(f"❌ Error: {str(e)}", parse_mode=enums.ParseMode.HTML)

async def _show_movie_page(client, message: Message, user_id: int, page: int):
    """Show a page of movie selection (5 movies per page)"""
    try:
        session = user_sessions.get(user_id)
        if not session:
            await message.edit_text("❌ Session expired. Please start over.")
            return
        
        all_movies = session["all_movies"]
        total_pages = session["total_pages"]
        
        # Calculate start and end indices for current page
        start_idx = page * 5
        end_idx = min(start_idx + 5, len(all_movies))
        current_movies = all_movies[start_idx:end_idx]
        
        # Create inline keyboard with movie options (5 per page)
        keyboard = []
        for movie in current_movies:
            # Truncate long titles
            display_title = movie['title']
            if len(display_title) > 25:
                display_title = display_title[:22] + "..."
            
            button_text = f"🎬 {display_title} ({movie.get('release_year', 'N/A')}) ⭐ {movie.get('vote_average', 'N/A')}"
            callback_data = f"select_movie:{movie['id']}:{message.id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Add pagination buttons if needed
        pagination_buttons = []
        if total_pages > 1:
            if page > 0:
                pagination_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page:{page-1}:{message.id}"))
            
            # Show current page info
            pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
            
            if page < total_pages - 1:
                pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}:{message.id}"))
            
            if pagination_buttons:
                keyboard.append(pagination_buttons)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{message.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update session with current page
        session["current_page"] = page
        
        # Update message with current page
        clean_title = _remove_year_from_title(session["original_title"])
        await message.edit_text(
            f"🎬 <b>Multiple movies found for:</b> {clean_title}\n"
            f"📄 <b>Page {page+1} of {total_pages}</b> - Showing {start_idx+1}-{end_idx} of {len(all_movies)} results\n\n"
            "Please select the correct movie:",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error showing movie page: {e}")
        await message.edit_text("❌ Error displaying movie selection.")

async def handle_movie_selection_callback(client, callback_query):
    """Handle movie selection and pagination from inline keyboard"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if data.startswith("cancel:"):
            await callback_query.message.edit_text("❌ Request cancelled.")
            await callback_query.answer()
            return
        
        if data.startswith("page:"):
            # Handle pagination
            _, page_num, original_msg_id = data.split(":")
            page_num = int(page_num)
            
            await callback_query.answer(f"📄 Switching to page {page_num + 1}")
            await _show_movie_page(client, callback_query.message, user_id, page_num)
            return
        
        if data == "noop":
            # No operation for page indicator button
            await callback_query.answer()
            return
        
        if data.startswith("select_movie:"):
            _, movie_id, original_msg_id = data.split(":")
            movie_id = int(movie_id)
            
            await callback_query.answer("🔄 Processing your selection...")
            
            # Get stored movies from user session
            session = user_sessions.get(user_id)
            if not session:
                await callback_query.message.edit_text("❌ Session expired. Please start over.")
                return
            
            # Find the selected movie from all movies
            selected_movie = None
            for movie in session["all_movies"]:
                if movie["id"] == movie_id:
                    selected_movie = movie
                    break
            
            if not selected_movie:
                await callback_query.message.edit_text("❌ Movie not found in session.")
                return
            
            # Update message to show processing
            await callback_query.message.edit_text(
                f"🎬 <b>Selected:</b> {selected_movie['display_title']}\n\n"
                "🔄 Fetching details and generating poster...",
                parse_mode=enums.ParseMode.HTML
            )
            
            # Get full movie details
            movie_data = tmdb_api.get_movie_details(movie_id)
            
            if not movie_data:
                await callback_query.message.edit_text(
                    f"❌ Failed to get details for: {selected_movie['title']}",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            
            # Generate poster
            poster_path = poster_generator.generate_poster(movie_data)
            
            # Build stylish caption
            caption = build_caption(movie_data)
            
            # Create download button
            download_button = InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 Download", url=DOWNLOAD_BOT_LINK)
            ]])
            
            # Send the poster based on configuration
            try:
                if POST_TO_CHANNEL:
                    # Send to channel
                    await send_to_channel(client, poster_path, caption, download_button)
                    await callback_query.message.edit_text(
                        f"✅ <b>Poster generated and sent to channel!</b>\n\n"
                        f"🍿 <b>{movie_data['title']}</b> ({movie_data.get('release_year', 'N/A')})",
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    # Send directly to user
                    with open(poster_path, 'rb') as poster_file:
                        await client.send_photo(
                            chat_id=user_id,
                            photo=poster_file,
                            caption=caption,
                            reply_markup=download_button,
                            parse_mode=enums.ParseMode.HTML
                        )
                    
                    await callback_query.message.edit_text(
                        f"✅ <b>Poster generated successfully!</b>\n\n"
                        f"🍿 <b>{movie_data['title']}</b> ({movie_data.get('release_year', 'N/A')})",
                        parse_mode=enums.ParseMode.HTML
                    )
                
                # Clean up poster file after sending
                poster_generator.cleanup_poster(poster_path)
                
            except Exception as e:
                # Clean up poster file even if sending fails
                poster_generator.cleanup_poster(poster_path)
                raise e
            
            # Clean up session
            if user_id in user_sessions:
                del user_sessions[user_id]
            
            mark_movie_processed(session["original_title"])
            
    except Exception as e:
        log.error(f"💥 Error in movie selection callback: {e}")
        await callback_query.message.edit_text("❌ Error processing your selection.")

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
    series_name = series_info.get('series_name', movie_title)
    season = series_info.get('season', 1)
    episode = series_info.get('episode')
    
    if episode:
        await message.reply_text(
            f"📺 Series detected: <b>{series_name}</b>\n"
            f"Season {season}, Episode {episode}\n\n"
            "🔄 TV series support coming soon!",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            f"📺 Series detected: <b>{series_name}</b>\n"
            f"Season {season}\n\n"
            "🔄 TV series support coming soon!",
            parse_mode=enums.ParseMode.HTML
        )