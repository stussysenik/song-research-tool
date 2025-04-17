from pydantic import BaseModel, Field
from typing import List, Optional

class Song(BaseModel):
    """Model representing a single song."""
    title: str = Field(description="Song title")
    artist: str = Field(description="Artist name")
    source: Optional[str] = Field(None, description="Source of the song data (e.g., 'OCR', 'manual')")

class SongList(BaseModel):
    """Model representing a list of songs."""
    songs: List[Song] = Field(default_factory=list, description="List of songs extracted from document")
    source_file: Optional[str] = Field(None, description="Original file name if extracted from document")
    
    def to_csv(self, output_path: str) -> None:
        """Convert song list to CSV format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("title,artist\n")
            for song in self.songs:
                f.write(f"{song.title},{song.artist}\n") 