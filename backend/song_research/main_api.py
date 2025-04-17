from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Union, Any
import csv
from io import StringIO
from .core.downloader import PlaylistDownloader, DownloadProgress
from .ocr.gemini_extractor import GeminiExtractor
import os
import logging
from .models.song import Song, SongList
from .api.routes.extraction import router as extraction_router
from .api.routes.download import router as download_router
from fastapi.responses import JSONResponse
import uuid
from .ocr_processor import OCRProcessor
from .downloader import SongDownloader
import asyncio
import re
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Song Research API")

# Configure CORS with explicit headers for file uploads
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Allow both localhost and IP
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# Global downloader instance
downloader = PlaylistDownloader()

# Include our extraction routes
app.include_router(extraction_router, prefix="/api", tags=["extraction"])
app.include_router(download_router, prefix="/api", tags=["download"])

class SongList(BaseModel):
    songs: List[Dict[str, str]]  # Accept a list of dict with title and artist

class DownloadRequest(BaseModel):
    title: str
    artist: str

@app.post("/api/download/song")
async def download_song(request: DownloadRequest) -> DownloadProgress:
    """Download a single song"""
    song = Song(title=request.title, artist=request.artist)
    return await downloader.download_song(song)

@app.post("/api/download/playlist")
async def download_playlist(songlist: SongList) -> Dict[str, Any]:
    """Download multiple songs from song list, return task_id."""
    try:
        # Convert the songs list to Song objects
        song_objects = []
        for song_dict in songlist.songs:
            # Create Song object from dict
            if 'title' in song_dict and 'artist' in song_dict:
                song_objects.append(Song(
                    title=song_dict['title'].strip(),
                    artist=song_dict['artist'].strip()
                ))
        
        if not song_objects:
            raise HTTPException(status_code=400, detail="No valid songs found in input")
            
        # Convert to list of tuples for the downloader
        songs: List[Tuple[str, str]] = [(song.title, song.artist) for song in song_objects]
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Start download in background, passing the task_id to the downloader
        # *** NOTE: Assumes downloader.download_playlist accepts task_id ***
        # *** This might require changes in PlaylistDownloader class ***
        logger.info(f"Initiating playlist download task {task_id} for {len(songs)} songs.")
        asyncio.create_task(downloader.download_playlist(songs, task_id=task_id))
        
        # Return the task_id in the response
        return {
            "success": True,
            "message": f"Download of {len(songs)} songs started",
            "total": len(songs),
            "task_id": task_id # Include the task ID
        }
    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        # Ensure task_id is not included on error
        return {
            "success": False,
            "message": f"Failed to start download playlist: {str(e)}"
            # No task_id on failure
        }

@app.get("/api/download/progress/{task_id}")
async def get_progress_for_task(task_id: str):
    """Get download progress for a specific task."""
    logger.info(f"Fetching progress for task {task_id}")
    try:
        # Look for the task in the active downloads
        # Since we don't have a proper task registry yet, we'll return the global progress
        # This is a temporary solution until task-specific tracking is implemented
        progress_data = downloader.get_progress() 
        if progress_data is None or not progress_data:
            # Return empty object instead of 404 if no progress yet
            logger.warning(f"No active progress found for task {task_id}. Returning empty object.")
            return {}
            
        # Convert the progress data to a format the frontend expects
        formatted_progress = {}
        for song_key, progress in progress_data.items():
            # Convert to dict if it's not already
            if not isinstance(progress, dict):
                formatted_progress[song_key] = {
                    "song": progress.song if hasattr(progress, 'song') else "Unknown",
                    "status": progress.status if hasattr(progress, 'status') else "unknown",
                    "progress": progress.progress if hasattr(progress, 'progress') else 0,
                    "error": progress.error if hasattr(progress, 'error') else None
                }
            else:
                formatted_progress[song_key] = progress
                
        return formatted_progress
    except Exception as e:
        logger.error(f"Error fetching progress for task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get progress for task {task_id}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/process-songs/")
async def process_songs(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    direct_url: Optional[str] = Form(None),
    song_text: Optional[str] = Form(None),
    platform: Optional[str] = Form(None)  # Added platform parameter
):
    """Process songs from various input sources with optional platform specification."""
    try:
        songs = []
        
        if direct_url:
            # Process direct URL
            songs.append(direct_url)
        elif file:
            # Process file upload
            file_path = save_uploaded_file(file)
            
            if file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Image processing
                ocr_processor = OCRProcessor()
                songs = ocr_processor.process_image(file_path)
            elif file.filename.lower().endswith('.pdf'):
                # PDF processing
                ocr_processor = OCRProcessor()
                songs = ocr_processor.process_pdf(file_path)
            elif file.filename.lower().endswith(('.txt', '.csv')):
                # Text file processing
                with open(file_path, 'r') as f:
                    content = f.read()
                ocr_processor = OCRProcessor()
                songs = ocr_processor.extract_songs_from_text(content)
            
            # Clean up uploaded file
            os.remove(file_path)
        elif song_text:
            # Process direct text input
            ocr_processor = OCRProcessor()
            songs = ocr_processor.extract_songs_from_text(song_text)
        
        if not songs:
            raise HTTPException(status_code=400, detail="No songs found in the provided input")
        
        # Initialize the downloader with platform preference if specified
        downloader = SongDownloader(platform_preference=platform)
        
        # Start download process
        task_id = str(uuid.uuid4())
        background_tasks.add_task(
            download_songs_task,
            songs=songs,
            task_id=task_id,
            downloader=downloader
        )
        
        return {"message": "Processing started", "task_id": task_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing songs: {str(e)}")

@app.post("/api/extract")
async def extract_songs(file: UploadFile = File(...)):
    """Extract songs from an image using OCR"""
    logger.info(f"Received file upload request: {file.filename} ({file.content_type})")
    
    if not file:
        logger.error("No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    if not file.content_type or not file.content_type.startswith(('image/', 'application/pdf')):
        logger.error(f"Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image or PDF")
    
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        try:
            contents = await file.read()
            if not contents:
                logger.error("Empty file uploaded")
                raise HTTPException(status_code=400, detail="Empty file uploaded")
            
            logger.info(f"Saving temporary file: {temp_path}")    
            with open(temp_path, "wb") as f:
                f.write(contents)

            # Process with GeminiExtractor
            logger.info("Initializing GeminiExtractor")
            extractor = GeminiExtractor()
            
            file_size = os.path.getsize(temp_path)
            logger.info(f"File size: {file_size} bytes")
            
            if not extractor.validate_token_usage(file_size):
                logger.error("File too large for processing")
                raise HTTPException(status_code=400, detail="File too large for processing")

            logger.info("Processing file with GeminiExtractor")
            song_list = extractor.process_file(temp_path)
            
            if not song_list or not song_list.songs:
                logger.error("No songs extracted from image")
                raise HTTPException(status_code=400, detail="No songs could be extracted from the image")
            
            logger.info(f"Successfully extracted {len(song_list.songs)} songs")
            return {"songs": song_list.songs}

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                logger.info(f"Cleaning up temporary file: {temp_path}")
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/test")
async def test_api():
    """Test endpoint to verify API is running"""
    return {"status": "ok", "message": "API is running"}

# Add helper function for file uploads
def save_uploaded_file(file: UploadFile) -> str:
    """Save an uploaded file to a temporary location and return the path."""
    temp_path = f"temp_{file.filename}"
    try:
        contents = file.file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
        return temp_path
    finally:
        file.file.close()

# Add the missing download_songs_task function
async def download_songs_task(songs: List, task_id: str, downloader: SongDownloader):
    """
    Process a list of songs for downloading.
    
    Args:
        songs: List of song data (can be URLs, dicts with title/artist, or strings)
        task_id: Unique task ID for tracking progress
        downloader: SongDownloader instance to use for downloads
    """
    logger.info(f"Starting download task {task_id} for {len(songs)} songs")
    
    # Create output directory if it doesn't exist
    os.makedirs(downloader.output_dir, exist_ok=True)
    
    # Track global progress via the main downloader instance
    global_progress = {}
    
    # Process each song
    for i, song_data in enumerate(songs):
        try:
            song_id = f"song_{i}_{task_id[-6:]}"  # Create a unique ID for this song
            
            # Extract song title and artist if needed
            if isinstance(song_data, dict) and 'title' in song_data and 'artist' in song_data:
                title = song_data['title']
                artist = song_data['artist']
                logger.info(f"Downloading {title} by {artist}")
                
                # Create progress entry
                global_progress[song_id] = {
                    "song": f"{title} - {artist}",
                    "status": "searching",
                    "progress": 0,
                    "error": None
                }
                
                # Update global downloader progress
                if hasattr(downloader, 'progress'):
                    downloader.progress[song_id] = DownloadProgress(
                        song=f"{title} - {artist}",
                        status='searching',
                        progress=0
                    )
                
                # Do the actual download
                try:
                    logger.info(f"Starting download for: {title} by {artist}")
                    
                    # Create search query
                    search_query = f"{title} {artist} audio"
                    
                    # Set up download options
                    safe_title = re.sub(r'[^\w\s-]', '', title)
                    safe_artist = re.sub(r'[^\w\s-]', '', artist)
                    
                    output_template = os.path.join(downloader.output_dir, f"{safe_title} - {safe_artist}.%(ext)s")
                    
                    ytdl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': output_template,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '320',
                        }],
                        'default_search': 'ytsearch',
                    }
                    
                    # Try YouTube search
                    global_progress[song_id]["status"] = "downloading"
                    global_progress[song_id]["progress"] = 10
                    
                    # Update global progress
                    if hasattr(downloader, 'progress'):
                        downloader.progress[song_id].status = 'downloading'
                        downloader.progress[song_id].progress = 10
                    
                    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                        ydl.download([f"ytsearch1:{search_query}"])
                        
                        # Update progress
                        global_progress[song_id]["status"] = "finished"
                        global_progress[song_id]["progress"] = 100
                        
                        # Update global progress
                        if hasattr(downloader, 'progress'):
                            downloader.progress[song_id].status = 'finished'
                            downloader.progress[song_id].progress = 100
                        
                        logger.info(f"Download successful for: {title} by {artist}")
                        
                except Exception as err:
                    logger.error(f"YouTube search failed for {title}. Error: {str(err)}")
                    
                    # Try SoundCloud instead
                    try:
                        logger.info(f"Trying SoundCloud for: {title} by {artist}")
                        
                        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                            ydl.download([f"scsearch1:{title} {artist}"])
                            
                            # Update progress
                            global_progress[song_id]["status"] = "finished"
                            global_progress[song_id]["progress"] = 100
                            
                            # Update global progress
                            if hasattr(downloader, 'progress'):
                                downloader.progress[song_id].status = 'finished'
                                downloader.progress[song_id].progress = 100
                            
                            logger.info(f"SoundCloud download successful for: {title} by {artist}")
                            
                    except Exception as sc_err:
                        logger.error(f"SoundCloud search failed for {title}. Error: {str(sc_err)}")
                        
                        # Mark as error
                        global_progress[song_id]["status"] = "error"
                        global_progress[song_id]["error"] = str(sc_err)
                        
                        # Update global progress
                        if hasattr(downloader, 'progress'):
                            downloader.progress[song_id].status = 'error'
                            downloader.progress[song_id].error = str(sc_err)
                
            else:
                # Handle URLs or other formats using process_song
                logger.info(f"Processing song data: {song_data}")
                
                # Create progress entry
                global_progress[song_id] = {
                    "song": str(song_data)[:50],  # Limit length for display
                    "status": "processing",
                    "progress": 0,
                    "error": None
                }
                
                # Update global progress
                if hasattr(downloader, 'progress'):
                    downloader.progress[song_id] = DownloadProgress(
                        song=str(song_data)[:50],
                        status='processing',
                        progress=0
                    )
                
                # Call process_song
                result = downloader.process_song(song_data)
                
                # Log the result
                if result and result.get('success'):
                    logger.info(f"Successfully downloaded: {result.get('title')} by {result.get('artist')}")
                    
                    # Update progress
                    global_progress[song_id]["status"] = "finished"
                    global_progress[song_id]["progress"] = 100
                    global_progress[song_id]["song"] = f"{result.get('title')} - {result.get('artist')}"
                    
                    # Update global progress
                    if hasattr(downloader, 'progress'):
                        downloader.progress[song_id].status = 'finished'
                        downloader.progress[song_id].progress = 100
                        downloader.progress[song_id].song = f"{result.get('title')} - {result.get('artist')}"
                else:
                    error = result.get('error') if result else "Unknown error"
                    logger.error(f"Failed to download song: {error}")
                    
                    # Update progress
                    global_progress[song_id]["status"] = "error"
                    global_progress[song_id]["error"] = error
                    
                    # Update global progress
                    if hasattr(downloader, 'progress'):
                        downloader.progress[song_id].status = 'error'
                        downloader.progress[song_id].error = error
                
        except Exception as e:
            logger.error(f"Error processing song {song_data}: {str(e)}")
            song_id = f"song_{i}_{task_id[-6:]}"
            
            # Create progress entry if doesn't exist
            if song_id not in global_progress:
                global_progress[song_id] = {
                    "song": str(song_data)[:50],
                    "status": "error",
                    "progress": 0,
                    "error": str(e)
                }
            else:
                global_progress[song_id]["status"] = "error"
                global_progress[song_id]["error"] = str(e)
            
            # Update global progress
            if hasattr(downloader, 'progress'):
                if song_id not in downloader.progress:
                    downloader.progress[song_id] = DownloadProgress(
                        song=str(song_data)[:50],
                        status='error',
                        error=str(e)
                    )
                else:
                    downloader.progress[song_id].status = 'error'
                    downloader.progress[song_id].error = str(e)
    
    # Ensure the global downloader has these progress entries
    if hasattr(downloader, 'progress') and not downloader.progress:
        downloader.progress = global_progress
    
    logger.info(f"Download task {task_id} completed") 