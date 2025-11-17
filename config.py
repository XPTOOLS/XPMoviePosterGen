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
