import requests
import time
import re
import json
from typing import Dict, Optional, List
from core.logger import log
from config import IMDB_BASE_URL, IMDB_SEARCH_URL, IMDB_IMAGE_BASE, USE_IMDB_FALLBACK

class IMDBAPI:
    """
    IMDB API integration with direct scraping as fallback
    """
    def __init__(self):
        self.base_url = IMDB_BASE_URL
        self.search_url = IMDB_SEARCH_URL
        self.image_base = IMDB_IMAGE_BASE
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        log.info("🎭 IMDB API client initialized")

    def search_movie(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for MOVIES only on IMDB"""
        if not USE_IMDB_FALLBACK:
            return []
            
        try:
            log.info(f"🔍 Searching IMDB for MOVIE: '{query}' (year: {year})")
            return self._search_imdb_direct(query, year, limit, tv=False)
            
        except Exception as e:
            log.error(f"💥 IMDB movie search failed for '{query}': {e}")
            return []

    def _search_imdb_direct(self, query: str, year: Optional[int] = None, limit: int = 10, tv: bool = False) -> List[Dict]:
        """Direct IMDB search using PyMovieDb"""
        try:
            from PyMovieDb import IMDB
            
            imdb = IMDB()
            search_results = imdb.search(query, year=year, tv=tv)
            
            # Handle PyMovieDb response format
            if isinstance(search_results, str):
                try:
                    search_results = json.loads(search_results)
                except json.JSONDecodeError:
                    log.error(f"❌ PyMovieDb returned invalid JSON string")
                    return []
            
            if not search_results or search_results.get('status') == 404 or not search_results.get('results'):
                log.warning(f"🔍 No IMDB results found for: '{query}'")
                return []
            
            results = []
            for item in search_results.get('results', [])[:limit]:
                if 'title' in item.get('url', ''):
                    # Extract year from URL or name if possible
                    release_year = self._extract_year_from_imdb_item(item, query)
                    
                    # Determine media type
                    media_type = self._determine_media_type(item, tv)
                    
                    results.append({
                        'id': item.get('id', ''),
                        'title': item.get('name', ''),
                        'release_year': release_year,
                        'poster_url': item.get('poster', ''),
                        'media_type': media_type,
                        'source': 'imdb',
                        'vote_average': 0,
                        'vote_count': 0
                    })
            
            log.info(f"✅ PyMovieDb found {len(results)} {'TV' if tv else 'movie'} results for: {query}")
            return results
            
        except Exception as e:
            log.error(f"💥 PyMovieDb search failed: {e}")
            return []

    def _extract_year_from_imdb_item(self, item: Dict, query: str) -> str:
        """Extract year from IMDB item data"""
        try:
            name = item.get('name', '')
            year_match = re.search(r'\((\d{4})\)', name)
            if year_match:
                return year_match.group(1)
            
            query_year_match = re.search(r'\b(19|20)\d{2}\b', query)
            if query_year_match:
                return query_year_match.group()
            
            return 'Unknown'
        except Exception:
            return 'Unknown'

    def _determine_media_type(self, item: Dict, tv_search: bool) -> str:
        """Determine media type from IMDB item"""
        try:
            item_type = item.get('type', '').lower()
            
            if tv_search:
                return 'tv'
            
            if any(tv_type in item_type for tv_type in ['tvseries', 'tvminiseries', 'tvepisode']):
                return 'tv'
            else:
                return 'movie'
                
        except Exception:
            return 'movie' if not tv_search else 'tv'

    def search_tv_series(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for TV SERIES only on IMDB"""
        if not USE_IMDB_FALLBACK:
            return []
            
        try:
            log.info(f"📺 Searching IMDB for TV SERIES: '{query}' (year: {year})")
            return self._search_imdb_direct(query, year, limit, tv=True)
            
        except Exception as e:
            log.error(f"💥 IMDB TV series search failed for '{query}': {e}")
            return []

    def unified_search(self, query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for both movies and TV series on IMDB"""
        if not USE_IMDB_FALLBACK:
            return []
            
        try:
            log.info(f"🔍 Unified IMDB search for: '{query}' (year: {year})")
            
            movies = self.search_movie(query, year, limit)
            tv_series = self.search_tv_series(query, year, limit)
            
            all_results = movies + tv_series
            
            # Remove duplicates based on ID
            seen_ids = set()
            unique_results = []
            for result in all_results:
                if result['id'] not in seen_ids:
                    seen_ids.add(result['id'])
                    unique_results.append(result)
            
            log.info(f"✅ Unified IMDB search found {len(unique_results)} total results")
            return unique_results[:limit]
            
        except Exception as e:
            log.error(f"💥 Unified IMDB search failed for '{query}': {e}")
            return []

    def get_movie_details(self, imdb_id: str) -> Optional[Dict]:
        """Get detailed movie information from IMDB - PRIMARY METHOD"""
        if not USE_IMDB_FALLBACK:
            return None
            
        try:
            log.info(f"📋 Fetching IMDB details for: {imdb_id}")
            
            # Try direct scraping first (most reliable)
            movie_data = self._scrape_imdb_direct(imdb_id)
            if movie_data:
                log.info(f"✅ Successfully scraped IMDB details for: {imdb_id}")
                return movie_data
            
            # Fallback to PyMovieDb
            log.info(f"🔄 Direct scraping failed, trying PyMovieDb for: {imdb_id}")
            from PyMovieDb import IMDB
            imdb = IMDB()
            movie_data = imdb.get_by_id(imdb_id)
            
            if isinstance(movie_data, str):
                try:
                    movie_data = json.loads(movie_data)
                except json.JSONDecodeError:
                    log.error(f"❌ PyMovieDb returned invalid JSON")
                    return None
            
            if not movie_data or movie_data.get('status') == 404:
                log.warning(f"❌ IMDB details not found for: {imdb_id}")
                return None
            
            return self._convert_imdb_to_standard_format(movie_data, imdb_id)
            
        except Exception as e:
            log.error(f"💥 IMDB details request failed for {imdb_id}: {e}")
            return None

    def _scrape_imdb_direct(self, imdb_id: str) -> Optional[Dict]:
        """Direct IMDB scraping - most reliable method"""
        try:
            url = f"https://www.imdb.com/title/{imdb_id}/"
            log.debug(f"🌐 Scraping IMDB URL: {url}")
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                log.error(f"❌ IMDB page not found: {url}")
                return None
            
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1')
            title = title_elem.text.strip() if title_elem else f"Movie {imdb_id}"
            
            # Extract year
            year_elem = soup.find('a', href=re.compile(r'releaseinfo|year=\d{4}'))
            year = year_elem.text.strip() if year_elem else 'Unknown'
            year_match = re.search(r'\d{4}', year)
            release_year = year_match.group() if year_match else 'Unknown'
            
            # Extract rating
            rating_elem = soup.find('span', class_=re.compile(r'rating'))
            if not rating_elem:
                rating_elem = soup.find('div', {'data-testid': 'hero-rating-bar__aggregate-rating'})
            rating = float(rating_elem.text.strip().split('/')[0]) if rating_elem else 0
            
            # Extract vote count
            vote_elem = soup.find('div', {'class': re.compile(r'rating')})
            vote_text = vote_elem.text if vote_elem else ''
            vote_match = re.search(r'([\d,]+)\s*user', vote_text)
            vote_count = int(vote_match.group(1).replace(',', '')) if vote_match else 0
            
            # EXTRACT GENRES - FIXED WITH BETTER SELECTORS
            genres = []
            try:
                log.debug("🎭 Attempting to extract genres from IMDB...")
                
                # Method 1: Try the new IMDB layout with data-testid
                genre_container = soup.find('div', {'data-testid': 'genres'})
                if genre_container:
                    log.debug("🎭 Found genre container with data-testid")
                    genre_links = genre_container.find_all('a', class_=re.compile(r'ipc-chip'))
                    genres = [link.find('span').text.strip() for link in genre_links if link.find('span')]
                    log.debug(f"🎭 Method 1 found genres: {genres}")
                
                # Method 2: Try ipc-chip-list__scroll-container
                if not genres:
                    genre_container = soup.find('div', class_='ipc-chip-list__scroll-container')
                    if genre_container:
                        log.debug("🎭 Found genre container with ipc-chip-list")
                        genre_spans = genre_container.find_all('span', class_='ipc-chip__text')
                        genres = [span.text.strip() for span in genre_spans if span.text.strip()]
                        log.debug(f"🎭 Method 2 found genres: {genres}")
                
                # Method 3: Try all ipc-chip elements
                if not genres:
                    genre_chips = soup.find_all('a', class_=re.compile(r'ipc-chip'))
                    for chip in genre_chips:
                        span = chip.find('span', class_='ipc-chip__text')
                        if span and span.text.strip():
                            genres.append(span.text.strip())
                    log.debug(f"🎭 Method 3 found genres: {genres}")
                
                # Method 4: Try the old-style genre links
                if not genres:
                    genre_links = soup.find_all('a', href=re.compile(r'/search/title\?genres='))
                    for link in genre_links:
                        genre_text = link.text.strip()
                        if genre_text and genre_text.lower() != 'genres':
                            genres.append(genre_text)
                    log.debug(f"🎭 Method 4 found genres: {genres}")
                
                # Method 5: Try meta tags as last resort
                if not genres:
                    meta_genre = soup.find('meta', {'property': 'genre'})
                    if meta_genre and meta_genre.get('content'):
                        genres = [g.strip() for g in meta_genre['content'].split(',')]
                        log.debug(f"🎭 Method 5 found genres: {genres}")
                
                # Clean and validate genres
                valid_genres = []
                for genre in genres:
                    if genre and len(genre) > 1 and genre.lower() not in ['genres', 'genre', 'plot', 'summary']:
                        # Remove any numbers or special characters
                        clean_genre = re.sub(r'[^a-zA-Z\s]', '', genre).strip()
                        if clean_genre and len(clean_genre) > 1:
                            valid_genres.append(clean_genre)
                
                # Limit to 3 unique genres
                genres = list(dict.fromkeys(valid_genres))[:3]
                
                log.info(f"🎭 Final extracted genres: {genres}")
                
            except Exception as e:
                log.warning(f"⚠️ Could not extract genres: {e}")
                genres = []
            
            # Extract description/overview
            desc_elem = soup.find('span', {'data-testid': 'plot-l'})
            overview = desc_elem.text.strip() if desc_elem else ''
            
            # Extract poster image
            poster_elem = soup.find('img', {'class': 'ipc-image'})
            poster_url = poster_elem.get('src') if poster_elem else ''
            
            # Extract runtime
            runtime_elem = soup.find('li', {'data-testid': 'title-techspec_runtime'})
            runtime_text = runtime_elem.text if runtime_elem else ''
            runtime_match = re.search(r'(\d+)\s*min', runtime_text)
            runtime = int(runtime_match.group(1)) if runtime_match else 0
            
            # Determine media type
            media_type = 'movie'
            if soup.find('a', href=re.compile(r'title_type=tv_series')):
                media_type = 'tv'
            
            # Build movie data
            movie_data = {
                'name': title,
                'description': overview,
                'rating': {'ratingValue': rating, 'ratingCount': vote_count},
                'genre': genres,
                'datePublished': release_year,
                'poster': poster_url,
                'duration': f'PT{runtime//60}H{runtime%60}M' if runtime else '',
                'type': media_type
            }
            
            return self._convert_imdb_to_standard_format(movie_data, imdb_id)
            
        except Exception as e:
            log.error(f"💥 Direct IMDB scraping failed for {imdb_id}: {e}")
            return None


    def _convert_imdb_to_standard_format(self, imdb_data: dict, imdb_id: str) -> Dict:
        """Convert IMDB data to our standard movie format"""
        try:
            # Extract rating
            rating_data = imdb_data.get('rating', {})
            rating_value = rating_data.get('ratingValue')
            vote_count = rating_data.get('ratingCount')
            
            # Extract genres with debug logging
            genres = imdb_data.get('genre', [])
            log.debug(f"🎭 Raw genres from IMDB: {genres} (type: {type(genres)})")
            
            if isinstance(genres, str):
                genres = [genre.strip() for genre in genres.split(',')]
            
            log.debug(f"🎭 Processed genres for poster: {genres}")
            
            # Extract release year
            release_date = imdb_data.get('datePublished', '')
            release_year = release_date[:4] if release_date else 'Unknown'
            
            # Extract duration
            duration = imdb_data.get('duration', '')
            runtime = self._parse_duration_to_minutes(duration)
            
            # Extract overview
            overview = imdb_data.get('description') or imdb_data.get('overview') or ''
            
            # Determine media type
            media_type = imdb_data.get('type', 'movie').lower()
            if 'tv' in media_type or 'series' in media_type:
                media_type = 'tv'
            else:
                media_type = 'movie'
            
            # EXTRACT LANGUAGE - ADD THIS SECTION
            language = imdb_data.get('inLanguage', 'en')
            if isinstance(language, list):
                language = language[0] if language else 'en'
            if not language or language == 'None':
                language = 'en'
            
            # Build standardized movie data
            standardized_data = {
                'movie_id': imdb_id,
                'title': imdb_data.get('name', 'Unknown Title'),
                'original_title': imdb_data.get('alternateName', ''),
                'overview': overview,
                'tmdb_rating': float(rating_value) if rating_value else 0,
                'vote_count': int(vote_count) if vote_count else 0,
                'genres': genres,
                'release_date': release_date,
                'release_year': release_year,
                'poster_path': '',
                'poster_url': imdb_data.get('poster', ''),
                'runtime': runtime,
                'popularity': 0,
                'original_language': language,
                'language': language,  # required by image generator
                'media_type': media_type,
                'source': 'imdb',
                'cached_at': time.time()
            }
            
            log.info(f"✅ Converted IMDB data for: {standardized_data['title']} ({media_type})")
            return standardized_data
            
        except Exception as e:
            log.error(f"💥 Error converting IMDB data: {e}")
            return None

    def _parse_duration_to_minutes(self, duration: str) -> int:
        """Convert PT1H30M format to minutes"""
        try:
            if not duration:
                return 0
                
            hours_match = re.search(r'(\d+)H', duration)
            minutes_match = re.search(r'(\d+)M', duration)
            
            hours = int(hours_match.group(1)) if hours_match else 0
            minutes = int(minutes_match.group(1)) if minutes_match else 0
            
            return hours * 60 + minutes
        except Exception:
            return 0

    def get_movie_by_title(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search and get full movie details by title using IMDB"""
        if not USE_IMDB_FALLBACK:
            return None
            
        try:
            log.info(f"🎯 IMDB get by title: '{title}' (year: {year})")
            
            search_results = self.unified_search(title, year, limit=1)
            if not search_results:
                return None
            
            first_result = search_results[0]
            imdb_id = first_result.get('id')
            
            if imdb_id:
                return self.get_movie_details(imdb_id)
            
            return None
            
        except Exception as e:
            log.error(f"💥 IMDB get by title failed for '{title}': {e}")
            return None

# Global IMDB API instance
imdb_api = IMDBAPI()
