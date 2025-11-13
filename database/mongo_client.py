from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import MONGO_URI, DATABASE_NAME
from core.logger import log

class MongoDBClient:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            if not MONGO_URI:
                log.warning("📭 MONGO_URI not set - running without database")
                return
            
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[DATABASE_NAME]
            log.success("✅ Successfully connected to MongoDB")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            log.warning(f"📭 MongoDB connection failed: {e}")
            self.client = None
            self.db = None
        except Exception as e:
            log.error(f"💥 Unexpected MongoDB error: {e}")
            self.client = None
            self.db = None
    
    def get_collection(self, collection_name):
        """Get a specific collection from database"""
        if self.db is None:
            return None
        
        return self.db[collection_name]
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            log.info("📭 MongoDB connection closed")

# Global MongoDB client instance
mongo_client = MongoDBClient()