"""
Download API Routes

This module contains FastAPI routes for downloading songs and playlists.
It handles validation of song data and initiates download processes.
"""

from typing import Union, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException
import asyncio
from ...api.models import Song
import logging
from ...core.downloader import downloader, PlaylistDownloader
from pydantic import BaseModel

router = APIRouter()

logger = logging.getLogger(__name__)

# Create a global downloader instance
downloader = PlaylistDownloader()

class SongList(BaseModel):
    songs: List[Song]

@router.post("/download/playlist")
async def download_playlist_endpoint(songlist: SongList):
    """
    Endpoint to download a playlist of songs
    
    Args:
        songlist: SongList object with a list of Song objects
        
    Returns:
        JSON response with download status
    """
    try:
        logger.info(f"Playlist download request received for {len(songlist.songs)} songs")
        
        if not songlist.songs:
            raise HTTPException(status_code=400, detail="No songs provided")
        
        # Extract title and artist from each song
        song_pairs = [(song.title, song.artist) for song in songlist.songs]
        
        # Start the download process in the background
        asyncio.create_task(downloader.download_playlist(song_pairs))
        
        return {
            "success": True, 
            "message": f"Download of {len(songlist.songs)} songs started",
            "total": len(songlist.songs)
        }
    except Exception as e:
        logger.error(f"Playlist download error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

@router.get("/download/progress")
async def get_download_progress(song_key: str = None):
    """
    Get the current progress of ongoing downloads
    
    Args:
        song_key: Optional key to get progress for a specific song
        
    Returns:
        Dictionary with download progress information
    """
    try:
        return downloader.get_progress(song_key)
    except Exception as e:
        logger.error(f"Error retrieving download progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download-song")
async def download_song_endpoint(songs: List[Song]):
    """
    Endpoint to download one or more songs
    
    Args:
        songs: List of Song objects with title and artist fields
        
    Returns:
        JSON response with download status
    """
    try:
        logger.info(f"Download request received for {len(songs)} songs")
        
        # Convert to list of (title, artist) tuples
        song_pairs = [(song.title, song.artist) for song in songs]
        
        # Start the download process in the background
        asyncio.create_task(downloader.download_playlist(song_pairs))
        
        return {
            "success": True, 
            "message": f"Download of {len(songs)} songs started",
            "total": len(songs)
        }
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}") 