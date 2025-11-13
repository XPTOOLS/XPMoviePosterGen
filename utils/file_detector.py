import re
from pyrogram.types import Message
from core.logger import log

async def extract_movie_title(message: Message) -> str:
    """Extract movie title from various message types"""
    try:
        # Case 1: Text message
        if message.text:
            log.debug("📝 Processing text message")
            return _clean_movie_title(message.text)
        
        # Case 2: Document with filename
        if message.document and message.document.file_name:
            log.debug("📄 Processing document with filename")
            filename = message.document.file_name
            title = _extract_title_from_filename(filename)
            if title:
                return title
        
        # Case 3: Photo with caption
        if message.photo and message.caption:
            log.debug("🖼️ Processing photo with caption")
            return _clean_movie_title(message.caption)
        
        # Case 4: Video with caption or filename
        if message.video:
            if message.caption:
                log.debug("🎥 Processing video with caption")
                return _clean_movie_title(message.caption)
            elif message.video.file_name:
                log.debug("🎥 Processing video with filename")
                title = _extract_title_from_filename(message.video.file_name)
                if title:
                    return title
        
        # Case 5: Check caption for any media
        if message.caption:
            log.debug("📋 Processing message caption")
            return _clean_movie_title(message.caption)
        
        log.warning("🔍 No movie title could be extracted from message")
        return ""
        
    except Exception as e:
        log.error(f"💥 Error extracting movie title: {e}")
        return ""

def _extract_title_from_filename(filename: str) -> str:
    """Extract movie title from filename - IMPROVED for TV series"""
    try:
        # Remove file extension
        name_without_ext = re.sub(r'\.[^.]*$', '', filename)
        
        # First, try to extract TV series pattern (most specific)
        series_match = _extract_tv_series_pattern(name_without_ext)
        if series_match:
            return series_match
        
        # Common patterns in movie filenames
        patterns_to_remove = [
            r'\b\d{3,4}p\b',  # Resolution like 1080p, 720p (word boundaries)
            r'\bbluray\b', r'\bwebrip\b', r'\bwebdl\b', r'\bhdrip\b', r'\bdvdrip\b',
            r'\bx264\b', r'\bx265\b', r'\bhevc\b', r'\bavc\b',
            r'\b\d{4}\b',  # Year as separate word
            r'\[.*?\]', r'\(.*?\)',  # Brackets and parentheses
            r'\b(?:ppv|rip|dvd|scr|brrip|brip|extended|remastered|unrated|directors.cut)\b',
            r'\b(?:ac3|dts|aac|mp3|dd5\.1|dts\-hd)\b',  # Audio codecs
            r'\b(?:h264|h265|av1)\b',  # Video codecs
            r'\b(?:rarbg|yts|amzn|amazon|web|hdtv)\b',  # Sources
            r'\b(?:dubbed|dual\.audio|subbed)\b',  # Audio features
            r'\b(?:youthtrendx|rarbg|yts|amzn|amazon)\b',  # Release groups
        ]
        
        # Clean the filename step by step
        cleaned = name_without_ext
        
        # First, try to extract title between specific patterns
        # Look for patterns like: Movie.Name.2025.1080p... or Movie-Name-2025...
        title_match = re.search(r'^([A-Za-z0-9]+(?:[.\-\s][A-Za-z0-9]+)*)', cleaned)
        if title_match:
            cleaned = title_match.group(1)
        
        # Remove all the patterns
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace dots, underscores, and hyphens with spaces
        cleaned = re.sub(r'[._\-]', ' ', cleaned)
        
        # Remove extra spaces and trim
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If we have what looks like a year at the end, remove it
        cleaned = re.sub(r'\s+\d{4}$', '', cleaned)
        
        if cleaned:
            log.debug(f"🔄 Filename '{filename}' → Title '{cleaned}'")
            return cleaned
        
        return ""
        
    except Exception as e:
        log.error(f"💥 Error extracting title from filename: {e}")
        return ""

def _extract_tv_series_pattern(filename: str) -> str:
    """Extract TV series name from filename patterns"""
    try:
        # TV series patterns (most specific first)
        patterns = [
            # S01E01 pattern
            r'^(.+?)[\.\s\-_]*(?:s\d{1,2}e\d{1,2}|season[\s\.]?\d{1,2}[\s\.]?episode[\s\.]?\d{1,2})',
            # S01 pattern (season only)
            r'^(.+?)[\.\s\-_]*(?:s\d{1,2}(?!e\d))',
            # Season 1 pattern
            r'^(.+?)[\.\s\-_]*(?:season[\s\.]?\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                series_name = match.group(1).strip()
                # Clean up the series name
                series_name = re.sub(r'[._\-]', ' ', series_name)
                series_name = re.sub(r'\s+', ' ', series_name).strip()
                
                # Remove common quality/release patterns that might be at the end
                series_name = re.sub(r'\s*(?:1080p|720p|webrip|bluray|youthtrendx).*$', '', series_name, flags=re.IGNORECASE)
                series_name = series_name.strip()
                
                if series_name:
                    log.debug(f"📺 Extracted series name: '{series_name}' from '{filename}'")
                    return series_name
        
        return ""
        
    except Exception as e:
        log.error(f"💥 Error extracting TV series pattern: {e}")
        return ""

def _clean_movie_title(title: str) -> str:
    """Clean and normalize movie title"""
    if not title:
        return ""
    
    # Remove common prefixes/suffixes and clean up
    cleaned = title.strip()
    
    # Remove URLs
    cleaned = re.sub(r'http\S+', '', cleaned)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove year at the end if present
    cleaned = re.sub(r'\s*\(\d{4}\)\s*$', '', cleaned)
    cleaned = re.sub(r'\s*\d{4}\s*$', '', cleaned)
    
    # Trim to reasonable length (first 100 chars)
    cleaned = cleaned[:100].strip()
    
    if cleaned and len(cleaned) > 2:
        log.debug(f"🧹 Cleaned title: '{title}' → '{cleaned}'")
        return cleaned
    
    return ""

def is_duplicate_request(movie_title: str, file_size: int = None) -> bool:
    """Check if this is a duplicate movie request (same title + similar size)"""
    # This will be enhanced when we implement the database
    # For now, we'll do basic title matching
    from database.movie_data import get_recent_requests
    
    recent_requests = get_recent_requests(movie_title)
    
    if recent_requests:
        log.info(f"🔄 Possible duplicate detected: {movie_title}")
        return True
    
    return False

def extract_season_series_info(filename: str) -> dict:
    """Extract season and series information from filename"""
    try:
        # Patterns for TV series (most specific first)
        season_patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
            r'(\d{1,2})[Xx](\d{1,2})',      # 1x01
            r'[Ss]eason[\s\.]?(\d{1,2})[\s\.]?[Ee]pisode[\s\.]?(\d{1,2})',  # Season 1 Episode 1
            r'[Ss](\d{1,2})',               # S01
            r'[Ss]eason[\s\.]?(\d{1,2})',   # Season 1
        ]
        
        for pattern in season_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                season_num = int(match.group(1)) if match.groups() else 1
                episode_num = int(match.group(2)) if len(match.groups()) > 1 else None
                
                # Extract series name by removing the season/episode pattern and everything after
                series_name = _extract_series_name(filename, pattern)
                
                return {
                    'is_series': True,
                    'season': season_num,
                    'episode': episode_num,
                    'series_name': series_name
                }
        
        return {'is_series': False}
        
    except Exception as e:
        log.error(f"💥 Error extracting series info: {e}")
        return {'is_series': False}

def _extract_series_name(filename: str, pattern: str) -> str:
    """Extract series name by removing season/episode patterns and quality info"""
    try:
        # Remove the season/episode pattern and everything after it
        cleaned = re.sub(pattern + '.*', '', filename, flags=re.IGNORECASE)
        
        # Remove common file patterns and quality info
        quality_patterns = [
            r'[\.\s\-_]*(?:1080p|720p|480p|2160p|4k)',
            r'[\.\s\-_]*(?:webrip|webdl|bluray|hdtv|dvdrip)',
            r'[\.\s\-_]*(?:x264|x265|hevc|avc)',
            r'[\.\s\-_]*(?:youthtrendx|rarbg|yts|amzn)',
            r'[\.\s\-_]*$'  # Trailing separators
        ]
        
        for quality_pattern in quality_patterns:
            cleaned = re.sub(quality_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace dots, underscores, and hyphens with spaces
        cleaned = re.sub(r'[._\-]', ' ', cleaned)
        
        # Remove extra spaces and trim
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
        
    except Exception as e:
        log.error(f"💥 Error extracting series name: {e}")
        # Fallback: basic cleaning
        return re.sub(r'[._\-]', ' ', filename).strip()