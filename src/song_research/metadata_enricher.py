import os
import requests
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TXXX
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class MetadataEnricher:
    """Enrich MP3 files with additional metadata and cover art."""
    
    def __init__(self):
        self.lastfm_api_key = os.getenv("LASTFM_API_KEY", "")
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
    
    def enrich_file(self, file_path, title, artist):
        """Enrich an MP3 file with metadata and cover art."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
            
        try:
            # Get additional metadata from Last.fm
            metadata = self._get_track_info(title, artist)
            
            # Apply metadata to file
            if metadata:
                self._apply_metadata(file_path, metadata)
                logger.info(f"Enriched metadata for {file_path}")
                return True
            else:
                logger.warning(f"No metadata found for {title} by {artist}")
                return False
                
        except Exception as e:
            logger.error(f"Error enriching metadata: {str(e)}")
            return False
    
    def _get_track_info(self, title, artist):
        """Get track information from Last.fm."""
        if not self.lastfm_api_key:
            return None
            
        params = {
            "method": "track.getInfo",
            "api_key": self.lastfm_api_key,
            "artist": artist,
            "track": title,
            "format": "json",
            "autocorrect": 1
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "track" not in data:
                return None
                
            track_data = data["track"]
            
            # Extract useful metadata
            metadata = {
                "title": track_data.get("name", title),
                "artist": track_data.get("artist", {}).get("name", artist),
                "album": track_data.get("album", {}).get("title", ""),
                "cover_url": None,
                "genres": []
            }
            
            # Try to get album art
            if "album" in track_data and "image" in track_data["album"]:
                for img in track_data["album"]["image"]:
                    if img["size"] == "large" or img["size"] == "extralarge":
                        if img["#text"]:
                            metadata["cover_url"] = img["#text"]
                            break
            
            # Try to get genre tags
            if "toptags" in track_data and "tag" in track_data["toptags"]:
                metadata["genres"] = [tag["name"] for tag in track_data["toptags"]["tag"][:3]]
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching track info: {str(e)}")
            return None
    
    def _apply_metadata(self, file_path, metadata):
        """Apply metadata to an MP3 file."""
        try:
            # Load ID3 tags
            audio = ID3(file_path)
        except:
            # Create ID3 if it doesn't exist
            audio = ID3()
        
        # Set title
        if metadata.get("title"):
            audio["TIT2"] = TIT2(encoding=3, text=metadata["title"])
            
        # Set artist
        if metadata.get("artist"):
            audio["TPE1"] = TPE1(encoding=3, text=metadata["artist"])
            
        # Set album
        if metadata.get("album"):
            audio["TALB"] = TALB(encoding=3, text=metadata["album"])
            
        # Set genre tags as custom tags
        if metadata.get("genres"):
            audio["TXXX:GENRES"] = TXXX(encoding=3, desc="GENRES", text=", ".join(metadata["genres"]))
            
        # Add cover art if available
        if metadata.get("cover_url"):
            try:
                response = requests.get(metadata["cover_url"])
                img = Image.open(BytesIO(response.content))
                
                # Convert to JPEG if not already
                if img.format != "JPEG":
                    buffer = BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG")
                    img_data = buffer.getvalue()
                else:
                    img_data = response.content
                
                audio["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,  # Cover (front)
                    desc="Cover",
                    data=img_data
                )
            except Exception as e:
                logger.error(f"Error adding cover art: {str(e)}")
        
        # Save changes
        audio.save(file_path) 