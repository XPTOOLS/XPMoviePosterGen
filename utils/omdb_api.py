import requests
from typing import Dict, Optional, List
from core.logger import log
from config import OMDB_API_KEY, OMDB_BASE_URL

class OMDbAPI:
    def __init__(self):
        self.api_key = OMDB_API_KEY
        self.base_url = OMDB_BASE_URL.rstrip('/')  # Remove trailing slash if present
        log.info("🎬 OMDb API client initialized")
    
    def search_movie(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for movie on OMDb"""
        try:
            params = {
                "apikey": self.api_key,
                "s": query,
                "type": "movie",
                "r": "json"
            }
            
            if year:
                params["y"] = year
            
            log.debug(f"🔍 Searching OMDb for movie: '{query}'")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            log.debug(f"OMDb response: {data}")
            
            if data.get("Response") == "True" and data.get("Search"):
                # Return the first result
                first_result = data["Search"][0]
                log.info(f"✅ OMDb found movie: {first_result.get('Title')}")
                
                # Get full details
                return self.get_by_imdb_id(first_result["imdbID"])
            else:
                log.warning(f"🔍 No OMDb results found for movie: '{query}' - {data.get('Error', 'Unknown error')}")
                return None
                
        except Exception as e:
            log.error(f"💥 OMDb movie search failed for '{query}': {e}")
            return None
    
    def search_tv_series(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for TV series on OMDb"""
        try:
            params = {
                "apikey": self.api_key,
                "s": query,
                "type": "series",
                "r": "json"
            }
            
            if year:
                params["y"] = year
            
            log.debug(f"📺 Searching OMDb for TV series: '{query}'")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            log.debug(f"OMDb TV response: {data}")
            
            if data.get("Response") == "True" and data.get("Search"):
                # Return the first result
                first_result = data["Search"][0]
                log.info(f"✅ OMDb found TV series: {first_result.get('Title')}")
                
                # Get full details
                return self.get_by_imdb_id(first_result["imdbID"])
            else:
                log.warning(f"🔍 No OMDb results found for TV series: '{query}' - {data.get('Error', 'Unknown error')}")
                return None
                
        except Exception as e:
            log.error(f"💥 OMDb TV series search failed for '{query}': {e}")
            return None
    
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Get full details by IMDb ID"""
        try:
            params = {
                "apikey": self.api_key,
                "i": imdb_id,
                "plot": "full",
                "r": "json"
            }
            
            log.debug(f"📋 Fetching OMDb details for: {imdb_id}")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("Response") == "True":
                normalized_data = self._normalize_omdb_data(data)
                log.info(f"✅ OMDb details fetched for: {normalized_data['title']}")
                return normalized_data
            else:
                log.warning(f"❌ OMDb details not found for: {imdb_id} - {data.get('Error', 'Unknown error')}")
                return None
                
        except Exception as e:
            log.error(f"💥 OMDb details request failed for {imdb_id}: {e}")
            return None
    
    def _normalize_omdb_data(self, omdb_data: Dict) -> Dict:
        """Convert OMDb data to our standard format"""
        try:
            # Extract year from released date or Year field
            released = omdb_data.get("Released", "")
            year_field = omdb_data.get("Year", "")
            
            if released and released != "N/A":
                release_year = released.split()[-1] if released else ""
            elif year_field and year_field != "N/A":
                release_year = year_field.split('–')[0]  # Handle ranges like "2010-2015"
            else:
                release_year = "Unknown"
            
            # Process genres
            genres = []
            genre_field = omdb_data.get("Genre", "")
            if genre_field and genre_field != "N/A":
                genres = [genre.strip() for genre in genre_field.split(",")]
            
            # Process rating
            rating_str = omdb_data.get("imdbRating", "0")
            try:
                rating = float(rating_str) if rating_str != "N/A" else 0
            except:
                rating = 0
            
            # Process votes
            votes_str = omdb_data.get("imdbVotes", "0")
            try:
                votes = int(votes_str.replace(",", "")) if votes_str != "N/A" else 0
            except:
                votes = 0
            
            # Determine if it's a TV series
            is_tv_series = omdb_data.get("Type") == "series"
            
            # Get poster URL
            poster_url = omdb_data.get("Poster", "")
            if poster_url == "N/A":
                poster_url = ""
            
            normalized_data = {
                "movie_id": omdb_data.get("imdbID", ""),
                "title": omdb_data.get("Title", "Unknown"),
                "original_title": omdb_data.get("Title", ""),
                "overview": omdb_data.get("Plot", "") if omdb_data.get("Plot") != "N/A" else "",
                "tmdb_rating": round(rating, 1),
                "vote_count": votes,
                "genres": genres,
                "release_date": omdb_data.get("Released", "") if omdb_data.get("Released") != "N/A" else "",
                "release_year": release_year,
                "poster_url": poster_url,
                "runtime": omdb_data.get("Runtime", "") if omdb_data.get("Runtime") != "N/A" else "",
                "original_language": "en",  # OMDb doesn't provide this
                "is_tv_series": is_tv_series,
                "source": "omdb"
            }
            
            return normalized_data
            
        except Exception as e:
            log.error(f"💥 Error normalizing OMDb data: {e}")
            # Return basic data as fallback
            return {
                "movie_id": omdb_data.get("imdbID", ""),
                "title": omdb_data.get("Title", "Unknown"),
                "tmdb_rating": 0,
                "genres": [],
                "release_year": "Unknown",
                "poster_url": "",
                "is_tv_series": omdb_data.get("Type") == "series",
                "source": "omdb"
            }

# Global OMDb API instance
omdb_api = OMDbAPI()