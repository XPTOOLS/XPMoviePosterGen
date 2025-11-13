import re
from pyrogram.types import Message
from typing import Tuple, Optional
from core.logger import log

async def extract_movie_title(message: Message) -> Tuple[str, Optional[int]]:
    """Extract movie title and year from various message types"""
    try:
        # Case 1: Text message
        if message.text:
            log.debug("📝 Processing text message")
            return _extract_title_and_year(message.text)
        
        # Case 2: Document with filename
        if message.document and message.document.file_name:
            log.debug("📄 Processing document with filename")
            filename = message.document.file_name
            title, year = _extract_title_and_year_from_filename(filename)
            if title:
                return title, year
        
        # Case 3: Photo with caption
        if message.photo and message.caption:
            log.debug("🖼️ Processing photo with caption")
            return _extract_title_and_year(message.caption)
        
        # Case 4: Video with caption or filename
        if message.video:
            if message.caption:
                log.debug("🎥 Processing video with caption")
                return _extract_title_and_year(message.caption)
            elif message.video.file_name:
                log.debug("🎥 Processing video with filename")
                title, year = _extract_title_and_year_from_filename(message.video.file_name)
                if title:
                    return title, year
        
        # Case 5: Check caption for any media
        if message.caption:
            log.debug("📋 Processing message caption")
            return _extract_title_and_year(message.caption)
        
        log.warning("🔍 No movie title could be extracted from message")
        return "", None
        
    except Exception as e:
        log.error(f"💥 Error extracting movie title: {e}")
        return "", None

def _extract_title_and_year(text: str) -> Tuple[str, Optional[int]]:
    """Extract title and year from text"""
    if not text:
        return "", None
    
    cleaned = text.strip()
    
    # Remove URLs
    cleaned = re.sub(r'http\S+', '', cleaned)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Extract year from various patterns
    year = None
    year_patterns = [
        r'\((\d{4})\)',  # (2014)
        r'\[(\d{4})\]',  # [2014]
        r'\s+(\d{4})\s*$',  # 2014 at the end
        r'\s+\((\d{4})\)\s*$',  # (2014) at the end
        r'^(\d{4})\s+',  # 2014 at the beginning
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, cleaned)
        if match:
            try:
                year = int(match.group(1))
                # Remove the year part from the title
                cleaned = re.sub(pattern, '', cleaned).strip()
                break
            except (ValueError, IndexError):
                continue
    
    # Trim to reasonable length (first 100 chars)
    cleaned = cleaned[:100].strip()
    
    if cleaned and len(cleaned) > 2:
        log.debug(f"🧹 Extracted title: '{text}' → '{cleaned}' (year: {year})")
        return cleaned, year
    
    return "", None

def _extract_title_and_year_from_filename(filename: str) -> Tuple[str, Optional[int]]:
    """Extract movie title and year from filename"""
    try:
        # Remove file extension
        name_without_ext = re.sub(r'\.[^.]*$', '', filename)
        
        # First, try to extract TV series pattern (most specific)
        series_match = _extract_tv_series_pattern(name_without_ext)
        if series_match:
            # For TV series, extract year separately
            series_title, series_year = _extract_title_and_year(series_match)
            return series_title, series_year
        
        # Extract year from filename first
        year = None
        year_match = re.search(r'\b(19|20)\d{2}\b', name_without_ext)
        if year_match:
            try:
                year = int(year_match.group(0))
                # Remove the year for title cleaning
                name_without_ext = re.sub(r'\b(19|20)\d{2}\b', '', name_without_ext)
            except ValueError:
                pass
        
        # Common patterns in movie filenames
        patterns_to_remove = [
            r'\b\d{3,4}p\b',  # Resolution like 1080p, 720p
            r'\bbluray\b', r'\bwebrip\b', r'\bwebdl\b', r'\bhdrip\b', r'\bdvdrip\b',
            r'\bx264\b', r'\bx265\b', r'\bhevc\b', r'\bavc\b',
            r'\[.*?\]', r'\(.*?\)',  # Brackets and parentheses (but we already extracted year)
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
        
        if cleaned:
            log.debug(f"🔄 Filename '{filename}' → Title '{cleaned}' (year: {year})")
            return cleaned, year
        
        return "", None
        
    except Exception as e:
        log.error(f"💥 Error extracting title from filename: {e}")
        return "", None

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

# Keep the old function for backward compatibility but mark it as deprecated
def _clean_movie_title(title: str) -> str:
    """DEPRECATED: Use _extract_title_and_year instead"""
    cleaned_title, _ = _extract_title_and_year(title)
    return cleaned_title

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
