from pathlib import Path
import yt_dlp
import ssl
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create unverified SSL context
ssl._create_default_https_context = ssl._create_unverified_context

@dataclass
class DownloadProgress:
    song: str
    status: str  # 'starting', 'downloading', 'finished', 'error'
    progress: float = 0
    error: Optional[str] = None
    total_bytes: Optional[int] = None
    downloaded_bytes: Optional[int] = None
    speed: Optional[str] = None
    eta: Optional[str] = None

class PlaylistDownloader:
    def __init__(self, output_dir: str = "playlist"):
        self.output_dir = output_dir
        self.progress: dict[str, DownloadProgress] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._active = False
        Path(output_dir).mkdir(exist_ok=True)

    def _progress_hook(self, d):
        song = d.get('info_dict', {}).get('title', 'Unknown')
        song_key = d.get('info_dict', {}).get('song_key', song)
        
        # Ensure we have a valid song key
        if not song_key or song_key.strip() == '':
            logger.error("Empty song key detected in progress hook")
            return

        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                # Ensure we have valid numbers
                if downloaded < 0 or total < 0:
                    logger.error(f"Invalid download values for {song_key}: downloaded={downloaded}, total={total}")
                    return
                
                # Calculate progress percentage
                progress = (downloaded / total * 100) if total else 0
                
                # Format speed and ETA
                speed = d.get('speed', 0)
                speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "N/A"
                eta = d.get('eta', 0)
                eta_str = f"{eta}s" if eta else "N/A"

                self.progress[song_key] = DownloadProgress(
                    song=song_key,
                    status='downloading',
                    progress=progress,
                    total_bytes=total,
                    downloaded_bytes=downloaded,
                    speed=speed_str,
                    eta=eta_str
                )
                logger.info(f"Downloading {song_key}: {progress:.1f}% at {speed_str}, ETA: {eta_str}")
            except Exception as e:
                logger.error(f"Error updating progress for {song_key}: {str(e)}")

        elif d['status'] == 'finished':
            self.progress[song_key] = DownloadProgress(
                song=song_key,
                status='processing',  # Indicate post-processing
                progress=100,
                speed="Processing...",
                eta="..."
            )
            logger.info(f"Processing {song_key}")

        elif d['status'] == 'error':
            error_msg = d.get('error', 'Unknown error')
            self.progress[song_key] = DownloadProgress(
                song=song_key,
                status='error',
                error=error_msg
            )
            logger.error(f"Error downloading {song_key}: {error_msg}")

    def cleanup(self):
        """Clean up resources"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        self._active = False
        logger.info("Downloader cleanup complete")

    async def download_song(self, title: str, artist: str) -> DownloadProgress:
        # Validate input
        if not title or not title.strip() or not artist or not artist.strip():
            error_msg = "Title and artist must not be empty"
            logger.error(error_msg)
            return DownloadProgress(
                song=f"{artist} - {title}",
                status='error',
                error=error_msg
            )

        song_key = f"{artist} - {title}"
        self.progress[song_key] = DownloadProgress(song=song_key, status='starting')
        logger.info(f"Starting download for {song_key}")

        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': '%(title)s.%(ext)s',
            'paths': {'home': self.output_dir},
            'progress_hooks': [self._progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'info_dict': {'song_key': song_key}  # Add song_key to info_dict for progress tracking
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Run download in thread pool to not block
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor,
                    lambda: ydl.download([f"ytsearch1:{artist} {title} audio"])
                )
                
            return self.progress[song_key]
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to download {song_key}: {error_msg}")
            self.progress[song_key] = DownloadProgress(
                song=song_key,
                status='error',
                error=error_msg
            )
            return self.progress[song_key]

    async def download_playlist(self, songs: List[Tuple[str, str]]) -> List[DownloadProgress]:
        """Download multiple songs concurrently"""
        self._active = True
        tasks = []
        for title, artist in songs:
            task = asyncio.create_task(self.download_song(title, artist))
            tasks.append(task)
        
        try:
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
                    # Mark as truly finished after post-processing
                    if result.status == 'processing':
                        result.status = 'finished'
                        result.speed = 'Complete'
                        result.eta = '0s'
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

    def get_progress(self, song_key: Optional[str] = None) -> Union[DownloadProgress, dict]:
        """Get download progress for all songs or a specific song"""
        if not self._active:
            # Update any 'processing' status to 'finished' when inactive
            for progress in self.progress.values():
                if progress.status == 'processing':
                    progress.status = 'finished'
                    progress.speed = 'Complete'
                    progress.eta = '0s'
        
        if song_key:
            return self.progress.get(song_key)
        return self.progress 