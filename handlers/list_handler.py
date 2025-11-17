from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from pyrogram import enums
from datetime import datetime, timedelta
from database.movie_data import get_recent_movies
from config import DOWNLOAD_BOT_LINK, LIST_CHANNEL_ID
from core.logger import log

# Store message IDs for editing
list_message_ids = {}

async def list_command(client: Client, message: Message):
    """Handle /list command to show recent movies organized by alphabet"""
    try:
        log.info(f"📋 /list command received from user {message.from_user.id} (@{message.from_user.username})")
        
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
        
        # Create alphabet buttons
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
    """Create inline keyboard with alphabet buttons"""
    try:
        buttons = []
        row = []
        
        # Add alphabet buttons
        for letter in organized_movies.keys():
            row.append(InlineKeyboardButton(f"📋 {letter}", callback_data=f"send_letter:{letter}"))
            if len(row) == 3:  # 3 buttons per row
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
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Error", callback_data="noop")]])

def _remove_duplicate_movies(movies):
    """Remove duplicate movies based on title (case insensitive)"""
    try:
        seen_titles = set()
        unique_movies = []
        
        for movie in movies:
            title = movie.get('movie_title', '').strip().lower()
            if not title:
                continue
                
            # Clean the title for better deduplication
            clean_title = _clean_movie_title(title)
            
            if clean_title not in seen_titles:
                seen_titles.add(clean_title)
                unique_movies.append(movie)
        
        log.info(f"🔄 Deduplication: {len(movies)} → {len(unique_movies)} unique titles")
        return unique_movies
        
    except Exception as e:
        log.error(f"💥 Error removing duplicates: {e}")
        return movies

def _clean_movie_title(title):
    """Clean movie title for better deduplication"""
    try:
        import re
        
        # Remove common quality indicators
        quality_patterns = [
            r'\b(480p|720p|1080p|2160p|4k|hd|fhd|uhd|bluray|webdl|webrip|dvdrip|brrip)\b',
            r'\b(x264|x265|h264|h265|hevc|avc)\b',
            r'\b(ac3|aac|dd5\.1|dts)\b',
            r'\[.*?\]',  # Remove anything in brackets
            r'\(.*?\)',  # Remove anything in parentheses (but keep year)
        ]
        
        clean_title = title.lower().strip()
        
        # Remove quality patterns
        for pattern in quality_patterns:
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
        
        # Remove extra spaces and special characters
        clean_title = re.sub(r'[^\w\s]', ' ', clean_title)  # Replace special chars with space
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()  # Remove extra spaces
        
        # Extract year if present (for better grouping)
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_title)
        if year_match:
            year = year_match.group()
            # Remove year from title for deduplication
            clean_title = re.sub(r'\s*\b(19|20)\d{2}\b', '', clean_title).strip()
            # Add year at the end for consistent grouping
            clean_title = f"{clean_title} {year}"
        
        return clean_title.strip()
        
    except Exception as e:
        log.error(f"💥 Error cleaning movie title: {e}")
        return title.lower().strip()

def _organize_movies_by_alphabet(movies):
    """Organize movies by their starting letter"""
    try:
        organized = {}
        
        for movie in movies:
            title = movie.get('movie_title', '').strip()
            if not title:
                continue
                
            # Convert to title case for display
            display_title = title.title()
            first_char = display_title[0].upper()
            
            # Handle special characters and numbers
            if not first_char.isalpha():
                first_char = "#"
            
            if first_char not in organized:
                organized[first_char] = []
            
            # Only add if not already in the list (case insensitive)
            if display_title.lower() not in [m.lower() for m in organized[first_char]]:
                organized[first_char].append(display_title)
        
        # Sort the letters and movies within each letter
        for letter in organized:
            organized[letter].sort(key=lambda x: x.lower())
        
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
        message_parts.append(f"<code>@Moviessearchfilterbot</code>")
        message_parts.append("")
        
        for movie in chunk_movies:
            # Truncate long movie names
            display_name = movie[:50] + "..." if len(movie) > 50 else movie
            message_parts.append(f"▶️{display_name}")
        
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
        elif data == "cancel_list":
            await _handle_cancel_list(client, callback_query)
        else:
            log.warning(f"⚠️ Unknown list callback: {data}")
            await callback_query.answer("❌ Unknown action")
        
    except Exception as e:
        log.error(f"💥 Error in list callback handler: {e}")
        await callback_query.answer("❌ Error processing your request.", show_alert=True)

async def _handle_single_letter(client, callback_query):
    """Handle sending/editing a single letter list"""
    try:
        letter = callback_query.data.split(":")[1]
        await callback_query.answer(f"🔄 Processing {letter} list...")
        log.info(f"📋 Processing {letter} list for user {callback_query.from_user.id}")
        
        # Get recent movies
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        recent_movies = get_recent_movies(start_time, end_time)
        
        if not recent_movies:
            await callback_query.message.edit_text("❌ No movies found to send.")
            return
        
        # Remove duplicates and organize
        unique_movies = _remove_duplicate_movies(recent_movies)
        organized_movies = _organize_movies_by_alphabet(unique_movies)
        
        if letter not in organized_movies:
            await callback_query.answer(f"❌ No {letter} list found", show_alert=True)
            return
        
        # Create posting options for single letter
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"📤 Send {letter} to Channel", callback_data=f"send_single:{letter}:channel"),
                InlineKeyboardButton(f"🤖 Send {letter} to Bot", callback_data=f"send_single:{letter}:bot")
            ],
            [
                InlineKeyboardButton("🔙 Back to All Lists", callback_data="back_to_lists")
            ]
        ])
        
        await callback_query.message.edit_text(
            f"📋 <b>{letter} List Ready</b>\n\n"
            f"📊 <b>Movies in {letter} list:</b> {len(organized_movies[letter])}\n"
            f"🕐 <b>Time Period:</b> Last 24 hours\n\n"
            f"<i>Select where to send the {letter} list:</i>",
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
        
        # Create posting options for all letters
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📤 Send All to Channel", callback_data="send_all:channel"),
                InlineKeyboardButton("🤖 Send All to Bot", callback_data="send_all:bot")
            ],
            [
                InlineKeyboardButton("🔙 Back to All Lists", callback_data="back_to_lists")
            ]
        ])
        
        await callback_query.message.edit_text(
            "📋 <b>All Lists Ready</b>\n\n"
            "<i>Select where to send all alphabetical lists:</i>",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )
        
    except Exception as e:
        log.error(f"💥 Error handling all letters: {e}")
        await callback_query.answer("❌ Error", show_alert=True)

async def _handle_cancel_list(client, callback_query):
    """Handle list cancellation"""
    try:
        await callback_query.answer("❌ Cancelled")
        await callback_query.message.delete()
        log.info(f"✅ List operation cancelled by user {callback_query.from_user.id}")
    except Exception as e:
        log.error(f"💥 Error cancelling list: {e}")

async def _send_or_edit_list_message(client, chat_id, letter, movies, is_channel=True):
    """Send new list or edit existing one"""
    try:
        # Split movies into chunks
        movie_chunks = _split_movies_into_chunks(movies, chunk_size=30)
        total_chunks = len(movie_chunks)
        
        message_ids = []
        
        for chunk_num, chunk_movies in enumerate(movie_chunks, 1):
            list_message = _generate_letter_chunk_message(letter, chunk_movies, chunk_num, total_chunks)
            
            # Add download button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Click to Download", url=DOWNLOAD_BOT_LINK)]
            ])
            
            # Check if we have existing message ID for this letter chunk
            message_key = f"{letter}_{chunk_num}"
            existing_message_id = list_message_ids.get(message_key)
            
            if existing_message_id and is_channel:
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
                    log.debug(f"✏️ Edited existing {letter} list chunk {chunk_num} in channel")
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
                    list_message_ids[message_key] = message.id
            else:
                # Send new message
                message = await client.send_message(
                    chat_id=chat_id,
                    text=list_message,
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
                message_ids.append(message.id)
                if is_channel:
                    list_message_ids[message_key] = message.id
                    log.debug(f"💾 Stored message ID for {letter} chunk {chunk_num}: {message.id}")
        
        return message_ids
        
    except Exception as e:
        log.error(f"💥 Error sending/editing list message: {e}")
        return []

# Update the callback handlers to use the new system
async def _process_list_sending(client, callback_query, letter=None, target="channel"):
    """Process list sending for single letter or all letters"""
    try:
        user_id = callback_query.from_user.id
        is_channel = target == "channel"
        chat_id = LIST_CHANNEL_ID if is_channel else user_id
        chat_name = "channel" if is_channel else "bot"
        
        await callback_query.answer(f"🔄 Sending to {chat_name}...")
        
        # Get recent movies
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        recent_movies = get_recent_movies(start_time, end_time)
        
        if not recent_movies:
            await callback_query.message.edit_text("❌ No movies found to send.")
            return
        
        # Remove duplicates and organize
        unique_movies = _remove_duplicate_movies(recent_movies)
        organized_movies = _organize_movies_by_alphabet(unique_movies)
        
        total_messages_sent = 0
        
        if letter:  # Single letter
            if letter in organized_movies:
                message_ids = await _send_or_edit_list_message(
                    client, chat_id, letter, organized_movies[letter], is_channel
                )
                total_messages_sent = len(message_ids)
                
                await callback_query.message.edit_text(
                    f"✅ <b>{letter} List successfully sent to {chat_name}!</b>\n\n"
                    f"📊 <b>Movies in {letter} list:</b> {len(organized_movies[letter])}\n"
                    f"📤 <b>Messages sent/updated:</b> {total_messages_sent}\n"
                    f"📅 <b>Time period:</b> Last 24 hours\n"
                    f"📍 <b>Target:</b> {chat_name}",
                    parse_mode=enums.ParseMode.HTML
                )
                log.success(f"✅ {letter} list sent to {chat_name} with {total_messages_sent} messages by user {user_id}")
            else:
                await callback_query.answer(f"❌ No {letter} list found", show_alert=True)
        
        else:  # All letters
            for letter, movies in organized_movies.items():
                message_ids = await _send_or_edit_list_message(
                    client, chat_id, letter, movies, is_channel
                )
                total_messages_sent += len(message_ids)
                log.debug(f"✅ Processed {letter} list with {len(message_ids)} messages")
            
            await callback_query.message.edit_text(
                f"✅ <b>All lists successfully sent to {chat_name}!</b>\n\n"
                f"📊 <b>Total unique movies:</b> {len(unique_movies)}\n"
                f"🔤 <b>Alphabet sections:</b> {len(organized_movies)}\n"
                f"📤 <b>Total messages sent/updated:</b> {total_messages_sent}\n"
                f"📅 <b>Time period:</b> Last 24 hours\n"
                f"📍 <b>Target:</b> {chat_name}",
                parse_mode=enums.ParseMode.HTML
            )
            log.success(f"✅ All lists sent to {chat_name} with {total_messages_sent} total messages by user {user_id}")
        
    except Exception as e:
        log.error(f"💥 Error processing list sending: {e}")
        await callback_query.message.edit_text("❌ Failed to send lists.")

# Update the callback query handler to include new actions
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
        elif data.startswith("send_single:"):
            _, letter, target = data.split(":")
            await _process_list_sending(client, callback_query, letter, target)
        elif data.startswith("send_all:"):
            _, target = data.split(":")
            await _process_list_sending(client, callback_query, target=target)
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

# Register list handlers
def register_list_handlers(client: Client):
    client.on_message(filters.command("list") & filters.private)(list_command)
    client.on_callback_query(filters.regex(r"^(list_letter:|send_letter:|send_single:|send_all:|send_all_letters|back_to_lists|cancel_list|list_all|list_back|list_cancel)$"))(handle_list_callback)
    log.info("🎯 List handlers registered successfully")