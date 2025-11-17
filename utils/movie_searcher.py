# utils/movie_searcher.py
import time
from typing import Dict, Optional, List
from core.logger import log
from config import USE_IMDB_FALLBACK

class MovieSearcher:
    def __init__(self):
        self.imdb_api = None
        self.tmdb_api = None
        self._init_apis()
        log.info("🎯 Movie Searcher initialized with IMDB primary + TMDB fallback")

    def _init_apis(self):
        """Initialize API clients"""
        try:
            # Primary: IMDB
            from utils.imdb_api import imdb_api as imdb_instance
            self.imdb_api = imdb_instance
            log.success("✅ IMDB API initialized as PRIMARY")
        except Exception as e:
            log.error(f"❌ Failed to initialize IMDB API: {e}")
            self.imdb_api = None

        try:
            # Fallback: TMDB
            from utils.tmdb_api import tmdb_api as tmdb_instance
            self.tmdb_api = tmdb_instance
            log.success("✅ TMDB API initialized as fallback")
        except Exception as e:
            log.error(f"❌ Failed to initialize TMDB API: {e}")
            self.tmdb_api = None

    def search_media(self, query: str, year: Optional[int] = None, media_type: str = "auto", limit: int = 10) -> List[Dict]:
        """Search media with IMDB primary + TMDB fallback"""
        log.info(f"🔍 Searching {media_type}: '{query}' (year: {year})")
        
        all_results = []
        
        # Step 1: Try IMDB first (Primary)
        if self.imdb_api:
            if media_type == "tv" or media_type == "auto":
                imdb_results = self.imdb_api.search_tv_series(query, year, limit)
                all_results.extend(imdb_results)
            
            if media_type == "movie" or media_type == "auto":
                imdb_results = self.imdb_api.search_movie(query, year, limit)
                all_results.extend(imdb_results)
        
        # Step 2: If IMDB fails or returns few results, try TMDB
        if len(all_results) < limit and self.tmdb_api:
            if media_type == "tv" or media_type == "auto":
                tmdb_results = self.tmdb_api.search_tv_series(query, year, limit - len(all_results))
                # Convert TMDB format to standard format
                for result in tmdb_results:
                    all_results.append({
                        'id': str(result['id']),
                        'title': result.get('name', ''),
                        'release_year': result.get('release_year', 'Unknown'),
                        'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                        'media_type': 'tv',
                        'source': 'tmdb',
                        'vote_average': result.get('vote_average', 0),
                        'vote_count': result.get('vote_count', 0)
                    })
            
            if media_type == "movie" or media_type == "auto":
                tmdb_results = self.tmdb_api.search_movies(query, year, limit - len(all_results))
                # Convert TMDB format to standard format
                for result in tmdb_results:
                    all_results.append({
                        'id': str(result['id']),
                        'title': result.get('title', ''),
                        'release_year': result.get('release_year', 'Unknown'),
                        'poster_url': f"https://image.tmdb.org/t/p/w500{result.get('poster_path', '')}" if result.get('poster_path') else '',
                        'media_type': 'movie',
                        'source': 'tmdb',
                        'vote_average': result.get('vote_average', 0),
                        'vote_count': result.get('vote_count', 0)
                    })
        
        # Remove duplicates based on title + year
        unique_results = self._remove_duplicates(all_results)
        
        log.info(f"🎯 Total unique results: {len(unique_results)}")
        return unique_results[:limit]

    def _remove_duplicates(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results based on title + year"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Create a unique key based on title and year
            key = f"{result['title'].lower()}_{result.get('release_year', 'unknown')}"
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results

    def get_media_details(self, source: str, media_id: str, media_type: str = 'movie') -> Optional[Dict]:
        """Get detailed media information from the appropriate source"""
        try:
            if source == 'imdb' and self.imdb_api:
                return self.imdb_api.get_movie_details(media_id)
            elif source == 'tmdb' and self.tmdb_api:
                if media_type == 'movie':
                    return self.tmdb_api.get_movie_details(int(media_id))
                else:
                    return self.tmdb_api.get_tv_series_details(int(media_id))
            
            return None
            
        except Exception as e:
            log.error(f"💥 Error getting details from {source} for {media_id}: {e}")
            return None

# Global instance
movie_searcher = MovieSearcher()