from core.logger import log
from config import CHANNEL_WATERMARK_HANDLE

def build_caption(movie_data: dict) -> str:
    """Build stylish formatted caption for the movie post"""
    try:
        title = movie_data.get('title', 'Unknown Title')
        rating = movie_data.get('tmdb_rating', 0)
        genres = movie_data.get('genres', [])
        release_year = movie_data.get('release_year', '')
        overview = movie_data.get('overview', '')
        original_language = movie_data.get('original_language', 'en')
        
        # Build caption in stylish format
        caption_parts = []
        
        # Title with year (popcorn emoji)
        if release_year:
            caption_parts.append(f"<b>🍿 Name: {title} ({release_year})</b>")
        else:
            caption_parts.append(f"<b>🍿 Name: {title}</b>")
        
        caption_parts.append("")  # Empty line for spacing
        
        # Genres with hashtags (theater masks emoji)
        if genres:
            genre_hashtags = " ".join([f"#{genre.replace(' ', '')}" for genre in genres[:3]])
            caption_parts.append(f"<b>🎭 Genre</b>: {genre_hashtags}")
        
        # Rating (star emoji)
        if rating > 0:
            caption_parts.append(f"<b>⭐️ IMDb </b>: {rating} / 10")
        
        # Language (speaking head emoji)
        language_map = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese',
            'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian', 'pt': 'Portuguese'
        }
        language_name = language_map.get(original_language, 'English')
        caption_parts.append(f"<b>🗣️ Language </b>:  #{language_name}")
        
        # Storyline (speech balloon emoji) - Limited to 2 lines
        if overview:
            caption_parts.append("")  # Empty line
            caption_parts.append("<b>💬 Storyline</b>:")
            # Truncate overview if too long and split into 2 lines max
            if len(overview) > 200:
                overview = overview[:197] + "..."
            caption_parts.append(f"<blockquote>{overview}</blockquote>")
        
        # Footer with channel watermark
        caption_parts.append("")  # Empty line
        caption_parts.append("▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬")
        caption_parts.append(f"              •{CHANNEL_WATERMARK_HANDLE}•")
        
        caption = "\n".join(caption_parts)
        log.debug(f"📝 Built stylish caption for: {title}")
        
        return caption
        
    except Exception as e:
        log.error(f"💥 Error building caption: {e}")
        return f"<b>🍿 Name</b>: {movie_data.get('title', 'Movie')}\n\n▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬\n              •{CHANNEL_WATERMARK_HANDLE}•"

def build_compact_caption(movie_data: dict) -> str:
    """Build compact caption for when storyline is too long"""
    try:
        title = movie_data.get('title', 'Unknown Title')
        rating = movie_data.get('tmdb_rating', 0)
        genres = movie_data.get('genres', [])
        release_year = movie_data.get('release_year', '')
        
        caption_parts = []
        
        # Title with year
        if release_year:
            caption_parts.append(f"<b>🍿 Name</b>: {title} ({release_year})")
        else:
            caption_parts.append(f"<b>🍿 Name</b>: {title}")
        
        caption_parts.append("")  # Empty line
        
        # Genres
        if genres:
            genre_text = " • ".join(genres[:3])
            caption_parts.append(f"<b>🎭 Genre</b>: {genre_text}")
        
        # Rating
        if rating > 0:
            caption_parts.append(f"<b>⭐️ IMDb </b>: {rating}/10")
        
        # Footer
        caption_parts.append("")  # Empty line
        caption_parts.append("▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬")
        caption_parts.append(f"              •{CHANNEL_WATERMARK_HANDLE}•")
        
        return "\n".join(caption_parts)
        
    except Exception as e:
        log.error(f"💥 Error building compact caption: {e}")
        return f"🍿 Name: {movie_data.get('title', 'Movie')}\n\n▬▬▬▬「 ᴘᴏᴡᴇʀᴇᴅ ʙʏ 」▬▬▬▬\n              •{CHANNEL_WATERMARK_HANDLE}•"
