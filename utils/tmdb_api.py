import requests
import time
from typing import Dict, Optional, List
from config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_BASE
from core.logger import log

class TMDBAPI:
    def __init__(self):
        self.api_key = TMDB_API_KEY
        self.base_url = TMDB_BASE_URL
        self.image_base = TMDB_IMAGE_BASE
        self.params = {"api_key": self.api_key, "language": "en-US"}
        
        self.genre_cache = None
        self.last_genre_fetch = 0
        
        self._validate_api_key()
        log.info("🎬 TMDB API client initialized")
    
    def _validate_api_key(self):
        """Validate TMDB API key on startup"""
        try:
            test_url = f"{self.base_url}/configuration"
            response = requests.get(test_url, params=self.params, timeout=10)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key is INVALID")
            elif response.status_code == 200:
                log.success("✅ TMDB API Key validated successfully")
            else:
                log.warning(f"⚠️ TMDB API validation returned status: {response.status_code}")
                
        except Exception as e:
            log.error(f"💥 TMDB API validation failed: {e}")
    
    def _get_genres(self) -> Dict[int, str]:
        """Get and cache movie genres from TMDB"""
        current_time = time.time()
        
        if (self.genre_cache and 
            current_time - self.last_genre_fetch < 86400):
            return self.genre_cache
        
        try:
            url = f"{self.base_url}/genre/movie/list"
            response = requests.get(url, params=self.params, timeout=10)
            
            if response.status_code == 401:
                return self._get_fallback_genres()
                
            response.raise_for_status()
            
            genres_data = response.json()
            self.genre_cache = {genre["id"]: genre["name"] for genre in genres_data["genres"]}
            self.last_genre_fetch = current_time
            
            log.debug(f"✅ Fetched {len(self.genre_cache)} genres from TMDB")
            return self.genre_cache
            
        except Exception as e:
            log.error(f"💥 Error fetching genres: {e}")
            return self._get_fallback_genres()
    
    def _get_fallback_genres(self) -> Dict[int, str]:
        """Fallback genre list if TMDB fails"""
        return {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
        }
    
    def search_multiple_movies(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for multiple movies and return top results"""
        if not query or not query.strip():
            return []
        
        try:
            params = self.params.copy()
            params.update({
                "query": query.strip(),
                "include_adult": False,
                "page": 1
            })
            
            if year:
                params["year"] = year
            
            url = f"{self.base_url}/search/movie"
            log.debug(f"🔍 Searching TMDB for multiple: '{query}' (year: {year})")
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key rejected")
                return []
                
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                log.warning(f"🔍 No TMDB results found for: '{query}'")
                return []
            
            # Sort by popularity and limit results
            sorted_results = sorted(results, key=lambda x: x.get("vote_count", 0), reverse=True)
            limited_results = sorted_results[:limit]
            
            # Add basic details to each result
            for result in limited_results:
                result["release_year"] = result.get("release_date", "")[:4] if result.get("release_date") else "Unknown"
                result["display_title"] = f"{result['title']} ({result['release_year']})"
            
            log.info(f"✅ Found {len(limited_results)} movies for: {query}")
            return limited_results
            
        except Exception as e:
            log.error(f"💥 TMDB multiple search failed for '{query}': {e}")
            return []
    
    def search_movie(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a single movie by title"""
        results = self.search_multiple_movies(query, year, limit=1)
        return results[0] if results else None
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed information about a movie"""
        try:
            url = f"{self.base_url}/movie/{movie_id}"
            
            log.debug(f"📋 Fetching details for movie ID: {movie_id}")
            
            response = requests.get(url, params=self.params, timeout=15)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key rejected")
                return None
                
            response.raise_for_status()
            
            movie_data = response.json()
            
            # Process genres
            genres = self._get_genres()
            genre_names = [genres.get(genre_id, "Unknown") for genre_id in movie_data.get("genre_ids", [])]
            if not genre_names and "genres" in movie_data:
                genre_names = [genre["name"] for genre in movie_data["genres"]]
            
            # Extract release year
            release_date = movie_data.get("release_date", "")
            release_year = release_date[:4] if release_date else "Unknown"
            
            # Build normalized movie data
            normalized_data = {
                "movie_id": movie_id,
                "title": movie_data.get("title", "Unknown Title"),
                "original_title": movie_data.get("original_title", ""),
                "overview": movie_data.get("overview", ""),
                "tmdb_rating": round(movie_data.get("vote_average", 0), 1),
                "vote_count": movie_data.get("vote_count", 0),
                "genres": genre_names,
                "release_date": release_date,
                "release_year": release_year,
                "poster_path": movie_data.get("poster_path", ""),
                "poster_url": f"{self.image_base}{movie_data.get('poster_path', '')}" if movie_data.get("poster_path") else "",
                "runtime": movie_data.get("runtime", 0),
                "popularity": movie_data.get("popularity", 0),
                "original_language": movie_data.get("original_language", "en"),  # Added language
                "cached_at": time.time()
            }
            
            log.info(f"✅ Fetched details for: {normalized_data['title']} ({release_year})")
            return normalized_data
            
        except Exception as e:
            log.error(f"💥 TMDB details request failed for movie {movie_id}: {e}")
            return None
    
    def get_movie_by_title(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search and get full movie details by title"""
        search_result = self.search_movie(title, year)
        if not search_result:
            if year:
                log.info(f"🔄 Retrying search without year: {title}")
                search_result = self.search_movie(title)
            
            if not search_result:
                return None
        
        movie_id = search_result.get("id")
        if movie_id:
            return self.get_movie_details(movie_id)
        
        return None
    
def get_movie_by_title_with_fallback(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
    """Search for movie with OMDb fallback"""
    # Try TMDB first
    movie_data = self.get_movie_by_title(title, year)
    if movie_data:
        return movie_data
    
    # TMDB failed, try OMDb
    log.info(f"🔄 TMDB failed, trying OMDb for: {title}")
    from utils.omdb_api import omdb_api
    return omdb_api.search_movie(title, year)

def get_tv_series_by_title_with_fallback(self, title: str) -> Optional[Dict]:
    """Search for TV series with OMDb fallback"""
    # Try TMDB first
    series_data = self.get_tv_series_by_title(title)
    if series_data:
        return series_data
    
    # TMDB failed, try OMDb
    log.info(f"🔄 TMDB failed, trying OMDb for TV series: {title}")
    from utils.omdb_api import omdb_api
    return omdb_api.search_tv_series(title)

# Global TMDB API instance
tmdb_api = TMDBAPI()