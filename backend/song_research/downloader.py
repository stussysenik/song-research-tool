import re
import requests
from urllib.parse import urlparse
import os
import yt_dlp
import logging
from .metadata_enricher import MetadataEnricher
from .download_verification import DownloadVerifier
import asyncio
import uuid
import sys
import json
import time
import unicodedata
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)

# Simple implementation of progress tracking classes
class SongStatus(Enum):
    """Status of a song download."""
    QUEUED = auto()
    SEARCHING = auto()
    DOWNLOADING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()

class SongProgress:
    """Progress information for a single song."""
    def __init__(self, song_name: str, status: SongStatus = SongStatus.QUEUED, progress: float = 0, 
                 message: str = "", error: str = None):
        self.song_name = song_name
        self.status = status
        self.progress = progress
        self.message = message
        self.error = error
        self.updated_at = time.time()

class ProgressTracker:
    """Tracks the progress of song downloads."""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.songs = {}
        
    def add_song(self, song_id: str, song_name: str, status: SongStatus = SongStatus.QUEUED, 
                 message: str = "Queued for download"):
        """Add a song to track."""
        self.songs[song_id] = SongProgress(song_name, status, 0, message)
        
    def update_progress(self, song_id: str, status: SongStatus = None, progress: float = None, 
                        message: str = None, error: str = None):
        """Update the progress of a song."""
        if song_id not in self.songs:
            self.add_song(song_id, song_id, SongStatus.QUEUED)
            
        song_progress = self.songs[song_id]
        
        if status is not None:
            song_progress.status = status
        if progress is not None:
            song_progress.progress = progress
        if message is not None:
            song_progress.message = message
        if error is not None:
            song_progress.error = error
            
        song_progress.updated_at = time.time()
        
    def get_progress(self, song_id: str = None):
        """Get progress information for one or all songs."""
        if song_id is not None:
            return self.songs.get(song_id)
        return self.songs

def generate_song_id(song_title: str, artist: Optional[str] = None) -> str:
    """Generate a unique ID for a song based on title and artist."""
    # Normalize text to handle special characters
    title = unicodedata.normalize('NFKD', song_title).encode('ascii', 'ignore').decode('ascii').lower()
    
    # Clean up title to keep only alphanumeric characters
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    if artist:
        artist = unicodedata.normalize('NFKD', artist).encode('ascii', 'ignore').decode('ascii').lower()
        artist = re.sub(r'[^a-z0-9\s]', '', artist)
        artist = re.sub(r'\s+', ' ', artist).strip()
        combined = f"{artist} - {title}"
    else:
        combined = title
    
    # Use hash to generate a consistent ID
    return hashlib.md5(combined.encode()).hexdigest()[:10]

class SongDownloader:
    def __init__(self, progress_tracker=None, output_dir='playlist', platform_preference=None):
        self.output_dir = output_dir
        self.progress_tracker = progress_tracker
        self.metadata_enricher = MetadataEnricher()
        self.download_verifier = DownloadVerifier()
        self.platform_preference = platform_preference
    
    def process_song(self, song_data):
        """Process a song for download, handling both URLs and text queries."""
        if isinstance(song_data, str) and self._is_valid_url(song_data):
            return self.download_from_url(song_data)
        
        # Handle traditional title+artist format
        title, artist = self._parse_song_info(song_data)
        return self.download_song(title, artist)
    
    def _parse_song_info(self, song_data):
        """Parse song data to extract title and artist."""
        # Handle dictionary input
        if isinstance(song_data, dict):
            return song_data.get('title', ''), song_data.get('artist', '')
            
        # Handle string input with common separators
        if isinstance(song_data, str):
            # Try different separators: "-", "by", ":", etc.
            for separator in [' - ', ' by ', ': ']:
                if separator in song_data:
                    parts = song_data.split(separator, 1)
                    if len(parts) == 2:
                        # Determine which part is likely the artist vs title
                        # This is a simplistic approach and could be improved
                        return parts[0].strip(), parts[1].strip()
            
            # If no separator found, return as title with unknown artist
            return song_data.strip(), "Unknown Artist"
            
        # Handle tuple or list input (title, artist)
        if isinstance(song_data, (tuple, list)) and len(song_data) >= 2:
            return song_data[0], song_data[1]
            
        # Default fallback
        return str(song_data), "Unknown Artist"
    
    def _is_valid_url(self, text):
        """Check if the provided text is a valid URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def get_ydl_opts(self, output_template, download=True):
        """Get yt-dlp options with the given output template."""
        return {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'default_search': 'auto',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': not download,  # Just extract info, don't download if download=False
            'skip_download': not download,  # Skip download if download=False
        }
    
    def download_from_url(self, url):
        """Download song directly from URL without search."""
        # Direct URL download is more reliable than search
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        
        ydl_opts = self.get_ydl_opts(output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'title': info.get('title', 'Unknown'),
                    'artist': info.get('uploader', 'Unknown'),
                    'success': True,
                    'filepath': f"{info.get('title', 'Unknown')} - {info.get('uploader', 'Unknown')}.mp3"
                }
        except Exception as e:
            return {
                'title': url,
                'artist': 'Unknown',
                'success': False,
                'error': str(e)
            }

    def _clean_for_search(self, text):
        """Clean text for better search results."""
        # Remove unnecessary words and characters that might affect search
        cleaned = text.lower()
        # Remove text in parentheses (often contains "feat." or "ft." which can cause matching issues)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)
        # Remove text in brackets
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
        # Remove common noise words
        for noise in ['official', 'video', 'audio', 'lyrics', 'music', 'hd', '4k', 'full']:
            cleaned = re.sub(rf'\b{noise}\b', '', cleaned)
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def download_song(self, title, artist):
        """Download a song using a multi-strategy approach."""
        # Clean inputs for better search results
        clean_title = self._clean_for_search(title)
        clean_artist = self._clean_for_search(artist)
        
        # Try different search strategies in order of reliability
        result = None
        
        # Determine search order based on platform preference
        search_strategies = []
        
        if self.platform_preference == 'soundcloud':
            # Prioritize SoundCloud searches
            search_strategies = [
                # Strategy 1: SoundCloud direct search
                ('scsearch', f'scsearch1:"{clean_title}" "{clean_artist}"'),
                # Strategy 2: YouTube with exact match
                ('youtube', f'ytsearch1:"{clean_title}" "{clean_artist}"'),
                # Strategy 3: Basic search as fallback
                ('basic', f'ytsearch:{clean_title} {clean_artist}')
            ]
        else:
            # Default to YouTube first
            search_strategies = [
                # Strategy 1: YouTube with exact match
                ('youtube', f'ytsearch1:"{clean_title}" "{clean_artist}"'),
                # Strategy 2: YouTube with "official audio" qualifier
                ('youtube', f'ytsearch1:"{clean_title}" "{clean_artist}" official audio'),
                # Strategy 3: SoundCloud search
                ('soundcloud', f'scsearch1:"{clean_title}" "{clean_artist}"'),
                # Strategy 4: Basic search as fallback
                ('basic', f'ytsearch:{clean_title} {clean_artist}')
            ]
        
        # Try each strategy in order
        for platform, search_query in search_strategies:
            logger.info(f"Trying {platform} search with: {search_query}")
            
            if platform == 'soundcloud':
                # Also try direct URL construction for SoundCloud
                sc_artist = self._to_url_format(clean_artist)
                sc_title = self._to_url_format(clean_title)
                soundcloud_url = f"https://soundcloud.com/{sc_artist}/{sc_title}"
                
                # Check if this URL exists before trying to download
                if self._url_exists(soundcloud_url):
                    logger.info(f"Found direct SoundCloud URL: {soundcloud_url}")
                    result = self.download_from_url(soundcloud_url)
                    if result and result.get('success'):
                        return result
            
            # Try the search query
            if platform == 'basic':
                # Use validation for basic search to ensure good matches
                result = self._try_download_with_validation(search_query, title, artist)
            else:
                # Use direct download for more specific searches
                result = self._try_download(search_query, title, artist)
                
            if result and result.get('success'):
                return result
        
        # If we have a result but it wasn't successful, return it
        if result:
            return result
            
        # As a last resort, try a very basic search
        return self._try_download(f'ytsearch:{title} {artist}', title, artist)

    def _to_url_format(self, text):
        """Convert text to URL-friendly format for SoundCloud URLs."""
        # Remove special characters, convert to lowercase, replace spaces with hyphens
        url_text = re.sub(r'[^\w\s]', '', text).lower().strip().replace(' ', '-')
        return url_text

    def _url_exists(self, url):
        """Check if a URL exists and returns a valid response."""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code < 400
        except:
            return False

    def _try_download(self, search_query, title, artist):
        """Try downloading with a specific search query."""
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        ydl_opts = self.get_ydl_opts(output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                return {
                    'title': info.get('title', title),
                    'artist': info.get('uploader', artist),
                    'success': True,
                    'filepath': f"{info.get('title', title)} - {info.get('uploader', artist)}.mp3"
                }
        except Exception as e:
            return {
                'title': title,
                'artist': artist,
                'success': False,
                'error': str(e)
            }

    def _try_download_with_validation(self, search_query, expected_title, expected_artist):
        """Try downloading with validation of results against expected title/artist."""
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        ydl_opts = self.get_ydl_opts(output_template, download=False)  # Don't download yet
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info_dict:
                    # It's a playlist or a list of videos
                    entries = info_dict['entries']
                    if not entries:
                        return {'title': expected_title, 'artist': expected_artist, 'success': False, 
                                'error': 'No results found'}
                        
                    # Find the best matching entry
                    best_match = self._find_best_match(entries, expected_title, expected_artist)
                    
                    if best_match:
                        # Now download the best match
                        ydl_opts = self.get_ydl_opts(output_template, download=True)
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                            info = ydl2.extract_info(best_match['webpage_url'], download=True)
                            return {
                                'title': info.get('title', expected_title),
                                'artist': info.get('uploader', expected_artist),
                                'success': True,
                                'filepath': f"{info.get('title', expected_title)} - {info.get('uploader', expected_artist)}.mp3",
                                'match_score': best_match.get('match_score', 0)
                            }
                
                return {'title': expected_title, 'artist': expected_artist, 'success': False, 
                        'error': 'Could not find a good match'}
                    
        except Exception as e:
            return {
                'title': expected_title,
                'artist': expected_artist,
                'success': False,
                'error': str(e)
            }

    def _find_best_match(self, entries, expected_title, expected_artist):
        """Find the best matching entry based on title and artist similarity."""
        best_match = None
        best_score = 0
        
        # Clean the expected values for better matching
        expected_title_clean = self._clean_for_search(expected_title)
        expected_artist_clean = self._clean_for_search(expected_artist)
        
        for entry in entries:
            title = entry.get('title', '').lower()
            uploader = entry.get('uploader', '').lower()
            
            # Clean the entry values the same way
            title_clean = self._clean_for_search(title)
            uploader_clean = self._clean_for_search(uploader)
            
            # Calculate similarity scores
            title_score = self._similarity_score(title_clean, expected_title_clean)
            artist_score = self._similarity_score(uploader_clean, expected_artist_clean)
            
            # Combined score with more weight on title match
            combined_score = (title_score * 0.7) + (artist_score * 0.3)
            
            # Boost score for exact matches
            if expected_title_clean in title_clean or title_clean in expected_title_clean:
                combined_score += 0.2
                
            if expected_artist_clean in uploader_clean or uploader_clean in expected_artist_clean:
                combined_score += 0.2
            
            # Cap at 1.0
            combined_score = min(combined_score, 1.0)
            
            # Only accept matches above threshold
            if combined_score > best_score and combined_score > 0.5:
                best_score = combined_score
                entry['match_score'] = combined_score
                best_match = entry
                
                # If we have a very good match, stop looking
                if combined_score > 0.8:
                    break
        
        return best_match

    def _similarity_score(self, text1, text2):
        """Calculate similarity between two strings."""
        # If one string contains the other, high similarity
        if text1 in text2 or text2 in text1:
            return 0.9
        
        # Count matching words
        words1 = set(text1.split())
        words2 = set(text2.split())
        common_words = words1.intersection(words2)
        
        if not words1 or not words2:
            return 0
        
        # Calculate Jaccard similarity
        jaccard = len(common_words) / len(words1.union(words2))
        
        # Calculate overlap coefficient
        overlap = len(common_words) / min(len(words1), len(words2))
        
        # Weight both metrics
        return (jaccard * 0.5) + (overlap * 0.5)
        
    async def download(self, song_title, artist, youtube_link=None, song_id=None):
        """
        Download a song asynchronously.
        
        Args:
            song_title: Title of the song
            artist: Artist name
            youtube_link: Optional direct YouTube link
            song_id: ID for progress tracking
            
        Returns:
            Tuple of (success, filepath)
        """
        try:
            # Update progress if we have a tracker and song_id
            if self.progress_tracker and song_id:
                self.progress_tracker.update_progress(
                    song_id,
                    status=SongStatus.SEARCHING,
                    message=f"Searching for {song_title} by {artist}..."
                )
            
            # If we have a direct YouTube link, use it
            if youtube_link and self._is_valid_url(youtube_link):
                result = self.download_from_url(youtube_link)
            else:
                # Otherwise search for the song
                result = self.download_song(song_title, artist)
            
            # Update progress based on result
            if self.progress_tracker and song_id:
                if result and result.get('success'):
                    self.progress_tracker.update_progress(
                        song_id,
                        status=SongStatus.COMPLETED,
                        message="Download complete"
                    )
                    return True, result.get('filepath')
                else:
                    error_msg = result.get('error', 'Unknown error') if result else 'Failed to download'
                    self.progress_tracker.update_progress(
                        song_id,
                        status=SongStatus.FAILED,
                        message=f"Download failed: {error_msg}"
                    )
                    return False, None
            
            # If no progress tracker, just return the result
            return result and result.get('success'), result.get('filepath') if result else None
            
        except Exception as e:
            logger.error(f"Error downloading {song_title} by {artist}: {str(e)}")
            
            # Update progress on error
            if self.progress_tracker and song_id:
                self.progress_tracker.update_progress(
                    song_id,
                    status=SongStatus.FAILED,
                    message=f"Download error: {str(e)}"
                )
            
            return False, None

class PlaylistDownloader:
    """Downloads a playlist of songs."""
    
    def __init__(self, task_id: str = None):
        self.task_id = task_id or str(uuid.uuid4())
        # Replace settings-based path with direct path
        # self.settings = get_settings()
        # self.output_dir = Path(self.settings.DOWNLOAD_DIR) / self.task_id
        self.output_dir = Path(os.path.join(os.path.dirname(__file__), "../../../playlist", self.task_id))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress_tracker = ProgressTracker(self.task_id)
        self.song_downloader = SongDownloader(self.progress_tracker, str(self.output_dir))
        
    async def download_playlist(self, songs: List[Dict]) -> str:
        """
        Download a playlist of songs.
        
        Args:
            songs: List of song dictionaries with at least a 'title' field
            
        Returns:
            Task ID for tracking progress
        """
        if not songs:
            logger.warning("No songs provided for download")
            return self.task_id
        
        # Initialize progress for all songs
        for idx, song in enumerate(songs):
            title = song.get('title', f"Unknown Song {idx+1}")
            artist = song.get('artist')
            
            # Generate consistent song ID
            song_id = song.get('id') or generate_song_id(title, artist)
            
            # Format the song name for display
            song_name = f"{artist} - {title}" if artist else title
            
            # Initialize progress for this song
            self.progress_tracker.add_song(
                song_id=song_id,
                song_name=song_name,
                status=SongStatus.QUEUED,
                message="Queued for download"
            )
            
            # Add the song ID to the dictionary for later reference
            song['id'] = song_id
        
        # Launch downloads concurrently but with a limit
        max_concurrent = min(3, len(songs))  # Limit concurrent downloads
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(song):
            async with semaphore:
                title = song.get('title', "Unknown")
                artist = song.get('artist')
                youtube_link = song.get('youtube_link')
                song_id = song.get('id')
                
                self.progress_tracker.update_progress(
                    song_id,
                    status=SongStatus.PROCESSING,
                    message="Starting download..."
                )
                
                # Attempt to download the song
                success, filepath = await self.song_downloader.download(
                    song_title=title,
                    artist=artist,
                    youtube_link=youtube_link,
                    song_id=song_id
                )
                
                return success, filepath, song
        
        # Create tasks for all songs while maintaining order
        download_tasks = []
        for idx, song in enumerate(songs):
            # Add a small delay between starting each task to avoid rate limiting
            await asyncio.sleep(0.5)
            task = asyncio.create_task(download_with_semaphore(song))
            download_tasks.append(task)
        
        # Wait for all downloads to complete
        results = []
        for task in asyncio.as_completed(download_tasks):
            result = await task
            results.append(result)
        
        # Count successful downloads
        successful = sum(1 for success, _, _ in results if success)
        logger.info(f"Downloaded {successful}/{len(songs)} songs for task {self.task_id}")
        
        return self.task_id 