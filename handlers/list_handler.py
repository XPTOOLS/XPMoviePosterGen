from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from pyrogram import enums
from datetime import datetime, timedelta
from database.movie_data import get_recent_movies, get_all_movies, get_list_message_ids, save_list_message_ids, delete_list_message_ids
from config import DOWNLOAD_BOT_LINK, LIST_CHANNEL_ID, QUALITY_PATTERNS, EPISODE_PATTERNS, SERIES_FIXES, COMMON_INDICATORS_PATTERN
from core.logger import log

# Store message IDs for editing (in-memory cache)
list_message_ids_cache = {}

async def list_command(client: Client, message: Message):
    """Handle /list command to show recent movies organized by alphabet"""
    try:
        log.info(f"📋 /list command received from user {message.from_user.id} (@{message.from_user.username})")
        
        # Load existing message IDs from database
        global list_message_ids_cache
        list_message_ids_cache = get_list_message_ids() or {}
        log.debug(f"📝 Loaded {len(list_message_ids_cache)} existing list message IDs from database")
        
        # Get movies from last 24 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        log.debug(f"🕐 Fetching movies from {start_time} to {end_time}")
        recent_movies = get_recent_movies(start_time, end_time)
        
        log.info(f"📊 Found {len(recent_movies)} movies in the last 24 hours")
        
        if not recent_movies:
            await message.reply_text(
                "❌ <b>No movies found in the last 24 hours!</b>\n\n"
                "There are no recently processed movies to display.",
                parse_mode=enums.ParseMode.HTML
            )
            log.warning(f"⚠️ No movies found for user {message.from_user.id} in last 24h")
            return
        
        # Remove duplicates - only keep unique movie titles
        unique_movies = _remove_duplicate_movies(recent_movies)
        log.info(f"🔍 After removing duplicates: {len(unique_movies)} unique movies")
        
        # Organize movies by starting letter
        organized_movies = _organize_movies_by_alphabet(unique_movies)
        log.debug(f"🔤 Organized movies into {len(organized_movies)} alphabetical groups")
        
        # Create alphabet buttons - ALWAYS show all letters A-Z plus numbers
        alphabet_buttons = _create_alphabet_buttons(organized_movies)
        
        # Send summary with alphabet selection
        summary_message = (
            f"📋 <b>Movie List Summary - Last 24 Hours</b>\n\n"
            f"📊 <b>Total Movies Found:</b> {len(recent_movies)}\n"
            f"🎯 <b>Unique Movies:</b> {len(unique_movies)}\n"
            f"🔤 <b>Alphabetical Sections:</b> {len(organized_movies)}\n"
            f"🕐 <b>Time Period:</b> Last 24 hours\n\n"
            f"<b>Select which lists to send:</b>"
        )
        
        await message.reply_text(
            summary_message,
            reply_markup=alphabet_buttons,
            parse_mode=enums.ParseMode.HTML
        )
        
        log.success(f"✅ Alphabet selection sent with {len(unique_movies)} unique movies for user {message.from_user.id}")
        
    except Exception as e:
        log.error(f"💥 Error in /list command: {e}")
        await message.reply_text("❌ An error occurred while generating the list.")

def _create_alphabet_buttons(organized_movies):
    """Create inline keyboard with alphabet buttons - ALWAYS show A-Z plus numbers"""
    try:
        buttons = []
        row = []
        
        # Always include all letters A-Z plus numbers/symbols
        all_possible_letters = [chr(i) for i in range(65, 91)]  # A-Z
        all_possible_letters.append("#")  # For numbers/special chars
        
        for letter in all_possible_letters:
            # Show button for letters that have movies OR are in organized_movies
            has_movies = letter in organized_movies and len(organized_movies[letter]) > 0
            button_text = f"📋 {letter}" if has_movies else f"○ {letter}"
            # ALWAYS allow clicking, even if no movies - user might want to check
            callback_data = f"send_letter:{letter}"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            if len(row) == 6:  # 6 buttons per row for better layout
                buttons.append(row)
                row = []
        
        # Add remaining buttons if any
        if row:
            buttons.append(row)
        
        # Add "Send All" and "Cancel" buttons
        buttons.extend([
            [InlineKeyboardButton("🚀 Send All Lists", callback_data="send_all_letters")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_list")]
        ])
        
        return InlineKeyboardMarkup(buttons)
        
    except Exception as e:
        log.error(f"💥 Error creating alphabet buttons: {e}")
        # Even error button should do something
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Error - Click to Refresh", callback_data="back_to_lists")]
        ])

def _remove_duplicate_movies(movies):
    """Remove duplicate movies and group TV series episodes"""
    try:
        seen_titles = set()
        unique_movies = []
        
        for movie in movies:
            title = movie.get('movie_title', '').strip().lower()
            if not title:
                continue
                
            # Clean the title for better deduplication
            clean_title = _clean_movie_title(title)
            
            # Extract series base name (remove episode info)
            series_base_name = _extract_series_base_name(clean_title)
            
            # Use series base name for deduplication if it's a series
            dedup_key = series_base_name if series_base_name != clean_title else clean_title
            
            if dedup_key not in seen_titles:
                seen_titles.add(dedup_key)
                # Store the cleaned title for display
                movie['display_title'] = series_base_name.title() if series_base_name != clean_title else clean_title.title()
                unique_movies.append(movie)
        
        log.info(f"🔄 Deduplication: {len(movies)} → {len(unique_movies)} unique titles/series")
        return unique_movies
        
    except Exception as e:
        log.error(f"💥 Error removing duplicates: {e}")
        return movies

def _extract_series_base_name(title):
    """Extract base series name by removing episode information"""
    try:
        import re
        
        clean_title = title.lower()
        
        # Remove common indicators using config pattern
        clean_title = re.sub(COMMON_INDICATORS_PATTERN, '', clean_title, flags=re.IGNORECASE)
        
        # Remove quality patterns from config
        for pattern in QUALITY_PATTERNS:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        # Apply episode patterns from config
        original_title = clean_title
        for pattern in EPISODE_PATTERNS:
            clean_title = re.sub(pattern, '', clean_title)
        
        # Remove trailing separators and clean up
        clean_title = re.sub(r'[\.\-\_\s]+$', '', clean_title)
        clean_title = clean_title.strip()
        
        # If the title got too short (less than 3 characters), use original
        if len(clean_title) < 3:
            clean_title = original_title
        
        # Apply series fixes from config
        if clean_title in SERIES_FIXES:
            clean_title = SERIES_FIXES[clean_title]
        
        # If we removed something, return the cleaned version
        if clean_title and clean_title != original_title:
            log.debug(f"📺 Extracted series base: '{title}' → '{clean_title}'")
            return clean_title
        
        return original_title
        
    except Exception as e:
        log.error(f"💥 Error extracting series base name: {e}")
        return title

def _clean_movie_title(title):
    """Clean movie title for better deduplication"""
    try:
        import re
        
        clean_title = title.lower().strip()
        
        # Remove common indicators using config pattern (most comprehensive)
        clean_title = re.sub(COMMON_INDICATORS_PATTERN, '', clean_title, flags=re.IGNORECASE)
        
        # Remove quality patterns from config
        for pattern in QUALITY_PATTERNS:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        # Remove extra spaces and special characters
        clean_title = re.sub(r'[^\w\s]', ' ', clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # Extract year if present (for better grouping)
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_title)
        if year_match:
            year = year_match.group()
            clean_title = re.sub(r'\s*\b(19|20)\d{2}\b', '', clean_title).strip()
            clean_title = f"{clean_title} {year}"
        
        return clean_title.strip()
        
    except Exception as e:
        log.error(f"💥 Error cleaning movie title: {e}")
        return title.lower().strip()

def _organize_movies_by_alphabet(movies):
    """Organize movies by their starting letter - properly handle numbers and special chars"""
    try:
        organized = {}
        
        for movie in movies:
            # Use display_title if available, otherwise use original title
            title = movie.get('display_title') or movie.get('movie_title', '').strip()
            if not title:
                continue
                
            # Convert to title case for display
            display_title = title.title()
            if not display_title:  # Skip empty titles
                continue
                
            first_char = display_title[0].upper()
            
            # Handle special characters and numbers
            if not first_char.isalpha():
                first_char = "#"  # Group numbers and special chars together
            
            if first_char not in organized:
                organized[first_char] = []
            
            # Only add if not already in the list (case insensitive)
            if display_title.lower() not in [m.lower() for m in organized[first_char]]:
                organized[first_char].append(display_title)
        
        # Sort the letters and movies within each letter
        for letter in organized:
            organized[letter].sort(key=lambda x: x.lower())
        
        # Ensure we always have entries for all letters A-Z and #, even if empty
        all_letters = [chr(i) for i in range(65, 91)]  # A-Z
        all_letters.append("#")  # For numbers/special chars
        
        for letter in all_letters:
            if letter not in organized:
                organized[letter] = []
        
        log.debug(f"📝 Organized {len(movies)} movies into {len(organized)} alphabetical sections")
        return dict(sorted(organized.items()))
        
    except Exception as e:
        log.error(f"💥 Error organizing movies by alphabet: {e}")
        return {}

def _split_movies_into_chunks(movies, chunk_size=30):
    """Split a list of movies into smaller chunks"""
    chunks = []
    for i in range(0, len(movies), chunk_size):
        chunks.append(movies[i:i + chunk_size])
    return chunks

def _generate_letter_chunk_message(letter, chunk_movies, chunk_num, total_chunks):
    """Generate message for a chunk of movies from a letter"""
    try:
        message_parts = []
        
        if chunk_num == 1:
            message_parts.append(f"🅰️ <b>{letter} LIST - COPY & SEARCH IN BOT:</b>")
        else:
            message_parts.append(f"🅰️ <b>{letter} LIST (Part {chunk_num}) - COPY & SEARCH IN BOT:</b>")
        
        message_parts.append("")
        message_parts.append(f"🤖 <b>Movie Bot:</b>")
        message_parts.append(f"@Moviessearchfilterbot")
        message_parts.append("")
        
        for movie in chunk_movies:
            # Truncate long movie names
            display_name = movie[:50] + "..." if len(movie) > 50 else movie
            message_parts.append(f"<code>▶️{display_name}</code>")
        
        message_parts.append("")
        if total_chunks > 1:
            message_parts.append(f"📅 <i>{letter} List • Part {chunk_num} of {total_chunks} • {len(chunk_movies)} items</i>")
        else:
            message_parts.append(f"📅 <i>{letter} List • {len(chunk_movies)} items</i>")
        
        final_message = "\n".join(message_parts)
        log.debug(f"📄 Generated {letter} list chunk {chunk_num}/{total_chunks} with {len(chunk_movies)} movies, {len(final_message)} characters")
        return final_message
        
    except Exception as e:
        log.error(f"💥 Error generating {letter} list chunk: {e}")
        return f"❌ Error generating {letter} list."

async def _send_or_edit_list_message(client, chat_id, letter, movies, is_channel=True, force_new=False):
    """Send new list or edit existing one with improved logic - FIXED to handle new content"""
    try:
        # Split movies into chunks
        movie_chunks = _split_movies_into_chunks(movies, chunk_size=30)
        total_chunks = len(movie_chunks)
        
        message_ids = []
        
        for chunk_num, chunk_movies in enumerate(movie_chunks, 1):
            # Skip empty chunks
            if not chunk_movies:
                continue
                
            list_message = _generate_letter_chunk_message(letter, chunk_movies, chunk_num, total_chunks)
            
            # Add download button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Click to Download", url=DOWNLOAD_BOT_LINK)]
            ])
            
            # Check if we have existing message ID for this letter chunk
            message_key = f"{letter}_{chunk_num}"
            existing_message_id = list_message_ids_cache.get(message_key)
            
            # For "Last 24 Hours" mode, we should CREATE NEW messages if:
            # 1. We have more chunks than before (new content)
            # 2. No existing message for this chunk
            # 3. Editing fails
            should_edit = (existing_message_id and is_channel and not force_new and chunk_num <= len([k for k in list_message_ids_cache.keys() if k.startswith(f"{letter}_")]))
            
            if should_edit:
                # Try to edit existing message
                try:
                    await client.edit_message_text(
                        chat_id=chat_id,
                        message_id=existing_message_id,
                        text=list_message,
                        reply_markup=keyboard,
                        parse_mode=enums.ParseMode.HTML
                    )
                    message_ids.append(existing_message_id)
                    log.info(f"✏️ Edited existing {letter} list chunk {chunk_num} (Message ID: {existing_message_id})")
                except Exception as e:
                    log.warning(f"⚠️ Could not edit {letter} list chunk {chunk_num}, sending new: {e}")
                    # Send new message if edit fails
                    message = await client.send_message(
                        chat_id=chat_id,
                        text=list_message,
                        reply_markup=keyboard,
                        parse_mode=enums.ParseMode.HTML
                    )
                    message_ids.append(message.id)
                    list_message_ids_cache[message_key] = message.id
                    # Save to database
                    save_list_message_ids(list_message_ids_cache)
            else:
                # Send new message (for new chunks or when force_new is True)
                message = await client.send_message(
                    chat_id=chat_id,
                    text=list_message,
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
                message_ids.append(message.id)
                if is_channel:
                    list_message_ids_cache[message_key] = message.id
                    # Save to database
                    save_list_message_ids(list_message_ids_cache)
                    log.info(f"💾 Stored new message ID for {letter} chunk {chunk_num}: {message.id}")
        
        return message_ids
        
    except Exception as e:
        log.error(f"💥 Error sending/editing list message: {e}")
        return []

async def _delete_existing_list_messages(client, letter):
    """Delete existing list messages for a letter from channel"""
    try:
        deleted_count = 0
        keys_to_delete = []
        
        for message_key, message_id in list_message_ids_cache.items():
            if message_key.startswith(f"{letter}_"):
                try:
                    await client.delete_messages(LIST_CHANNEL_ID, message_id)
                    keys_to_delete.append(message_key)
                    deleted_count += 1
                    log.info(f"🗑️ Deleted {letter} list message {message_id}")
                except Exception as e:
                    log.warning(f"⚠️ Could not delete message {message_id}: {e}")
        
        # Remove from cache
        for key in keys_to_delete:
            del list_message_ids_cache[key]
        
        # Save updated cache to database
        save_list_message_ids(list_message_ids_cache)
        
        log.info(f"✅ Deleted {deleted_count} existing {letter} list messages")
        return deleted_count
        
    except Exception as e:
        log.error(f"💥 Error deleting existing list messages: {e}")
        return 0

async def _process_list_sending(client, callback_query, letter=None, target="channel", time_period="24h"):
    """Process list sending for single letter or all letters"""
    try:
        user_id = callback_query.from_user.id
        is_channel = target == "channel"
        chat_id = LIST_CHANNEL_ID if is_channel else user_id
        chat_name = "channel" if is_channel else "bot"
        
        await callback_query.answer(f"🔄 Sending to {chat_name}...")
        
        # Use global cache
        global list_message_ids_cache
        
        # Get movies based on time period
        if time_period == "all_time":
            # Get ALL movies from database
            all_movies = get_all_movies()
            log.info(f"📊 Found {len(all_movies)} total movies in database")
            movies_to_process = all_movies
            time_description = "All Time"
        else:
            # For "Last 24 Hours", we need to combine existing content with new content
            # First get all movies to maintain the existing list
            all_movies = get_all_movies()
            log.info(f"📊 Found {len(all_movies)} total movies in database")
            
            # Then get only the new movies from last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            recent_movies = get_recent_movies(start_time, end_time)
            log.info(f"📊 Found {len(recent_movies)} new movies in the last 24 hours")
            
            # Use ALL movies but mark which ones are new for processing
            movies_to_process = all_movies
            time_description = "Last 24 Hours (Updated)"
            
            log.info(f"🔄 Using {len(movies_to_process)} total movies with {len(recent_movies)} new additions")
        
        if not movies_to_process:
            await callback_query.message.edit_text("❌ No movies found to send.")
            return
        
        # Remove duplicates and organize
        unique_movies = _remove_duplicate_movies(movies_to_process)
        organized_movies = _organize_movies_by_alphabet(unique_movies)
        
        total_messages_sent = 0
        total_messages_edited = 0
        total_messages_new = 0
        
        if letter:  # Single letter
            if letter in organized_movies and organized_movies[letter]:
                # For "Last 24 Hours", we should edit existing messages to add new content
                # For "All Time", we delete and recreate
                force_new = (time_period == "all_time" and is_channel)
                
                if force_new:
                    deleted_count = await _delete_existing_list_messages(client, letter)
                    log.info(f"🗑️ Deleted {deleted_count} existing {letter} list messages for all-time update")
                
                message_ids = await _send_or_edit_list_message(
                    client, chat_id, letter, organized_movies[letter], is_channel, force_new
                )
                total_messages_sent = len(message_ids)
                
                # Count edited vs new messages
                if not force_new:
                    # Count how many of the current messages were edits of existing ones
                    existing_chunks = len([k for k in list_message_ids_cache.keys() if k.startswith(f"{letter}_")])
                    total_messages_edited = min(total_messages_sent, existing_chunks)
                    total_messages_new = total_messages_sent - total_messages_edited
                else:
                    total_messages_new = total_messages_sent
                
                await callback_query.message.edit_text(
                    f"✅ <b>{letter} List successfully processed!</b>\n\n"
                    f"📊 <b>Movies in {letter} list:</b> {len(organized_movies[letter])}\n"
                    f"📤 <b>Total messages:</b> {total_messages_sent}\n"
                    f"✏️ <b>Messages edited:</b> {total_messages_edited}\n"
                    f"🆕 <b>Messages sent:</b> {total_messages_new}\n"
                    f"📅 <b>Time period:</b> {time_description}\n"
                    f"📍 <b>Target:</b> {chat_name}",
                    parse_mode=enums.ParseMode.HTML
                )
                log.success(f"✅ {letter} list sent to {chat_name}: {total_messages_edited} edited, {total_messages_new} new by user {user_id}")
            else:
                await callback_query.answer(f"❌ No movies found for {letter} list", show_alert=True)
        
        else:  # All letters
            # For "Last 24 Hours", we should edit existing messages to add new content
            # For "All Time", we delete and recreate
            force_new = (time_period == "all_time" and is_channel)
            if force_new:
                # Delete all existing list messages
                delete_list_message_ids()
                list_message_ids_cache = {}
                log.info("🗑️ Deleted ALL existing list messages for all-time update")
            
            # Process only letters that have movies
            processed_letters = 0
            for letter, movies in organized_movies.items():
                if movies:  # Only process letters that have movies
                    message_ids = await _send_or_edit_list_message(
                        client, chat_id, letter, movies, is_channel, force_new
                    )
                    total_messages_sent += len(message_ids)
                    processed_letters += 1
                    log.debug(f"✅ Processed {letter} list with {len(message_ids)} messages")
            
            # Count totals
            if not force_new:
                total_messages_edited = len([k for k in list_message_ids_cache.keys() if any(k.startswith(f"{l}_") for l in organized_movies.keys() if organized_movies[l])])
                total_messages_new = total_messages_sent - total_messages_edited
            else:
                total_messages_new = total_messages_sent
                total_messages_edited = 0
            
            await callback_query.message.edit_text(
                f"✅ <b>All lists successfully processed!</b>\n\n"
                f"📊 <b>Total unique movies:</b> {len(unique_movies)}\n"
                f"🔤 <b>Alphabet sections processed:</b> {processed_letters}\n"
                f"📤 <b>Total messages:</b> {total_messages_sent}\n"
                f"✏️ <b>Messages edited:</b> {total_messages_edited}\n"
                f"🆕 <b>Messages sent:</b> {total_messages_new}\n"
                f"📅 <b>Time period:</b> {time_description}\n"
                f"📍 <b>Target:</b> {chat_name}",
                parse_mode=enums.ParseMode.HTML
            )
            log.success(f"✅ All lists sent to {chat_name}: {total_messages_edited} edited, {total_messages_new} new by user {user_id}")
        
    except Exception as e:
        log.error(f"💥 Error processing list sending: {e}")
        await callback_query.message.edit_text("❌ Failed to send lists.")

async def _handle_single_letter(client, callback_query):
    """Handle sending/editing a single letter list"""
    try:
        letter = callback_query.data.split(":")[1]
        await callback_query.answer(f"🔄 Processing {letter} list...")
        log.info(f"📋 Processing {letter} list for user {callback_query.from_user.id}")
        
        # Get movies from both time periods to show accurate counts
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        # Get recent movies (24h)
        recent_movies = get_recent_movies(start_time, end_time)
        recent_unique_movies = _remove_duplicate_movies(recent_movies)
        recent_organized_movies = _organize_movies_by_alphabet(recent_unique_movies)
        
        # Get all movies (all time)
        all_movies = get_all_movies()
        all_unique_movies = _remove_duplicate_movies(all_movies)
        all_organized_movies = _organize_movies_by_alphabet(all_unique_movies)
        
        # Count movies for this letter in both time periods
        recent_count = len(recent_organized_movies.get(letter, []))
        all_time_count = len(all_organized_movies.get(letter, []))
        
        # Always allow sending, even if no recent movies
        # Create time period selection for single letter
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🕐 Last 24h ({recent_count})", callback_data=f"time_select:{letter}:24h"),
                InlineKeyboardButton(f"📅 All Time ({all_time_count})", callback_data=f"time_select:{letter}:all_time")
            ],
            [
                InlineKeyboardButton("🔙 Back to All Lists", callback_data="back_to_lists")
            ]
        ])
        
        # Create appropriate message based on available movies
        if recent_count > 0 and all_time_count > 0:
            message_text = (
                f"📋 <b>{letter} List Options</b>\n\n"
                f"📊 <b>Available Movies:</b>\n"
                f"• 🕐 Last 24 Hours: {recent_count} movies\n"
                f"• 📅 All Time: {all_time_count} movies\n\n"
                f"<i>Select which time period to send:</i>\n"
                f"• <b>Last 24 Hours:</b> Continue where we left off (edit existing)\n"
                f"• <b>All Time:</b> Send complete list (delete & recreate)"
            )
        elif recent_count == 0 and all_time_count > 0:
            message_text = (
                f"📋 <b>{letter} List Options</b>\n\n"
                f"📊 <b>Available Movies:</b>\n"
                f"• 🕐 Last 24 Hours: No new movies\n"
                f"• 📅 All Time: {all_time_count} movies\n\n"
                f"<i>Select which time period to send:</i>\n"
                f"• <b>Last 24 Hours:</b> No new movies to add\n"
                f"• <b>All Time:</b> Send complete list (delete & recreate existing)"
            )
        elif recent_count > 0 and all_time_count == 0:
            message_text = (
                f"📋 <b>{letter} List Options</b>\n\n"
                f"📊 <b>Available Movies:</b>\n"
                f"• 🕐 Last 24 Hours: {recent_count} movies\n"
                f"• 📅 All Time: No movies found\n\n"
                f"<i>Select which time period to send:</i>\n"
                f"• <b>Last 24 Hours:</b> Continue where we left off (edit existing)\n"
                f"• <b>All Time:</b> No movies available"
            )
        else:
            message_text = (
                f"📋 <b>{letter} List</b>\n\n"
                f"❌ <b>No movies found for '{letter}' in any time period.</b>\n\n"
                f"<i>This letter currently has no movies in the database.</i>"
            )
            # If no movies at all, only show back button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to All Lists", callback_data="back_to_lists")]
            ])
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error handling single letter: {e}")
        await callback_query.answer("❌ Error processing letter", show_alert=True)

async def _handle_all_letters(client, callback_query):
    """Handle sending all letters"""
    try:
        await callback_query.answer("🔄 Preparing all lists...")
        
        # Get counts for both time periods
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        # Get recent movies (24h)
        recent_movies = get_recent_movies(start_time, end_time)
        recent_unique_movies = _remove_duplicate_movies(recent_movies)
        recent_organized_movies = _organize_movies_by_alphabet(recent_unique_movies)
        
        # Get all movies (all time)
        all_movies = get_all_movies()
        all_unique_movies = _remove_duplicate_movies(all_movies)
        all_organized_movies = _organize_movies_by_alphabet(all_unique_movies)
        
        # Count non-empty letters
        recent_letters = len([l for l in recent_organized_movies if recent_organized_movies[l]])
        all_time_letters = len([l for l in all_organized_movies if all_organized_movies[l]])
        
        # Create time period selection for all letters
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🕐 Last 24h ({recent_letters} letters)", callback_data="time_select_all:24h"),
                InlineKeyboardButton(f"📅 All Time ({all_time_letters} letters)", callback_data="time_select_all:all_time")
            ],
            [
                InlineKeyboardButton("🔙 Back to All Lists", callback_data="back_to_lists")
            ]
        ])
        
        await callback_query.message.edit_text(
            "📋 <b>All Lists Options</b>\n\n"
            f"📊 <b>Available Lists:</b>\n"
            f"• 🕐 Last 24 Hours: {recent_letters} letters with movies\n"
            f"• 📅 All Time: {all_time_letters} letters with movies\n\n"
            "<i>Select which time period to include:</i>\n"
            "• <b>Last 24 Hours:</b> Continue where we left off (edit existing)\n"
            "• <b>All Time:</b> Send complete lists (delete & recreate all)",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error handling all letters: {e}")
        await callback_query.answer("❌ Error", show_alert=True)

async def _handle_time_selection(client, callback_query):
    """Handle time period selection"""
    try:
        data_parts = callback_query.data.split(":")
        
        if len(data_parts) == 3:  # Single letter time selection
            _, letter, time_period = data_parts
            # Now show target selection for single letter
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"📤 Send to Channel", callback_data=f"send_single:{letter}:channel:{time_period}"),
                    InlineKeyboardButton(f"🤖 Send to Bot", callback_data=f"send_single:{letter}:bot:{time_period}")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data=f"send_letter:{letter}")
                ]
            ])
            
            time_desc = "Last 24 Hours" if time_period == "24h" else "All Time"
            await callback_query.message.edit_text(
                f"📋 <b>{letter} List - {time_desc}</b>\n\n"
                f"<i>Select where to send the {letter} list:</i>",
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )
            
        else:  # All letters time selection
            _, time_period = data_parts
            # Now show target selection for all letters
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📤 Send All to Channel", callback_data=f"send_all:channel:{time_period}"),
                    InlineKeyboardButton("🤖 Send All to Bot", callback_data=f"send_all:bot:{time_period}")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="send_all_letters")
                ]
            ])
            
            time_desc = "Last 24 Hours" if time_period == "24h" else "All Time"
            await callback_query.message.edit_text(
                f"📋 <b>All Lists - {time_desc}</b>\n\n"
                f"<i>Select where to send all alphabetical lists:</i>",
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        log.error(f"💥 Error handling time selection: {e}")
        await callback_query.answer("❌ Error", show_alert=True)

async def _handle_cancel_list(client, callback_query):
    """Handle list cancellation"""
    try:
        await callback_query.answer("❌ Cancelled")
        await callback_query.message.delete()
        log.info(f"✅ List operation cancelled by user {callback_query.from_user.id}")
    except Exception as e:
        log.error(f"💥 Error cancelling list: {e}")

async def _show_alphabet_selection(client, callback_query):
    """Show alphabet selection again"""
    try:
        # Get recent movies to regenerate organized list
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        recent_movies = get_recent_movies(start_time, end_time)
        
        if not recent_movies:
            await callback_query.message.edit_text("❌ No movies found.")
            return
        
        unique_movies = _remove_duplicate_movies(recent_movies)
        organized_movies = _organize_movies_by_alphabet(unique_movies)
        
        alphabet_buttons = _create_alphabet_buttons(organized_movies)
        
        summary_message = (
            f"📋 <b>Movie List Summary - Last 24 Hours</b>\n\n"
            f"📊 <b>Total Movies Found:</b> {len(recent_movies)}\n"
            f"🎯 <b>Unique Movies:</b> {len(unique_movies)}\n"
            f"🔤 <b>Alphabetical Sections:</b> {len(organized_movies)}\n"
            f"🕐 <b>Time Period:</b> Last 24 hours\n\n"
            f"<b>Select which lists to send:</b>"
        )
        
        await callback_query.message.edit_text(
            summary_message,
            reply_markup=alphabet_buttons,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error showing alphabet selection: {e}")
        await callback_query.answer("❌ Error", show_alert=True)

async def handle_list_callback(client, callback_query):
    """Handle callback for list posting options"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        log.info(f"🔄 List callback received: {data} from user {user_id}")
        
        if data.startswith("send_letter:"):
            await _handle_single_letter(client, callback_query)
        elif data == "send_all_letters":
            await _handle_all_letters(client, callback_query)
        elif data.startswith("time_select:"):
            await _handle_time_selection(client, callback_query)
        elif data.startswith("time_select_all:"):
            await _handle_time_selection(client, callback_query)
        elif data.startswith("send_single:"):
            parts = data.split(":")
            if len(parts) == 4:
                _, letter, target, time_period = parts
                await _process_list_sending(client, callback_query, letter, target, time_period)
            else:
                # Backward compatibility
                _, letter, target = parts
                await _process_list_sending(client, callback_query, letter, target, "24h")
        elif data.startswith("send_all:"):
            parts = data.split(":")
            if len(parts) == 3:
                _, target, time_period = parts
                await _process_list_sending(client, callback_query, target=target, time_period=time_period)
            else:
                # Backward compatibility
                _, target = parts
                await _process_list_sending(client, callback_query, target=target, time_period="24h")
        elif data == "back_to_lists":
            await _show_alphabet_selection(client, callback_query)
        elif data == "cancel_list":
            await _handle_cancel_list(client, callback_query)
        else:
            log.warning(f"⚠️ Unknown list callback: {data}")
            await callback_query.answer("❌ Unknown action")
        
    except Exception as e:
        log.error(f"💥 Error in list callback handler: {e}")
        await callback_query.answer("❌ Error processing your request.", show_alert=True)

# Register list handlers
def register_list_handlers(client: Client):
    client.on_message(filters.command("list") & filters.private)(list_command)
    client.on_callback_query(filters.regex(r"^(send_letter:|send_single:|send_all:|send_all_letters|back_to_lists|cancel_list|time_select:|time_select_all:)"))(handle_list_callback)
    log.info("🎯 List handlers registered successfully")
