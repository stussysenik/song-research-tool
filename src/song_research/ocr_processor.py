import re

class OCRProcessor:
    def extract_songs_from_text(self, text):
        """Extract song information from OCR text with improved pattern matching."""
        songs = []
        
        # Look for direct URLs first
        url_pattern = r'https?://(?:www\.)?(?:soundcloud\.com|youtube\.com|youtu\.be|spotify\.com)/\S+'
        urls = re.findall(url_pattern, text)
        for url in urls:
            songs.append(url.strip())
        
        # Process remaining text for song-artist pairs
        # Remove already processed URLs
        for url in urls:
            text = text.replace(url, '')
        
        # Different formats to try
        formats = [
            # "Title - Artist" format
            r'([^-\n]+)\s*-\s*([^-\n]+)',
            # "Artist - Title" format
            r'([^-\n]+)\s*-\s*([^-\n]+)',
            # "Title by Artist" format
            r'([^\n]+)\s+by\s+([^\n]+)',
            # "Artist: Title" format
            r'([^:\n]+):\s*([^\n]+)'
        ]
        
        for pattern in formats:
            matches = re.findall(pattern, text)
            for match in matches:
                title, artist = match
                # Clean up extracted data
                title = title.strip()
                artist = artist.strip()
                
                # Skip if either is empty
                if not title or not artist:
                    continue
                    
                # Add to songs list
                song_info = {"title": title, "artist": artist}
                if song_info not in songs:
                    songs.append(song_info)
        
        # If we found no structured formats, try to extract track titles
        # This is a fallback for cases where the separator isn't clear
        if not songs:
            # Look for potential track patterns (numbered lists, etc.)
            track_patterns = [
                r'\d+\.\s+([^\n]+)',  # Numbered list: "1. Song name"
                r'•\s+([^\n]+)',      # Bullet points: "• Song name"
                r'\n([^\n]+)'         # Simply split by new lines as last resort
            ]
            
            for pattern in track_patterns:
                potential_tracks = re.findall(pattern, text)
                if potential_tracks:
                    for track in potential_tracks:
                        # Try to split into title/artist if possible
                        parts = re.split(r'\s+by\s+|\s*-\s*', track, 1)
                        if len(parts) == 2:
                            title, artist = parts
                            songs.append({"title": title.strip(), "artist": artist.strip()})
                        else:
                            # Store as title only, will need user intervention
                            songs.append({"title": track.strip(), "artist": "Unknown"})
                    break  # Use first successful pattern
        
        return songs
        
    def process_image(self, image_path):
        """Process an image with OCR to extract songs with improved accuracy."""
        # Use Gemini Vision API to analyze the image
        image_data = self._load_image(image_path)
        
        # Guide the model with a specific prompt for better extraction
        prompt = """
        This image may contain a music player, tracklist, playlist, or a song/album display.
        Please identify:
        1. All song titles and artists
        2. Any URLs or links to music
        3. Any platform information (YouTube, SoundCloud, Spotify, etc.)
        
        For each song, provide the title and artist in a clear format.
        If this is a single song being played, identify the song title and artist name.
        """
        
        response = self.model.generate_content([prompt, image_data])
        extracted_text = response.text
        
        # Process the extracted text to find songs
        songs = self.extract_songs_from_text(extracted_text)
        
        # If we identified a specific platform but no songs, try platform-specific extraction
        if "soundcloud" in extracted_text.lower() and not songs:
            songs = self._extract_soundcloud_specific(extracted_text)
        elif "spotify" in extracted_text.lower() and not songs:
            songs = self._extract_spotify_specific(extracted_text)
            
        return songs
        
    def _extract_soundcloud_specific(self, text):
        """Extract songs from SoundCloud-specific content."""
        # Use Gemini to analyze SoundCloud text more specifically
        prompt = f"""
        This is content from SoundCloud or about SoundCloud music.
        
        Content:
        {text}
        
        Please identify:
        1. Every song's EXACT title (including featuring artists in the title)
        2. The primary artist for each song
        3. Any SoundCloud URLs and the corresponding songs
        
        Format your response as a list with one song per line:
        Song 1 Title | Artist 1
        Song 2 Title | Artist 2
        etc.
        
        If a song title contains "feat." or "featuring" or "ft.", keep that as part of the title.
        """
        
        # Get enhanced extraction
        response = self.model.generate_content(prompt)
        
        # Parse the response
        songs = []
        for line in response.text.split('\n'):
            line = line.strip()
            if ' | ' in line:
                title, artist = line.split(' | ', 1)
                songs.append({
                    'title': title.strip(),
                    'artist': artist.strip()
                })
        
        # Also look for SoundCloud URLs
        soundcloud_pattern = r'soundcloud\.com/([^/]+)/([^/\s]+)'
        url_matches = re.finditer(soundcloud_pattern, text)
        
        for match in url_matches:
            artist = match.group(1).replace('-', ' ').title()
            title = match.group(2).replace('-', ' ').title()
            # Only add if not already in list
            if not any(s['title'].lower() == title.lower() and s['artist'].lower() == artist.lower() for s in songs):
                songs.append({
                    'title': title.strip(),
                    'artist': artist.strip()
                })
            
        return songs
        
    def _to_url_format(self, text):
        """Convert text to URL-friendly format."""
        # Remove special characters, convert to lowercase, replace spaces with hyphens
        url_text = re.sub(r'[^\w\s]', '', text).lower().strip().replace(' ', '-')
        return url_text 