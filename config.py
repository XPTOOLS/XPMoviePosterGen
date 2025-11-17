import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", ))
API_HASH = os.getenv("API_HASH", "")

# Keep Alive Configuration
PORT = 10000  # Port for the health server

# Welcome image url
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL", "https://i.ibb.co/9mmk62rg/xplogo.jpg")  # Add your image URL

# Movies/Series Generated list channel
LIST_CHANNEL_ID = os.getenv("LIST_CHANNEL_ID", "@MovieBox_x")  # Channel where lists will be posted

# TMDB Configuration - FIXED URLs
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")  # Your v3 API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"  # API base URL
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # Image base URL

# OMDb Configuration - NEW
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
OMDB_BASE_URL = "http://www.omdbapi.com/"

# IMDB Configuration (Fallback)
IMDB_BASE_URL = "https://www.imdb.com"
IMDB_SEARCH_URL = "https://imdb.iamidiotareyoutoo.com/search?q={}"
IMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # We'll use TMDB images for consistency
USE_IMDB_FALLBACK = True  # Enable/disable IMDB fallback

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "")
DATABASE_NAME = "MPoster_bot"

# Channel Configuration
DATABASE_CHANNEL_ID = int(os.getenv("DATABASE_CHANNEL_ID", -1002681833322))
MOVIE_CHANNEL_ID = os.getenv("MOVIE_CHANNEL_ID", "@Movieshub_101")

# Posting Configuration - NEW OPTION
POST_TO_CHANNEL = os.getenv("POST_TO_CHANNEL", "true").lower() == "true"  # true = channel, false = direct
# Private Sending Configuration - NEW
PRIVATE_SEND_USER_ID = int(os.getenv("PRIVATE_SEND_USER_ID", "5962658076"))  # Your user ID

# Download Configuration
DOWNLOAD_BOT_LINK = os.getenv("DOWNLOAD_BOT_LINK", "https://t.me/Moviessearchfilterbot?start")

# Watermark Configuration
CHANNEL_WATERMARK_HANDLE = os.getenv("CHANNEL_WATERMARK_HANDLE", "@Movieshub_101")
TELEGRAM_LOGO_URL = os.getenv("TELEGRAM_LOGO_URL", "https://i.ibb.co/DgKqgfz1/tlogo.png")
TELEGRAM_LOGO_SIZE = int(os.getenv("TELEGRAM_LOGO_SIZE", "50"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# Path Configuration
TEMP_FOLDER = "./temp/posters/"
FONT_PATH_BOLD = "./assets/fonts/Roboto-Bold.ttf"
FONT_PATH_REGULAR = "./assets/fonts/Roboto-Regular.ttf"
POSTER_TEMPLATE = "./assets/templates/background.jpg"

# Text Size Configuration - ENHANCED for 1280x720 poster
TITLE_FONT_SIZE = int(os.getenv("TITLE_FONT_SIZE", "70")) 
RATING_FONT_SIZE = int(os.getenv("RATING_FONT_SIZE", "40")) 
GENRE_FONT_SIZE = int(os.getenv("GENRE_FONT_SIZE", "30")) 
YEAR_FONT_SIZE = int(os.getenv("YEAR_FONT_SIZE", "30")) 
WATERMARK_FONT_SIZE = int(os.getenv("WATERMARK_FONT_SIZE", "24"))

# Poster Configuration - NEW
POSTER_WIDTH = int(os.getenv("POSTER_WIDTH", "450"))
BLUR_RADIUS = int(os.getenv("BLUR_RADIUS", "15"))

# Behavior Configuration
CLEANUP_AFTER_SEND = True
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
OPTIONAL_USE_OCR = False

# Admin Configuration
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",")]

def setup_directories():
    """Create required directories without importing logger"""
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    os.makedirs("./assets/fonts/", exist_ok=True)
    os.makedirs("./assets/templates/", exist_ok=True)
    os.makedirs("./logs/", exist_ok=True)

# Create directories on import
setup_directories()

# Create required directories
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs("./assets/fonts/", exist_ok=True)
os.makedirs("./assets/templates/", exist_ok=True)
os.makedirs("./logs/", exist_ok=True)

# Create directories on import
setup_directories()

# Create required directories
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs("./assets/fonts/", exist_ok=True)
os.makedirs("./assets/templates/", exist_ok=True)
os.makedirs("./logs/", exist_ok=True)

QUALITY_PATTERNS = [
    r'\b(480p|720p|1080p|2160p|4k|hd|fhd|uhd|bluray|webdl|webrip|dvdrip|brrip)\b',
    r'\b(x264|x265|h264|h265|hevc|avc)\b',
    r'\b(ac3|aac|dd5\.1|dts)\b',
    r'\b(\d+mb|\d+gb|pahe|in|hdr|2ch|heydl|yts|rarbg|amzn)\b',
    r'\[.*?\]',  # Remove anything in brackets
    r'\(.*?\)',  # Remove anything in parentheses
]

# Episode patterns for detecting and removing episode information
EPISODE_PATTERNS = [
    r'\s*[Ee]\d{1,3}.*$',  # E01, E02, etc.
    r'\s*[Ee]pisode\s*\d{1,3}.*$',  # Episode 1, Episode 2, etc.
    r'\s*[Ee]p\s*\d{1,3}.*$',  # Ep 1, Ep 2, etc.
    r'\s*[Ss]\d{1,2}[Ee]\d{1,3}.*$',  # S01E01, S01E02, etc.
    r'\s*\d{1,2}[Xx]\d{1,3}.*$',  # 1x01, 1x02, etc.
    r'\s*[Pp]art\s*\d{1,3}.*$',  # Part 1, Part 2, etc.
    r'\s*-\s*\d{1,3}.*$',  # - 01, - 02, etc.
    r'\s*#\d{1,3}.*$',  # #1, #2, etc.
    r'\s*[Ss]eason\s*\d{1,2}.*$',  # Season 1, Season 2, etc.
    r'\s*[Ss]\d{1,2}.*$',  # S01, S02, etc.
    r'\s*\d{1,2}\s*(?:spring|summer|autumn|winter).*$',  # 02 Spring, 03 Summer, etc.
    r'\s*\d{1,2}\s*$',  # Trailing numbers alone
]

# Series name fixes for common abbreviations
SERIES_FIXES = {
    'batman t a s': 'batman the animated series',
    'bbc': 'bbc documentaries',
    'baywatch hdr': 'baywatch',
    'tas': 'the animated series',
    'got': 'game of thrones',
    'tbbt': 'the big bang theory',
    'twd': 'the walking dead',
}

# Common file extensions and patterns (comprehensive list)
COMMON_FILE_INDICATORS = [
    # Quality
    '480p', '720p', '1080p', '2160p', '4k', 'hd', 'fhd', 'uhd',
    'bluray', 'webdl', 'webrip', 'dvdrip', 'brrip', 'hdtv',
    'remux', 'bdrip', 'web', 'bd', 'dvd', 'tvrip',
    
    # Video codecs
    'x264', 'x265', 'h264', 'h265', 'hevc', 'avc', 'av1',
    
    # Audio codecs
    'ac3', 'aac', 'dd5.1', 'dts', 'dts-hd', 'truehd', 'mp3',
    'flac', 'ogg', 'opus',
    
    # Audio channels
    '2ch', '5.1', '7.1', 'stereo', 'mono', 'surround',
    
    # Release groups and sources
    'yts', 'rarbg', 'amzn', 'amazon', 'web', 'hdtv', 'pdtv',
    'dsnp', 'hulu', 'nf', 'netflix', 'atvp', 'dsny', 'hmax',
    
    # File sizes and types
    '450mb', 'pahe', 'in', 'hdr', 'heydl', 'mkv', 'mp4', 'avi',
    'm4v', 'mov', 'wmv', 'flv', 'webm',
    
    # Other common indicators
    'repack', 'proper', 'directors.cut', 'extended', 'unrated',
    'theatrical', 'final', 'limited', 'complete', 'season',
    'episode', 's01', 's02', 's03', 'e01', 'e02', 'e03',
    'dual.audio', 'dubbed', 'subbed', 'subtitles',
]

# Regex pattern for common indicators (auto-generated)
COMMON_INDICATORS_PATTERN = r'\b(' + '|'.join(COMMON_FILE_INDICATORS) + r')\b'

# Channel Handler Configuration - MOVED FROM channel_handler.py

# Common words to remove for better title searching
COMMON_WORDS_TO_REMOVE = [
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
    'for', 'of', 'with', 'by', 'as', 'is', 'was', 'were', 'be', 'been',
    'this', 'that', 'these', 'those', 'from', 'into', 'during', 'including',
    'until', 'against', 'among', 'throughout', 'despite', 'towards', 'upon',
    'concerning', 'about', 'like', 'through', 'over', 'before', 'between',
    'after', 'since', 'without', 'under', 'within', 'along', 'following',
    'across', 'behind', 'beyond', 'plus', 'except', 'but', 'up', 'out',
    'down', 'off', 'above', 'near', 'via'
]

# Title cleaning patterns for duplicate detection
TITLE_CLEANING_PATTERNS = [
    r'[\.\_]',  # Replace dots and underscores with spaces
    r'\s*(19|20)\d{2}\s*',  # Remove years
]

# Series search alternatives
SERIES_SEARCH_ALTERNATIVES = [
    "{original}",  # Original title
    "{title_case}",  # Proper case
    "{and_to_ampersand}",  # Replace "and" with "&"
    "{series_suffix}",  # Add "series" suffix
    "{remove_common_words}",  # Remove common words
    "{extract_main_title}",  # Extract main title part
]

# Cache configuration
CACHE_CONFIG = {
    'movie_cooldown': 3600,  # 1 hour cooldown for movies
    'series_cooldown': 3600,  # 1 hour cooldown for series
    'max_cache_entries': 1000,  # Maximum entries in cache
    'cleanup_batch_size': 100,  # How many to remove when cleaning cache
}

# File Detector Configuration - MOVED FROM file_detector.py

# Year extraction patterns
YEAR_PATTERNS = [
    r'\((\d{4})\)',  # (2014)
    r'\[(\d{4})\]',  # [2014]
    r'\s+(\d{4})\s*$',  # 2014 at the end
    r'\s+\((\d{4})\)\s*$',  # (2014) at the end
    r'^(\d{4})\s+',  # 2014 at the beginning
]

# Filename cleaning patterns
FILENAME_CLEANING_PATTERNS = [
    r'\b\d{3,4}p\b',  # Resolution like 1080p, 720p
    r'\bbluray\b', r'\bwebrip\b', r'\bwebdl\b', r'\bhdrip\b', r'\bdvdrip\b',
    r'\bx264\b', r'\bx265\b', r'\bhevc\b', r'\bavc\b',
    r'\[.*?\]', r'\(.*?\)',  # Brackets and parentheses
    r'\b(?:ppv|rip|dvd|scr|brrip|brip|extended|remastered|unrated|directors\.cut)\b',
    r'\b(?:ac3|dts|aac|mp3|dd5\.1|dts\-hd)\b',  # Audio codecs
    r'\b(?:h264|h265|av1)\b',  # Video codecs
    r'\b(?:rarbg|yts|amzn|amazon|web|hdtv)\b',  # Sources
    r'\b(?:dubbed|dual\.audio|subbed)\b',  # Audio features
    r'\b(?:youthtrendx|rarbg|yts|amzn|amazon)\b',  # Release groups
]

# TV Series detection patterns
TV_SERIES_PATTERNS = [
    # S01E01 pattern
    r'^(.+?)[\.\s\-_]*(?:s\d{1,2}e\d{1,2}|season[\s\.]?\d{1,2}[\s\.]?episode[\s\.]?\d{1,2})',
    # S01 pattern (season only)
    r'^(.+?)[\.\s\-_]*(?:s\d{1,2}(?!e\d))',
    # Season 1 pattern
    r'^(.+?)[\.\s\-_]*(?:season[\s\.]?\d{1,2})',
]

# Season/Episode extraction patterns
SEASON_PATTERNS = [
    r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
    r'(\d{1,2})[Xx](\d{1,2})',      # 1x01
    r'[Ss]eason[\s\.]?(\d{1,2})[\s\.]?[Ee]pisode[\s\.]?(\d{1,2})',  # Season 1 Episode 1
    r'[Ss](\d{1,2})',               # S01
    r'[Ss]eason[\s\.]?(\d{1,2})',   # Season 1
]
