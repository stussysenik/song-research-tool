import os
import logging
from fastapi import UploadFile, HTTPException
from ..ocr.gemini_extractor import GeminiExtractor
from ..models.song import Song

logger = logging.getLogger(__name__)

async def extract_songs_from_file(file: UploadFile):
    """
    Extract songs from a single file using OCR.
    This helper function allows reuse in both single and bulk extraction endpoints.
    
    Args:
        file: The uploaded file to process
        
    Returns:
        List of extracted songs
        
    Raises:
        HTTPException: If file processing fails
    """
    if not file:
        logger.error("No file provided")
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    if not file.content_type or not file.content_type.startswith(('image/', 'application/pdf')):
        logger.error(f"Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image or PDF")
    
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
            
        return song_list.songs
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            logger.info(f"Cleaning up temporary file: {temp_path}")
            os.remove(temp_path) 