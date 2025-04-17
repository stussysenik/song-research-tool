import os
from typing import Optional
import google.generativeai as genai
from ..models.song import SongList, Song
import io
from PIL import Image, ImageEnhance, ImageFilter
import time
import logging

logger = logging.getLogger(__name__)

class GeminiExtractor:
    """Handles OCR text extraction using Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with API credentials."""
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
    def preprocess_image(self, image_data):
        """Preprocess the image to improve OCR quality."""
        try:
            # Open image from binary data
            image = Image.open(io.BytesIO(image_data))
            
            # Apply preprocessing steps
            # 1. Convert to grayscale for better text contrast
            if image.mode != 'L':
                image = image.convert('L')
                
            # 2. Resize image to improve text recognition (2x upscaling)
            width, height = image.size
            image = image.resize((width*2, height*2), Image.LANCZOS)
            
            # 3. Enhance contrast to make text more readable
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # 4. Apply slight sharpening to improve text edges
            image = image.filter(ImageFilter.SHARPEN)
            
            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}. Using original image.")
            return image_data
    
    def api_call_with_retry(self, model, prompt, image_data, max_retries=3):
        """Make API call with retry logic for network errors."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                return model.generate_content([
                    prompt,
                    {"mime_type": "image/jpeg", "data": image_data}
                ])
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                logger.warning(f"API call failed (attempt {retry_count}/{max_retries}): {error_msg}")
                
                if "NetworkError" in error_msg or "network" in error_msg.lower():
                    # Wait a bit longer between retries for network issues
                    wait_time = 2 ** retry_count  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Network error detected. Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    continue
                    
                if retry_count >= max_retries:
                    logger.error(f"Max retries ({max_retries}) reached. Giving up.")
                    raise
                
                # For non-network errors, shorter wait
                time.sleep(1)
        
        raise RuntimeError(f"Failed to call API after {max_retries} attempts")
    
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
            
            # Preprocess the image to improve text recognition
            processed_image = self.preprocess_image(image_data)
            
            # Create Gemini model - using gemini-1.5-flash model for budget-friendly OCR
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Improved prompt specifically for music player UIs
            prompt = """
            Extract all song titles and artists from this image. The image shows a music playlist or player interface.
            
            Pay special attention to:
            - Track listings with song titles and artist names
            - Modern music player UI elements (Apple Music, Spotify, YouTube Music, etc.)
            - Album listings
            - Different text sizes and formats
            
            For each song, identify:
            1. The exact song title (including any featured artists in the title)
            2. The primary artist name
            
            Return ONLY a clean JSON object with this exact format:
            {
              "songs": [
                {"title": "Song Title 1", "artist": "Artist Name 1"},
                {"title": "Song Title 2", "artist": "Artist Name 2"}
              ]
            }
            
            IMPORTANT:
            - Include EVERY song visible in the image
            - If the artist isn't visible or clear, use "Unknown" as the artist name
            - Do not include any explanations, just the JSON
            - Preserve the exact formatting of titles and artists, including capitalization
            - If text has (feat. Artist) in the title, keep it as part of the title
            - Ensure accuracy of transcription
            """
            
            # Process with Gemini (with retry logic)
            logger.info("Calling Gemini API to process image")
            response = self.api_call_with_retry(model, prompt, processed_image)
            logger.info("Successfully received response from Gemini API")
            
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
                
                # If JSON parsing failed, try fallback with different prompt
                if not song_list.songs:
                    # Try again with gemini-1.5-flash and a different prompt
                    logger.info("First extraction attempt yielded no songs. Trying with fallback prompt.")
                    fallback_model = genai.GenerativeModel('gemini-1.5-flash')
                    fallback_prompt = """
                    This is a music player interface screenshot. Extract all songs with their artists.
                    For each line in the playlist, identify:
                    - Song title
                    - Artist name
                    
                    Return in this simple format (one per line):
                    1. Title: Song Title 1, Artist: Artist Name 1
                    2. Title: Song Title 2, Artist: Artist Name 2
                    """
                    
                    fallback_response = self.api_call_with_retry(fallback_model, fallback_prompt, processed_image)
                    
                    # Look for Title: Artist patterns
                    title_artist_pattern = r'(?:Title|Song):\s*([^,]+),\s*(?:Artist|By|Singer):\s*([^\n]+)'
                    matches = re.finditer(title_artist_pattern, fallback_response.text, re.IGNORECASE)
                    for match in matches:
                        title = match.group(1).strip()
                        artist = match.group(2).strip()
                        song_obj = Song(
                            title=title, 
                            artist=artist,
                            source='OCR'
                        )
                        song_list.songs.append(song_obj)
                        
                    # If still no songs, try line-by-line parsing
                    if not song_list.songs:
                        logger.info("Fallback extraction yielded no songs. Trying line-by-line parsing.")
                        lines = response.text.strip().split('\n')
                        for line in lines:
                            # Parse "Artist - Title" format
                            if ' - ' in line:
                                parts = line.split(' - ', 1)
                                if len(parts) == 2:
                                    # Could be either Artist - Title or Title - Artist
                                    # For streaming UI screenshots, format is usually Title - Artist
                                    title = parts[0].strip()
                                    artist = parts[1].strip()
                                    song_obj = Song(
                                        title=title, 
                                        artist=artist,
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
        
        # Gemini 1.5 has a generous limit
        return estimated_tokens <= 10_000_000  # 10MB limit

    def extract_soundcloud_links(self, text: str) -> list:
        """
        Specialized method to extract SoundCloud songs from text.
        
        Args:
            text: Text that potentially contains SoundCloud links or song references
            
        Returns:
            List of Song objects
        """
        import re
        
        # Initialize the model with a SoundCloud-specific prompt
        model = genai.GenerativeModel('gemini-pro')
        
        # Create a prompt that focuses on SoundCloud content
        prompt = f"""
        Extract all songs from this SoundCloud content. The text below may contain song information
        from SoundCloud pages. Please identify all songs with their titles and artists.
        
        Text to analyze:
        {text}
        
        For each song, provide the exact song title and artist name in this exact format:
        Title: [song title]
        Artist: [artist name]
        
        If a SoundCloud URL is present, extract the song title and artist from the URL pattern.
        SoundCloud URLs typically follow the format: soundcloud.com/[artist-name]/[song-title]
        """
        
        try:
            # Get response from Gemini with retry
            response = self.api_call_with_retry(model, prompt, None, max_retries=2)
            extraction_result = response.text
            
            # Process the response to extract songs
            songs = []
            
            # First look for SoundCloud URLs
            soundcloud_pattern = r'soundcloud\.com/([^/]+)/([^/\s]+)'
            url_matches = re.finditer(soundcloud_pattern, text)
            
            for match in url_matches:
                artist = match.group(1).replace('-', ' ').title()
                title = match.group(2).replace('-', ' ').title()
                songs.append(Song(title=title, artist=artist))
            
            # Then look for Title/Artist pairs in the Gemini extraction
            title_pattern = r'Title: (.*?)\nArtist: (.*?)(?:\n|$)'
            title_matches = re.finditer(title_pattern, extraction_result)
            
            for match in title_matches:
                title = match.group(1).strip()
                artist = match.group(2).strip()
                # Only add if we don't already have this song
                if not any(s.title.lower() == title.lower() and s.artist.lower() == artist.lower() for s in songs):
                    songs.append(Song(title=title, artist=artist))
            
            return songs
            
        except Exception as e:
            logger.error(f"Failed to extract SoundCloud links: {str(e)}")
            return [] 