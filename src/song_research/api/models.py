from pydantic import BaseModel, Field
from typing import Optional, Union, List

class Song(BaseModel):
    """Model representing a song with metadata"""
    title: str
    artist: str
    album: Optional[str] = ""
    year: Optional[Union[int, None]] = None
    duration: Optional[Union[int, float, None]] = None
    
    class Config:
        # Allow extra fields to be provided without validation errors
        extra = "ignore"
        # Make validation more lenient
        validate_assignment = True
        # Convert types when possible
        smart_union = True 