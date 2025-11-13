"""
Movie Poster Generator Telegram Bot
Automatically generates stylized movie posters from TMDB data
"""

__version__ = "1.0.0"
__author__ = "Itachi Dev"
__description__ = "Pyrogram-based Telegram bot for automatic movie poster generation"

from utils.asset_manager import asset_manager
from utils.file_detector import extract_movie_title, extract_season_series_info
from utils.tmdb_api import tmdb_api
from utils.image_generator import poster_generator
from utils.caption_builder import build_caption, build_compact_caption
from utils.channel_poster import send_to_channel
from utils.omdb_api import omdb_api, OMDbAPI

__all__ = [
    'asset_manager',
    'extract_movie_title',
    'extract_season_series_info', 
    'tmdb_api',
    'omdb_api',  # NEW
    'OMDbAPI',   # NEW
    'poster_generator',
    'build_caption',
    'build_compact_caption',
    'send_to_channel'
]