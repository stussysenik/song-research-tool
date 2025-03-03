from pathlib import Path
import yt_dlp
import ssl
from typing import List, Tuple, Optional, Union, Dict, Any
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
from ..models.song import Song
import re
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create unverified SSL context for HTTPS connections
ssl._create_default_https_context = ssl._create_unverified_context

# Set up the download directory in the project root
DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../playlist"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@dataclass
class DownloadProgress:
    """
    Tracks the progress of a song download
    
    Attributes:
        song: String identifier for the song (usually "title by artist")
        status: Current status of the download ('starting', 'searching', etc.)
        progress: Percentage of download completion (0-100)
        error: Error message if download failed
        total_bytes: Total size of the file being downloaded
        downloaded_bytes: Number of bytes downloaded so far
        speed: Download speed (formatted string)
        eta: Estimated time remaining (formatted string)
    """
    song: str
    status: str  # 'starting', 'searching', 'downloading', 'processing', 'finished', 'error'
    progress: float = 0
    error: Optional[str] = None
    total_bytes: Optional[int] = None
    downloaded_bytes: Optional[int] = None
    speed: Optional[str] = None
    eta: Optional[str] = None

class PlaylistDownloader:
    """
    Handles downloading songs and playlists from various sources
    
    This class provides methods to download individual songs or entire playlists,
    with progress tracking and error handling. It uses yt-dlp to search and download
    from YouTube and other sources.
    """
    
    def __init__(self, output_dir: str = DOWNLOAD_DIR):
        """
        Initialize the downloader
        
        Args:
            output_dir: Directory where downloaded songs will be saved
        """
        self.output_dir = output_dir
        
        # Ensure the directory exists and is writable
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Test write permissions
        try:
            test_file = os.path.join(self.output_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Download directory is writable: {self.output_dir}")
        except Exception as e:
            logger.error(f"Cannot write to download directory: {str(e)}")
            # Try to use a fallback directory in the user's home folder
            home_dir = os.path.expanduser("~/playlist")
            os.makedirs(home_dir, exist_ok=True)
            logger.info(f"Using fallback directory: {home_dir}")
            self.output_dir = home_dir
        
        self.progress = {}
        self._active = False
        
    def cleanup(self):
        """Clean up resources after downloads are complete"""
        self._active = False
        logger.info("Downloader cleanup complete")
        
    def _generate_id(self, title: str, artist: str) -> str:
        """
        Generate a unique ID for a song based on title and artist
        
        Args:
            title: Song title
            artist: Artist name
            
        Returns:
            A normalized string ID for the song
        """
        normalized_title = re.sub(r'[^\w\s]', '', title.lower())
        normalized_artist = re.sub(r'[^\w\s]', '', artist.lower())
        return f"{normalized_artist}_{normalized_title}"
        
    def _progress_hook(self, d: Dict, song_key: str) -> None:
        """
        Progress hook for yt-dlp to update download status
        
        This is called by yt-dlp during the download process to report progress.
        
        Args:
            d: Dictionary with download information from yt-dlp
            song_key: Unique identifier for the song
        """
        if song_key not in self.progress:
            self.progress[song_key] = DownloadProgress(
                song=song_key,
                status="starting",
                progress=0
            )
            
        if d['status'] == 'downloading':
            self.progress[song_key].status = 'downloading'
            if 'total_bytes' in d and d['total_bytes'] > 0:
                downloaded = d.get('downloaded_bytes', 0)
                total = d['total_bytes']
                progress = min(0.9, downloaded / total)
                
                self.progress[song_key].progress = progress * 100
                self.progress[song_key].speed = d.get('speed', 0)
                self.progress[song_key].eta = d.get('eta', 0)
                
        elif d['status'] == 'finished':
            self.progress[song_key].status = 'processing'
            self.progress[song_key].progress = 95
            
    def _download_with_ytdlp(self, title: str, artist: str, song_key: str) -> str:
        """Download a song using yt-dlp and return the output file path"""
        # Check if this song is likely to be on Soundcloud
        is_soundcloud_likely = asyncio.run(self._check_soundcloud_likelihood(title, artist))
        
        # Create a more specific search query
        if is_soundcloud_likely:
            logger.info(f"Song '{title} by {artist}' likely on Soundcloud, prioritizing Soundcloud search")
            search_query = f"scsearch3:{title} {artist}"
        else:
            # Allow up to 3 results helps when the exact title isn't found
            search_query = f"ytsearch3:{title} {artist} official audio"
        
        # Define a safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_artist = re.sub(r'[^\w\s-]', '', artist)
        safe_filename = f"{safe_title} - {safe_artist}"
        output_path = os.path.join(self.output_dir, f"{safe_filename}.mp3")
        
        # Improved yt-dlp options with better formatting and error handling
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'progress_hooks': [lambda d: self._progress_hook(d, song_key)],
            'quiet': False,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'ignoreerrors': True,
            'no_warnings': False,  # Show warnings for better debugging
            'geo_bypass': True,    # Try to bypass geo-restrictions
            'nocheckcertificate': True,  # Skip HTTPS certificate validation
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Log search query for debugging
                logger.info(f"Searching for: {search_query}")
                
                # Search and download
                info = ydl.extract_info(search_query, download=True)
                
                if info is None:
                    # If the initial search failed and we didn't try Soundcloud yet, try it as fallback
                    if not is_soundcloud_likely:
                        logger.info(f"No YouTube results for '{title} by {artist}', trying Soundcloud as fallback")
                        fallback_query = f"scsearch3:{title} {artist}"
                        info = ydl.extract_info(fallback_query, download=True)
                        
                    # If still no results, try a more generic search
                    if info is None:
                        logger.info(f"Trying more generic search for '{title} by {artist}'")
                        generic_query = f"ytsearch3:{title} {artist}"
                        info = ydl.extract_info(generic_query, download=True)
                    
                    # If all searches failed, raise exception
                    if info is None:
                        raise Exception(f"No results found for {title} by {artist}")
                
                # Handle search results
                if 'entries' in info:
                    # Get the first valid entry
                    valid_entries = [e for e in info['entries'] if e is not None]
                    if not valid_entries:
                        raise Exception(f"No valid results found for {title} by {artist}")
                    info = valid_entries[0]
                
                # Get the output filename
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                output_file = f"{base}.mp3"
                
                # Log the output file path
                logger.info(f"Download completed, output file: {output_file}")
                
                # Check if the file exists
                if not os.path.exists(output_file):
                    # Try the safe filename path instead
                    if os.path.exists(output_path):
                        return output_path
                    
                    # Final check and fallback
                    logger.warning(f"Output file not found at {output_file} or {output_path}")
                    # Create a message file instead of an empty file
                    with open(output_path, 'w') as f:
                        f.write(f"Failed to download: {title} by {artist}\nPlease try again or download manually.")
                    return output_path
                    
                return output_file
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            # Create a message file instead of an empty file
            with open(output_path, 'w') as f:
                f.write(f"Failed to download: {title} by {artist}\nError: {str(e)}")
            return output_path
            
    async def download_song(self, song: Song) -> DownloadProgress:
        """
        Download a single song and return download progress
        
        Args:
            song: Song object with title and artist
            
        Returns:
            DownloadProgress object
        """
        song_key = self._generate_id(song.title, song.artist)
        logger.info(f"Starting download for: {song.title} by {song.artist} (key: {song_key})")
        
        # Create initial progress object
        self.progress[song_key] = DownloadProgress(
            song=f"{song.title} - {song.artist}",
            status='searching',
            progress=0
        )
        
        try:
            # Log the attempt with more details
            logger.info(f"Creating search query for: {song.title} by {song.artist}")
            
            # Create search query with optimizations for SoundCloud
            search_query = f"{song.title} {song.artist} audio"
            soundcloud_query = f"{song.title} {song.artist} site:soundcloud.com"
            
            # Set up download options with proper paths
            safe_title = re.sub(r'[^\w\s-]', '', song.title)
            safe_artist = re.sub(r'[^\w\s-]', '', song.artist)
            
            output_template = os.path.join(self.output_dir, f"{safe_title} - {safe_artist}.%(ext)s")
            logger.info(f"Output template: {output_template}")
            
            ytdl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'default_search': 'ytsearch',
                'quiet': True,
                'no_warnings': True,
                'logger': logger,  # Add logger to get more detailed error messages
                'progress_hooks': [lambda d: self._progress_hook(d, song_key)],
            }
            
            # Try SoundCloud first (often better quality)
            logger.info(f"Trying SoundCloud search for: {song.title} by {song.artist}")
            self.progress[song_key].status = 'downloading'
            self.progress[song_key].progress = 10
            
            try:
                logger.info(f"Starting SoundCloud download for: {soundcloud_query}")
                # Make directory if it doesn't exist
                os.makedirs(self.output_dir, exist_ok=True)
                
                with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                    # Try SoundCloud specific search
                    ydl.download([f"scsearch1:{song.title} {song.artist}"])
                    
                    # Update progress
                    self.progress[song_key].progress = 100
                    self.progress[song_key].status = 'finished'  # Use 'finished' for consistency
                    
                    logger.info(f"SoundCloud download successful for: {song.title} by {song.artist}")
                    return self.progress[song_key]
                    
            except Exception as soundcloud_err:
                # If SoundCloud fails, log the error and fall back to general search
                logger.warning(f"SoundCloud search failed for {song.title}. Error: {str(soundcloud_err)}")
                
                try:
                    logger.info(f"Starting general search for: {search_query}")
                    
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        ydl.download([f"ytsearch1:{search_query}"])
                        
                        # Update progress
                        self.progress[song_key].progress = 100
                        self.progress[song_key].status = 'finished'
                        
                        logger.info(f"General search download successful for: {song.title} by {song.artist}")
                        return self.progress[song_key]
                        
                except Exception as general_err:
                    logger.error(f"General search failed for {song.title}. Error: {str(general_err)}")
                    raise general_err
            
        except Exception as e:
            logger.error(f"Download failed for {song.title} by {song.artist}. Error: {str(e)}")
            
            # Check if the progress entry exists
            if song_key in self.progress:
                self.progress[song_key].status = 'error'
                self.progress[song_key].error = str(e)
            else:
                # Create a new progress entry if it doesn't exist
                self.progress[song_key] = DownloadProgress(
                    song=f"{song.title} - {song.artist}",
                    status='error',
                    error=str(e)
                )
            
            return self.progress[song_key]
            
    async def download_playlist(self, songs: List[Tuple[str, str]]) -> List[DownloadProgress]:
        """
        Download multiple songs concurrently
        
        Args:
            songs: List of (title, artist) tuples
            
        Returns:
            List of DownloadProgress objects for each song
        """
        self._active = True
        tasks = []
        
        for title, artist in songs:
            # Create Song objects with keyword arguments
            song = Song(title=title, artist=artist)
            task = asyncio.create_task(self.download_song(song))
            tasks.append(task)
        
        try:
            # Wait for all downloads to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            final_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {str(result)}")
                    # Create error progress for failed task
                    error_progress = DownloadProgress(
                        song="Unknown",
                        status='error',
                        error=str(result)
                    )
                    final_results.append(error_progress)
                else:
                    final_results.append(result)
            
            # Mark as inactive and cleanup
            self._active = False
            self.cleanup()
            return final_results
            
        except Exception as e:
            logger.error(f"Playlist download failed: {str(e)}")
            self._active = False
            self.cleanup()
            raise
            
    def get_progress(self, song_key: Optional[str] = None) -> Union[DownloadProgress, Dict[str, DownloadProgress]]:
        """
        Get download progress for all songs or a specific song
        
        Args:
            song_key: Optional key to get progress for a specific song
            
        Returns:
            DownloadProgress object for a specific song, or dictionary of all progress objects
        """
        if not self._active:
            # Update any 'processing' status to 'finished' when inactive
            for progress in self.progress.values():
                if progress.status == 'processing':
                    progress.status = 'finished'
                    progress.progress = 100
        
        if song_key:
            return self.progress.get(song_key)
        return self.progress

    async def _check_soundcloud_likelihood(self, title: str, artist: str) -> bool:
        """
        Check if a song is likely to be found on Soundcloud.
        This is a simple heuristic that can be improved with more sophisticated checks.
        
        Args:
            title: Song title
            artist: Artist name
            
        Returns:
            True if the song is likely on Soundcloud, False otherwise
        """
        # Expanded list of keywords associated with Soundcloud
        soundcloud_keywords = [
            'remix', 'dj', 'mix', 'electronic', 'edm', 'house', 'techno', 
            'dubstep', 'trap', 'lofi', 'lo-fi', 'beat', 'producer',
            'mashup', 'flip', 'edit', 'bootleg', 'future bass', 'deep house',
            'tropical', 'club', 'bassline', 'drum & bass', 'drum and bass',
            'dnb', 'd&b', 'jersey', 'breaks', 'unreleased', 'vip', 
            'soundcloud exclusive', 'free download', 'bedroom producer',
            'ambient', 'chill', 'indie dance', 'underground', 'garage'
        ]
        
        # Artists commonly found on Soundcloud
        soundcloud_artists = [
            'flume', 'diplo', 'skrillex', 'mr. carmack', 'kaytranada', 'disclosure', 
            'bonobo', 'porter robinson', 'clams casino', 'hudson mohawke', 'sam gellaitry',
            'mura masa', 'flying lotus', 'shlohmo', 'baauer', 'rustie', 'four tet',
            'rl grime', 'burial', 'cashmere cat', 'jamie xx', 'madlib', 'dj shadow',
            'san holo', 'illenium', 'odesza', 'herobust', 'said the sky', 'deadmau5',
            'lido', 'troyboi', 'mr. bill', 'tycho', 'jon hopkins', 'shigeto',
            'arca', 'tokimonsta', 'jai paul', 'iglooghost', 'aphex twin', 'machinedrum'
        ]
        
        combined = (title + ' ' + artist).lower()
        
        # Check for keywords in title or artist
        keyword_match = any(keyword in combined for keyword in soundcloud_keywords)
        
        # Check if artist is known to be popular on Soundcloud
        artist_match = any(sc_artist.lower() in artist.lower() for sc_artist in soundcloud_artists)
        
        return keyword_match or artist_match

    def _get_soundcloud_client_id(self) -> str:
        """
        Get a Soundcloud client ID for API access.
        In a production environment, this would use a proper API key management system.
        
        Returns:
            Soundcloud client ID
        """
        # In a real implementation, this would come from environment variables or a secure store
        # For development, we'll use a placeholder that yt-dlp will replace with its own logic
        return 'YOUR_SOUNDCLOUD_CLIENT_ID'  # yt-dlp will handle this automatically if empty 

    def _download_song(self, title: str, artist: str, progress_callback=None) -> str:
        """
        Download a single song from YouTube or other source
        
        Args:
            title: Song title
            artist: Artist name
            progress_callback: Function to call with progress updates
            
        Returns:
            Path to the downloaded file
        """
        song_identifier = f"{title} by {artist}"
        search_query = f"{title} {artist} official audio"
        
        # Prepare options for yt-dlp
        ydl_opts = self._get_base_ytdl_opts(song_identifier, progress_callback)
        
        # Add search options to prioritize exact matches
        ydl_opts.update({
            # Force use of the exact title and artist in search
            'default_search': 'ytsearch',
            'match_filter': lambda info_dict: 'Original title matches' 
                              if (title.lower() in info_dict.get('title', '').lower() and 
                                 artist.lower() in info_dict.get('title', '').lower()) 
                              else 'Original title not found',
            # Set a more restrictive search string
            'playlistend': 1,  # Only download first result that matches
        })
        
        # For songs likely on Soundcloud, try there first
        if self._is_likely_on_soundcloud(title, artist):
            try:
                return self._download_from_source(f"scsearch:{title} {artist}", ydl_opts)
            except Exception as e:
                logger.info(f"Could not find {song_identifier} on Soundcloud, trying YouTube: {str(e)}")
        
        # Try direct YouTube search with strict matching
        try:
            return self._download_from_source(f"ytsearch:{search_query}", ydl_opts)
        except Exception as e:
            logger.warning(f"Could not download {song_identifier} with strict matching: {str(e)}")
            
            # Fall back to more relaxed search if needed
            logger.info(f"Trying alternative search for {song_identifier}")
            ydl_opts.pop('match_filter', None)  # Remove strict matching
            return self._download_from_source(f"ytsearch:{title} {artist}", ydl_opts)

    def _format_soundcloud_query(self, song):
        """
        Format a query specifically for SoundCloud content.
        
        Args:
            song: Song object with title and artist
            
        Returns:
            Optimized search query for youtube-dl/yt-dlp
        """
        # Check if this might be a SoundCloud song
        if "soundcloud" in song.title.lower() or "soundcloud" in song.artist.lower():
            # If the title contains a URL, use it directly
            import re
            soundcloud_url = re.search(r'https?://soundcloud\.com/[^\s]+', f"{song.title} {song.artist}")
            if soundcloud_url:
                return soundcloud_url.group(0)
            
        # Otherwise create a SoundCloud-specific search
        return f"scsearch:{song.title} {song.artist}"

# Add this line at the end of the file
downloader = PlaylistDownloader() 