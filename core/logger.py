import sys
import os
from loguru import logger

# Import config directly without circular dependency
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

def setup_logger():
    """Configure Loguru logger with custom settings"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Add file handler
    logger.add(
        "./logs/bot.log",
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="1 month",
        compression="zip"
    )
    
    logger.info("📝 Logger setup completed")
    return logger

# Create global logger instance
log = setup_logger()