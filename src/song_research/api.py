from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional
import csv
from io import StringIO
from .core.downloader import PlaylistDownloader, DownloadProgress
from .ocr.gemini_extractor import GeminiExtractor
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

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

class SongList(BaseModel):
    songs: str  # CSV content as string

class DownloadRequest(BaseModel):
    title: str
    artist: str

@app.post("/api/download/song")
async def download_song(request: DownloadRequest) -> DownloadProgress:
    """Download a single song"""
    return await downloader.download_song(request.title, request.artist)

@app.post("/api/download/playlist")
async def download_playlist(songlist: SongList) -> List[DownloadProgress]:
    """Download multiple songs from CSV content"""
    try:
        # Parse CSV content
        songs: List[Tuple[str, str]] = []
        csv_file = StringIO(songlist.songs.strip())  # Strip whitespace
        reader = csv.reader(csv_file)
        
        # Skip empty header or handle no header
        header = next(reader, None)
        if not header or all(not cell.strip() for cell in header):
            logger.warning("Empty or invalid header in CSV")
            
        for row in reader:
            # Handle CSV format
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                songs.append((row[0].strip(), row[1].strip()))
            # Handle "Title - Artist" format
            elif len(row) == 1 and ' - ' in row[0]:
                parts = row[0].split(' - ', 1)
                title, artist = parts[0].strip(), parts[1].strip()
                if title and artist:  # Ensure neither is empty
                    songs.append((title, artist))
        
        if not songs:
            raise HTTPException(status_code=400, detail="No valid songs found in input. Each song must have both title and artist.")
            
        # Remove any duplicates while preserving order
        seen = set()
        unique_songs = []
        for song in songs:
            if song not in seen:
                seen.add(song)
                unique_songs.append(song)
        
        return await downloader.download_playlist(unique_songs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/download/progress")
async def get_progress(song_key: Optional[str] = None):
    """Get download progress for all songs or a specific song"""
    return downloader.get_progress(song_key)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

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