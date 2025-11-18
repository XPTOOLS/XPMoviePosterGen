import time
from database.mongo_client import mongo_client
from core.logger import log

class MovieDataManager:
    def __init__(self):
        self.collection = mongo_client.get_collection("movie_requests")
        self.series_collection = mongo_client.get_collection("processed_series")
        self.list_messages_collection = mongo_client.get_collection("list_messages")
    
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
    
    def is_series_processed(self, series_name: str, season: int) -> bool:
        """Check if a series season has already been processed"""
        try:
            if self.series_collection is None:
                return False
            
            # Look for this series + season in the database
            existing = self.series_collection.find_one({
                "series_name": series_name.lower().strip(),
                "season": season
            })
            
            return existing is not None
            
        except Exception as e:
            log.error(f"💥 Error checking series processed status: {e}")
            return False
    
    def mark_series_processed(self, series_name: str, season: int):
        """Mark a series season as processed"""
        try:
            if self.series_collection is None:
                return
            
            self.series_collection.insert_one({
                "series_name": series_name.lower().strip(),
                "season": season,
                "timestamp": time.time()
            })
            log.debug(f"✅ Marked series as processed: {series_name} Season {season}")
            
        except Exception as e:
            log.error(f"💥 Error marking series as processed: {e}")

    def get_recent_movies(self, start_time, end_time):
        """Get movies processed within a time range"""
        try:
            log.info(f"📊 Fetching recent movies from {start_time} to {end_time}")
            
            # Convert datetime to timestamp for database query
            start_timestamp = start_time.timestamp()
            end_timestamp = end_time.timestamp()
            
            # Get ALL movies from the time range
            recent_movies = list(self.collection.find({
                "timestamp": {
                    '$gte': start_timestamp,
                    '$lte': end_timestamp
                }
            }).sort("timestamp", -1))
            
            log.success(f"✅ Found {len(recent_movies)} movies in the time range")
            return recent_movies
            
        except Exception as e:
            log.error(f"💥 Error getting recent movies: {e}")
            return []

    def get_list_message_ids(self):
        """Get stored list message IDs from database"""
        try:
            if self.list_messages_collection is None:
                return {}
                
            result = self.list_messages_collection.find_one({"_id": "message_ids"})
            return result.get("message_ids", {}) if result else {}
        except Exception as e:
            log.error(f"💥 Error getting list message IDs: {e}")
            return {}

    def save_list_message_ids(self, message_ids):
        """Save list message IDs to database"""
        try:
            if self.list_messages_collection is None:
                return
                
            self.list_messages_collection.update_one(
                {"_id": "message_ids"},
                {"$set": {"message_ids": message_ids}},
                upsert=True
            )
            log.debug(f"💾 Saved {len(message_ids)} list message IDs to database")
        except Exception as e:
            log.error(f"💥 Error saving list message IDs: {e}")

    def get_all_movies(self):
        """Get ALL movies from database (not just recent)"""
        try:
            if self.collection is None:
                return []
                
            all_movies = list(self.collection.find({}).sort("timestamp", -1))
            log.info(f"📊 Retrieved {len(all_movies)} total movies from database")
            return all_movies
        except Exception as e:
            log.error(f"💥 Error getting all movies: {e}")
            return []

    def delete_list_message_ids(self):
        """Delete all list message IDs from database"""
        try:
            if self.list_messages_collection is None:
                return False
                
            result = self.list_messages_collection.delete_one({"_id": "message_ids"})
            log.info("🗑️ Deleted all list message IDs from database")
            return result.deleted_count > 0
        except Exception as e:
            log.error(f"💥 Error deleting list message IDs: {e}")
            return False

# Global movie data manager
movie_data_manager = MovieDataManager()

# Helper functions for easy access
def log_movie_request(movie_title: str, file_size: int = None, user_id: int = None):
    movie_data_manager.log_request(movie_title, file_size, user_id)

def get_recent_requests(movie_title: str, time_window: int = 3600) -> list:
    return movie_data_manager.get_recent_requests(movie_title, time_window)

def mark_movie_processed(movie_title: str):
    movie_data_manager.mark_as_processed(movie_title)

def is_series_processed(series_name: str, season: int) -> bool:
    return movie_data_manager.is_series_processed(series_name, season)

def mark_series_processed(series_name: str, season: int):
    movie_data_manager.mark_series_processed(series_name, season)

def get_recent_movies(start_time, end_time):
    return movie_data_manager.get_recent_movies(start_time, end_time)

def get_list_message_ids():
    return movie_data_manager.get_list_message_ids()

def save_list_message_ids(message_ids):
    movie_data_manager.save_list_message_ids(message_ids)

def get_all_movies():
    return movie_data_manager.get_all_movies()

def delete_list_message_ids():
    return movie_data_manager.delete_list_message_ids()
