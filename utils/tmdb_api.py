import requests
import time
import re
from typing import Dict, Optional, List, Tuple
from config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_BASE, USE_IMDB_FALLBACK
from core.logger import log

class TMDBAPI:
    def __init__(self):
        self.api_key = TMDB_API_KEY
        self.base_url = TMDB_BASE_URL
        self.image_base = TMDB_IMAGE_BASE
        self.params = {"api_key": self.api_key, "language": "en-US"}
        
        self.genre_cache = None
        self.tv_genre_cache = None
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

    def _extract_year_from_query(self, query: str) -> Tuple[str, Optional[int]]:
        """Extract year from query string and return cleaned query + year"""
        # Patterns to match years: (2014), 2014, [2014], etc.
        year_patterns = [
            r'\((\d{4})\)',  # (2014)
            r'\[(\d{4})\]',  # [2014]
            r'\s+(\d{4})\s*$',  # 2014 at the end
            r'\s+\((\d{4})\)\s*$',  # (2014) at the end
        ]
        
        cleaned_query = query.strip()
        year = None
        
        for pattern in year_patterns:
            match = re.search(pattern, cleaned_query)
            if match:
                year = int(match.group(1))
                # Remove the year part from the query
                cleaned_query = re.sub(pattern, '', cleaned_query).strip()
                break
        
        return cleaned_query, year

    def _get_genres(self, media_type: str = "movie") -> Dict[int, str]:
        """Get and cache genres from TMDB for movies or TV shows"""
        current_time = time.time()
        
        cache_attr = "genre_cache" if media_type == "movie" else "tv_genre_cache"
        cache = getattr(self, cache_attr)
        
        if cache and current_time - self.last_genre_fetch < 86400:
            return cache
        
        try:
            endpoint = "genre/movie/list" if media_type == "movie" else "genre/tv/list"
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=self.params, timeout=10)
            
            if response.status_code == 401:
                return self._get_fallback_genres(media_type)
                
            response.raise_for_status()
            
            genres_data = response.json()
            genre_cache = {genre["id"]: genre["name"] for genre in genres_data["genres"]}
            
            # Update the appropriate cache
            setattr(self, cache_attr, genre_cache)
            self.last_genre_fetch = current_time
            
            log.debug(f"✅ Fetched {len(genre_cache)} {media_type} genres from TMDB")
            return genre_cache
            
        except Exception as e:
            log.error(f"💥 Error fetching {media_type} genres: {e}")
            return self._get_fallback_genres(media_type)
    
    def _get_fallback_genres(self, media_type: str = "movie") -> Dict[int, str]:
        """Fallback genre list if TMDB fails"""
        if media_type == "tv":
            return {
                10759: "Action & Adventure", 16: "Animation", 35: "Comedy",
                80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
                10762: "Kids", 9648: "Mystery", 10763: "News", 10764: "Reality",
                10765: "Sci-Fi & Fantasy", 10766: "Soap", 10767: "Talk",
                10768: "War & Politics", 37: "Western"
            }
        else:
            return {
                28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
                80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
                14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
                9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
                10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
            }

    # KEEP THE OLD METHOD NAME FOR BACKWARD COMPATIBILITY
    def search_multiple_movies(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for multiple movies and return top results (backward compatibility)"""
        log.warning(f"🔄 Using legacy search_multiple_movies for: '{query}'")
        return self.search_movies(query, year, limit)

    def search_movies(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for movies with enhanced matching"""
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
            log.debug(f"🎬 Searching TMDB movies: '{query}' (year: {year})")
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key rejected")
                return []
                
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                log.warning(f"🔍 No movie results found for: '{query}'")
                return []
            
            # Enhanced sorting: prioritize exact title matches
            def sort_key(movie):
                score = movie.get("vote_count", 0)
                title = movie.get("title", "").lower()
                original_title = movie.get("original_title", "").lower()
                query_lower = query.lower()
                
                # Boost score for exact title matches
                if title == query_lower or original_title == query_lower:
                    score += 1000
                # Boost for partial matches
                elif query_lower in title or query_lower in original_title:
                    score += 500
                # Boost for year matches
                if year:
                    release_year = movie.get("release_date", "")[:4]
                    if release_year == str(year):
                        score += 300
                
                return score
            
            sorted_results = sorted(results, key=sort_key, reverse=True)
            limited_results = sorted_results[:limit]
            
            # Add display information
            for result in limited_results:
                result["release_year"] = result.get("release_date", "")[:4] if result.get("release_date") else "Unknown"
                result["display_title"] = f"{result['title']} ({result['release_year']})"
                result["media_type"] = "movie"
            
            log.info(f"✅ Found {len(limited_results)} movies for: {query}")
            return limited_results
            
        except Exception as e:
            log.error(f"💥 TMDB movie search failed for '{query}': {e}")
            return []

    def search_tv_series(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for TV series"""
        if not query or not query.strip():
            return []
        
        try:
            params = self.params.copy()
            params.update({
                "query": query.strip(),
                "include_adult": False,
                "page": 1
            })
            
            # For TV series, we can use first_air_date_year instead of year
            if year:
                params["first_air_date_year"] = year
            
            url = f"{self.base_url}/search/tv"
            log.debug(f"📺 Searching TMDB TV series: '{query}' (year: {year})")
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key rejected")
                return []
                
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                log.warning(f"🔍 No TV series results found for: '{query}'")
                return []
            
            # Enhanced sorting for TV series
            def sort_key(tv):
                score = tv.get("vote_count", 0)
                title = tv.get("name", "").lower()
                original_title = tv.get("original_name", "").lower()
                query_lower = query.lower()
                
                # Boost score for exact title matches
                if title == query_lower or original_title == query_lower:
                    score += 1000
                # Boost for partial matches
                elif query_lower in title or query_lower in original_title:
                    score += 500
                # Boost for year matches
                if year:
                    first_air_year = tv.get("first_air_date", "")[:4]
                    if first_air_year == str(year):
                        score += 300
                
                return score
            
            sorted_results = sorted(results, key=sort_key, reverse=True)
            limited_results = sorted_results[:limit]
            
            # Add display information
            for result in limited_results:
                result["release_year"] = result.get("first_air_date", "")[:4] if result.get("first_air_date") else "Unknown"
                result["display_title"] = f"{result['name']} ({result['release_year']})"
                result["media_type"] = "tv"
            
            log.info(f"✅ Found {len(limited_results)} TV series for: {query}")
            return limited_results
            
        except Exception as e:
            log.error(f"💥 TMDB TV series search failed for '{query}': {e}")
            return []

    def unified_search(self, query: str, year: Optional[int] = None, limit: int = 5) -> List[Dict]:
        """Search both movies and TV series, return combined results"""
        cleaned_query, extracted_year = self._extract_year_from_query(query)
        use_year = year or extracted_year
        
        log.info(f"🔍 Unified search for: '{cleaned_query}' (year: {use_year})")
        
        # Search both movies and TV series in parallel (conceptually)
        movies = self.search_movies(cleaned_query, use_year, limit)
        tv_series = self.search_tv_series(cleaned_query, use_year, limit)
        
        # Combine and prioritize results
        all_results = []
        
        # Add movies with type identifier
        for movie in movies:
            movie["search_rank"] = len(all_results) + 1
            all_results.append(movie)
        
        # Add TV series with type identifier
        for tv in tv_series:
            tv["search_rank"] = len(all_results) + 1
            all_results.append(tv)
        
        # Sort by combined popularity score
        def combined_score(item):
            score = item.get("vote_count", 0) + item.get("popularity", 0)
            # Boost exact matches
            title = item.get("title") or item.get("name", "").lower()
            if title.lower() == cleaned_query.lower():
                score += 1000
            return score
        
        all_results.sort(key=combined_score, reverse=True)
        
        log.info(f"🎯 Unified search found {len(all_results)} total results")
        return all_results[:limit]

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
            genres = self._get_genres("movie")
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
                "original_language": movie_data.get("original_language", "en"),
                "media_type": "movie",
                "cached_at": time.time()
            }
            
            log.info(f"✅ Fetched movie details: {normalized_data['title']} ({release_year})")
            return normalized_data
            
        except Exception as e:
            log.error(f"💥 TMDB movie details request failed for {movie_id}: {e}")
            return None

    def get_tv_series_details(self, tv_id: int) -> Optional[Dict]:
        """Get detailed information about a TV series"""
        try:
            url = f"{self.base_url}/tv/{tv_id}"
            
            log.debug(f"📋 Fetching details for TV series ID: {tv_id}")
            
            response = requests.get(url, params=self.params, timeout=15)
            
            if response.status_code == 401:
                log.error("❌ TMDB API Key rejected")
                return None
                
            response.raise_for_status()
            
            tv_data = response.json()
            
            # Process genres
            genres = self._get_genres("tv")
            genre_names = [genres.get(genre_id, "Unknown") for genre_id in tv_data.get("genre_ids", [])]
            if not genre_names and "genres" in tv_data:
                genre_names = [genre["name"] for genre in tv_data["genres"]]
            
            # Extract release year
            first_air_date = tv_data.get("first_air_date", "")
            release_year = first_air_date[:4] if first_air_date else "Unknown"
            
            # Build normalized TV series data
            normalized_data = {
                "movie_id": tv_id,  # Using same field name for consistency
                "title": tv_data.get("name", "Unknown Title"),
                "original_title": tv_data.get("original_name", ""),
                "overview": tv_data.get("overview", ""),
                "tmdb_rating": round(tv_data.get("vote_average", 0), 1),
                "vote_count": tv_data.get("vote_count", 0),
                "genres": genre_names,
                "release_date": first_air_date,
                "release_year": release_year,
                "poster_path": tv_data.get("poster_path", ""),
                "poster_url": f"{self.image_base}{tv_data.get('poster_path', '')}" if tv_data.get("poster_path") else "",
                "runtime": tv_data.get("episode_run_time", [0])[0] if tv_data.get("episode_run_time") else 0,
                "popularity": tv_data.get("popularity", 0),
                "original_language": tv_data.get("original_language", "en"),
                "media_type": "tv",
                "number_of_seasons": tv_data.get("number_of_seasons", 0),
                "number_of_episodes": tv_data.get("number_of_episodes", 0),
                "status": tv_data.get("status", ""),
                "cached_at": time.time()
            }
            
            log.info(f"✅ Fetched TV series details: {normalized_data['title']} ({release_year})")
            return normalized_data
            
        except Exception as e:
            log.error(f"💥 TMDB TV series details request failed for {tv_id}: {e}")
            return None

    def get_media_by_title(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search and get full details by title (supports both movies and TV series)"""
        cleaned_query, extracted_year = self._extract_year_from_query(title)
        use_year = year or extracted_year
        
        log.info(f"🎯 Smart search for: '{cleaned_query}' (year: {use_year})")
        
        # First try unified search to find the best match
        search_results = self.unified_search(cleaned_query, use_year, limit=3)
        
        if not search_results:
            log.warning(f"❌ No results found for: '{cleaned_query}'")
            return None
        
        # Get the best match
        best_match = search_results[0]
        media_type = best_match.get("media_type", "movie")
        media_id = best_match.get("id")
        
        if media_type == "movie":
            return self.get_movie_details(media_id)
        else:  # tv
            return self.get_tv_series_details(media_id)

    def get_media_by_title_with_fallback(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search and get full details by title with IMDB fallback"""
        try:
            # First try TMDB
            movie_data = self.get_media_by_title(title, year)
            if movie_data:
                return movie_data
            
            # TMDB failed, try IMDB fallback
            if USE_IMDB_FALLBACK:
                log.info(f"🔄 TMDB failed, trying IMDB fallback for: '{title}'")
                from utils.imdb_api import imdb_api
                imdb_data = imdb_api.get_movie_by_title(title, year)
                
                if imdb_data:
                    log.info(f"✅ IMDB fallback successful for: {imdb_data['title']}")
                    return imdb_data
            
            log.warning(f"❌ No results found in TMDB or IMDB for: '{title}'")
            return None
            
        except Exception as e:
            log.error(f"💥 Error in media search with fallback for '{title}': {e}")
            return None

    # KEEP THE OLD METHOD FOR BACKWARD COMPATIBILITY
    def search_movie(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a single movie by title (backward compatibility)"""
        results = self.search_multiple_movies(query, year, limit=1)
        return results[0] if results else None

    def get_movie_by_title(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search and get full movie details by title (backward compatibility)"""
        log.warning(f"🔄 Using legacy get_movie_by_title for: '{title}'")
        return self.get_media_by_title(title, year)
    
def get_media_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
    """Get media details by IMDB ID (works for both movies and TV)"""
    try:
        log.info(f"🔍 Searching TMDB by IMDB ID: {imdb_id}")
        
        # First try as movie
        url = f"{self.base_url}/find/{imdb_id}"
        params = self.params.copy()
        params["external_source"] = "imdb_id"
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 401:
            log.error("❌ TMDB API Key rejected")
            return None
            
        response.raise_for_status()
        
        data = response.json()
        
        # Check movie results first
        movie_results = data.get("movie_results", [])
        if movie_results:
            movie_data = movie_results[0]
            movie_id = movie_data.get("id")
            log.success(f"✅ Found movie via IMDB ID: {imdb_id} -> TMDB ID: {movie_id}")
            return self.get_movie_details(movie_id)
        
        # Check TV results
        tv_results = data.get("tv_results", [])
        if tv_results:
            tv_data = tv_results[0]
            tv_id = tv_data.get("id")
            log.success(f"✅ Found TV series via IMDB ID: {imdb_id} -> TMDB ID: {tv_id}")
            return self.get_tv_series_details(tv_id)
        
        # Check TV episode results (if it's a specific episode)
        tv_episode_results = data.get("tv_episode_results", [])
        if tv_episode_results:
            # For episodes, get the parent series
            episode_data = tv_episode_results[0]
            tv_id = episode_data.get("show_id")
            if tv_id:
                log.success(f"✅ Found TV episode via IMDB ID: {imdb_id} -> Series TMDB ID: {tv_id}")
                return self.get_tv_series_details(tv_id)
        
        log.warning(f"❌ No media found for IMDB ID: {imdb_id}")
        return None
        
    except Exception as e:
        log.error(f"💥 Error searching TMDB by IMDB ID {imdb_id}: {e}")
        return None

# Global TMDB API instance
tmdb_api = TMDBAPI()
