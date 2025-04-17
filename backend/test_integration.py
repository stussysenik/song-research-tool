#!/usr/bin/env python3
import os
import unittest
import sys
from song_research.ocr.gemini_extractor import GeminiExtractor

"""
Integration test to verify OCR extraction with the real IMG_5334.jpg file.
This test requires the GOOGLE_AI_API_KEY environment variable to be set.
"""

class IntegrationTest(unittest.TestCase):
    def setUp(self):
        # Check if API key is set
        self.api_key = os.environ.get("GOOGLE_AI_API_KEY")
        if not self.api_key:
            self.skipTest("GOOGLE_AI_API_KEY environment variable not set")
        
        # Path to the image file
        self.test_image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "IMG_5334.jpg"))
        if not os.path.exists(self.test_image_path):
            self.skipTest(f"Test image not found: {self.test_image_path}")
            
        print(f"Using image file: {self.test_image_path}")
        
    def test_ocr_extraction_with_real_image(self):
        """Test OCR extraction with the real image file."""
        # Initialize extractor
        extractor = GeminiExtractor(api_key=self.api_key)
        
        # Process the image
        print("Processing image with Gemini Vision API...")
        result = extractor.process_file(self.test_image_path)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertTrue(len(result.songs) > 0, "No songs extracted from the image")
        
        # Print the extracted songs
        print(f"Extracted {len(result.songs)} songs:")
        for i, song in enumerate(result.songs):
            print(f"{i+1}. {song.title} - {song.artist}")
            
        # Based on the actual extraction results, let's check for these artists/songs
        # Check for Ohmega Watts songs
        ohmega_songs = [song for song in result.songs if "Ohmega Watts" in song.artist]
        self.assertTrue(len(ohmega_songs) > 0, "No Ohmega Watts songs found")
        
        # Check for Specifics songs
        specifics_songs = [song for song in result.songs if "Specifics" == song.artist]
        self.assertTrue(len(specifics_songs) > 0, "No Specifics songs found")
        
        # Check for specific song titles that were extracted
        expected_songs = ["No Delay", "The Find", "My Tunes"]
        found_songs = [song.title.lower() for song in result.songs]
        
        for song in expected_songs:
            self.assertTrue(
                any(song.lower() in title for title in found_songs), 
                f"Expected song '{song}' not found in extracted titles"
            )
        
        # If we get here, the test passed
        print("✅ OCR extraction test passed successfully!")
        
if __name__ == "__main__":
    unittest.main() 