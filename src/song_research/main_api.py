from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
    """Download multiple songs from song list"""
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
        
        # Start download in background
        asyncio.create_task(downloader.download_playlist(songs))
        
        return {
            "success": True,
            "message": f"Download of {len(songs)} songs started",
            "total": len(songs)
        }
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to download songs: {str(e)}"
        }

@app.get("/api/download/progress")
async def get_progress(song_key: Optional[str] = None):
    """Get download progress for all songs or a specific song"""
    return downloader.get_progress(song_key)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/process-songs/")
async def process_songs(
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