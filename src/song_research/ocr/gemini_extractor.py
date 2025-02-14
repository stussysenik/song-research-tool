import os
from typing import Optional
from google.cloud import aiplatform
from ..models.song import SongList, Song

class GeminiExtractor:
    """Handles OCR text extraction using Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with API credentials."""
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("Google AI API key is required")
        
        # Initialize Gemini client
        aiplatform.init(project=self.api_key)
        
    def process_file(self, file_path: str) -> SongList:
        """Process a file and extract song information.
        
        Args:
            file_path: Path to the PDF or image file
            
        Returns:
            SongList object containing extracted songs
            
        Raises:
            ValueError: If file format is not supported
            RuntimeError: If API processing fails
        """
        # Validate file
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
            
        # Initialize response
        song_list = SongList(source_file=os.path.basename(file_path))
        
        try:
            # Upload file to Gemini
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create Gemini model
            model = aiplatform.Model("gemini-2.0-flash")
            
            # Process with Gemini
            response = model.predict(
                instances=[{
                    "text": "Extract song list from document",
                    "file": file_content
                }],
                parameters={
                    "response_format": "json"
                }
            )
            
            # Parse response into SongList
            for item in response.predictions:
                if 'title' in item and 'artist' in item:
                    song = Song(
                        title=item['title'],
                        artist=item['artist'],
                        source='OCR'
                    )
                    song_list.songs.append(song)
            
            return song_list
            
        except Exception as e:
            raise RuntimeError(f"Failed to process file: {str(e)}")
            
    def validate_token_usage(self, file_size: int) -> bool:
        """Check if file size is within token limits.
        
        Args:
            file_size: Size of file in bytes
            
        Returns:
            bool: True if within limits, False otherwise
        """
        # Approximate token count (rough estimate)
        estimated_tokens = file_size / 4  # Rough estimate of bytes to tokens
        
        # Gemini 2.0 Flash limit is 1M tokens
        return estimated_tokens <= 1_000_000 