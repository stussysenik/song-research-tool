import os
import re
import logging
import requests
import time
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class DownloadVerifier:
    """Verify downloaded songs against expected metadata."""
    
    def __init__(self):
        self.min_confidence = 0.7  # Minimum confidence threshold
    
    def verify_download(self, file_path, expected_title, expected_artist, download_info=None):
        """Verify a downloaded song matches expected metadata."""
        if not os.path.exists(file_path):
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": "File not found"
            }
        
        # Basic file size check
        file_size = os.path.getsize(file_path)
        if file_size < 100000:  # Less than 100KB is suspicious
            return {
                "verified": False,
                "confidence": 0.0,
                "reason": f"File too small ({file_size} bytes)"
            }
            
        # Calculate confidence score from multiple factors
        factors = []
        
        # 1. Title similarity
        if download_info and "title" in download_info:
            actual_title = download_info["title"]
            title_score = self._calculate_similarity(actual_title, expected_title)
            factors.append(("title", title_score, 0.4))  # 40% weight
            
        # 2. Artist similarity
        if download_info and "artist" in download_info:
            actual_artist = download_info["artist"]
            artist_score = self._calculate_similarity(actual_artist, expected_artist)
            factors.append(("artist", artist_score, 0.4))  # 40% weight
            
        # 3. File size sanity (penalize very small files)
        size_score = min(1.0, file_size / 2000000)  # Target ~2MB+ for quality songs
        factors.append(("file_size", size_score, 0.1))  # 10% weight
        
        # 4. File extension check
        _, ext = os.path.splitext(file_path)
        ext_score = 1.0 if ext.lower() == ".mp3" else 0.5
        factors.append(("format", ext_score, 0.1))  # 10% weight
        
        # Calculate weighted average confidence
        total_weight = sum(weight for _, _, weight in factors)
        if total_weight > 0:
            confidence = sum(score * weight for _, score, weight in factors) / total_weight
        else:
            confidence = 0.0
            
        # Build verification result
        result = {
            "verified": confidence >= self.min_confidence,
            "confidence": confidence,
            "factors": {name: score for name, score, _ in factors},
            "reason": "Verified" if confidence >= self.min_confidence else "Low confidence match"
        }
        
        return result
    
    def _calculate_similarity(self, text1, text2):
        """Calculate normalized similarity between two strings."""
        if not text1 or not text2:
            return 0.0
            
        # Normalize both texts
        text1 = self._normalize_text(text1)
        text2 = self._normalize_text(text2)
        
        # Direct match
        if text1 == text2:
            return 1.0
            
        # Substring match
        if text1 in text2 or text2 in text1:
            shorter = text1 if len(text1) < len(text2) else text2
            longer = text2 if len(text1) < len(text2) else text1
            return len(shorter) / len(longer) * 0.9  # 90% of perfect match
            
        # SequenceMatcher for more complex comparisons
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _normalize_text(self, text):
        """Normalize text for comparison."""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and extra spaces
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common filler words
        filler_words = ['official', 'audio', 'video', 'lyrics', 'ft', 'feat', 'remix', 'cover']
        for word in filler_words:
            text = re.sub(r'\b' + word + r'\b', '', text)
            
        # Remove common version indicators
        text = re.sub(r'\b(original|extended|radio|club|instrumental)\s+(version|mix|edit)\b', '', text)
        
        return text.strip() 