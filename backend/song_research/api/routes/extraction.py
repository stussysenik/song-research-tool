from typing import List, Dict
from fastapi import File, UploadFile, APIRouter, HTTPException
from fastapi.routing import APIRouter
from ..helpers import extract_songs_from_file
from pydantic import BaseModel
from ...models.song import Song
import logging
import os
from ...ocr.gemini_extractor import GeminiExtractor

logger = logging.getLogger(__name__)
router = APIRouter()

# Define the missing model
class SongExtractionResponse(BaseModel):
    success: bool
    songs: List[Song]
    errors: List[Dict[str, str]]
    total_extracted: int
    failed_files: int

# Add a new endpoint for bulk image processing
@router.post("/extract-songs-bulk", response_model=SongExtractionResponse)
async def extract_songs_bulk(files: List[UploadFile] = File(...)):
    """
    Extract songs from multiple image files.
    Processes each file individually and combines the results.
    
    Args:
        files: List of uploaded files to process
        
    Returns:
        Combined results with success status, extracted songs, and any errors
    """
    results = []
    errors = []
    
    logger.info(f"Starting bulk extraction: {len(files)} files")
    
    for idx, file in enumerate(files):
        logger.info(f"[{idx+1}/{len(files)}] Processing: {file.filename} ({file.content_type})")
        try:
            # Process each file individually using our helper function
            songs = await extract_songs_from_file(file)
            logger.info(f"✓ Extracted {len(songs)} songs from {file.filename}")
            for song in songs:
                logger.info(f"  - {song.title} by {song.artist}")
            results.extend(songs)
        except Exception as e:
            logger.error(f"✗ Failed to process {file.filename}: {str(e)}")
            errors.append({"filename": file.filename, "error": str(e)})
    
    logger.info(f"Extraction complete. Total songs: {len(results)}, Failed files: {len(errors)}")
    return {
        "success": True,
        "songs": results,
        "errors": errors,
        "total_extracted": len(results),
        "failed_files": len(errors)
    }

@router.post("/extract")
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

            # Process with improved error handling
            try:
                logger.info("Processing file with GeminiExtractor")
                song_list = extractor.process_file(temp_path)
                
                if not song_list or not song_list.songs:
                    logger.error("No songs extracted from image")
                    raise HTTPException(
                        status_code=400, 
                        detail="No songs could be extracted from the image. Please check if the image clearly shows songs and artists."
                    )
                
                logger.info(f"Successfully extracted {len(song_list.songs)} songs")
                # Return songs in the expected format
                return {"songs": song_list.songs}
                
            except Exception as api_error:
                # Check if this is a network error
                error_msg = str(api_error)
                if "NetworkError" in error_msg or "network" in error_msg.lower():
                    logger.error(f"Network error processing file: {error_msg}")
                    raise HTTPException(
                        status_code=503,  # Service Unavailable 
                        detail="Network error connecting to AI service. Please try again later."
                    )
                # Other API errors
                logger.error(f"API error processing file: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Error processing file: {error_msg}")

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                logger.info(f"Cleaning up temporary file: {temp_path}")
                os.remove(temp_path)
                
    except HTTPException:
        # Re-raise HTTPExceptions to preserve status code
        raise
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}") 