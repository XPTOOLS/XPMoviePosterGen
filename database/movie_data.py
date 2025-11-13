import time
from database.mongo_client import mongo_client
from core.logger import log

class MovieDataManager:
    def __init__(self):
        self.collection = mongo_client.get_collection("movie_requests")
    
    def log_request(self, movie_title: str, file_size: int = None, user_id: int = None):
        """Log a movie request to detect duplicates"""
        try:
            if self.collection is None:
                return
            
            request_data = {
                "movie_title": movie_title.lower().strip(),
                "file_size": file_size,
                "user_id": user_id,
                "timestamp": time.time(),
                "processed": False
            }
            
            self.collection.insert_one(request_data)
            log.debug(f"📝 Logged movie request: {movie_title}")
            
        except Exception as e:
            log.error(f"💥 Error logging movie request: {e}")
    
    def get_recent_requests(self, movie_title: str, time_window: int = 3600) -> list:
        """Get recent requests for the same movie (within time window)"""
        try:
            if self.collection is None:
                return []
            
            cutoff_time = time.time() - time_window
            
            recent_requests = list(self.collection.find({
                "movie_title": movie_title.lower().strip(),
                "timestamp": {"$gte": cutoff_time}
            }).sort("timestamp", -1).limit(10))
            
            return recent_requests
            
        except Exception as e:
            log.error(f"💥 Error getting recent requests: {e}")
            return []
    
    def mark_as_processed(self, movie_title: str):
        """Mark a movie request as processed"""
        try:
            if self.collection is None:
                return
            
            self.collection.update_many(
                {"movie_title": movie_title.lower().strip(), "processed": False},
                {"$set": {"processed": True}}
            )
            log.debug(f"✅ Marked {movie_title} as processed")
            
        except Exception as e:
            log.error(f"💥 Error marking as processed: {e}")

# Global movie data manager
movie_data_manager = MovieDataManager()

# Helper functions for easy access
def log_movie_request(movie_title: str, file_size: int = None, user_id: int = None):
    movie_data_manager.log_request(movie_title, file_size, user_id)

def get_recent_requests(movie_title: str, time_window: int = 3600) -> list:
    return movie_data_manager.get_recent_requests(movie_title, time_window)

def mark_movie_processed(movie_title: str):
    movie_data_manager.mark_as_processed(movie_title)