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
        
        # Get response from Gemini
        response = model.generate_content(prompt)
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