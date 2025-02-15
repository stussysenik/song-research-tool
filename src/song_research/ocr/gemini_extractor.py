import os
from typing import Optional
import google.generativeai as genai
from ..models.song import SongList, Song

class GeminiExtractor:
    """Handles OCR text extraction using Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with API credentials."""
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
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
            # Load the image
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Create Gemini model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Process with Gemini
            response = model.generate_content([
                "Extract song titles and artists from this image. Return the results in JSON format with 'songs' array containing objects with 'title' and 'artist' fields.",
                {"mime_type": "image/jpeg", "data": image_data}
            ])
            
            # Parse response into SongList
            try:
                # The response might be in text format, try to extract JSON part
                import json
                import re
                
                # Try to find JSON in the response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    if 'songs' in data:
                        for song in data['songs']:
                            if 'title' in song and 'artist' in song:
                                song_obj = Song(
                                    title=song['title'],
                                    artist=song['artist'],
                                    source='OCR'
                                )
                                song_list.songs.append(song_obj)
            except Exception as parse_error:
                raise RuntimeError(f"Failed to parse Gemini response: {str(parse_error)}")
            
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
        
        # Gemini Pro Vision has a more generous limit
        return estimated_tokens <= 4_000_000  # 4MB limit 