import os
import unittest
import shutil
from unittest.mock import patch, MagicMock
from song_research.ocr.gemini_extractor import GeminiExtractor
from song_research.models.song import Song, SongList

class TestGeminiExtractor(unittest.TestCase):
    """Test the GeminiExtractor class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Mock GOOGLE_AI_API_KEY for testing
        os.environ['GOOGLE_AI_API_KEY'] = 'mock_api_key'
        self.extractor = GeminiExtractor()
        
        # Base directory is two levels up from this file
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.test_image_path = os.path.join(base_dir, 'IMG_5334.jpg')
        
        # Print debug info to help troubleshoot path issues
        print(f"Looking for image at: {self.test_image_path}")
        print(f"File exists: {os.path.exists(self.test_image_path)}")
        
        # If not found, use a mock file for testing
        if not os.path.exists(self.test_image_path):
            self.test_image_path = 'mock_image.jpg'
            with open(self.test_image_path, 'w') as f:
                f.write('mock content')
            self.mock_file_created = True
            print(f"Created mock file instead: {self.test_image_path}")
        else:
            self.mock_file_created = False
            print(f"Found real image file: {self.test_image_path} ({os.path.getsize(self.test_image_path)} bytes)")
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'mock_file_created') and self.mock_file_created:
            if os.path.exists(self.test_image_path):
                os.remove(self.test_image_path)
    
    @patch('google.generativeai.GenerativeModel')
    def test_process_file_json_response(self, mock_model_class):
        """Test processing a file with a proper JSON response."""
        # Mock the model response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with valid JSON - use realistic song data from IMG_5334.jpg
        mock_response = MagicMock()
        mock_response.text = """
        Here are the songs I found in the image:
        
        ```json
        {
          "songs": [
            {"title": "New Magic Wand", "artist": "Tyler, The Creator"},
            {"title": "Earfquake", "artist": "Tyler, The Creator"},
            {"title": "I Think", "artist": "Tyler, The Creator"},
            {"title": "Exactly What You Run From You End Up Chasing", "artist": "Tyler, The Creator"},
            {"title": "Running Out of Time", "artist": "Tyler, The Creator"},
            {"title": "Gone, Gone / Thank You", "artist": "Tyler, The Creator"}
          ]
        }
        ```
        """
        mock_model.generate_content.return_value = mock_response
        
        # Process the file
        result = self.extractor.process_file(self.test_image_path)
        
        # Assertions
        self.assertIsInstance(result, SongList)
        self.assertEqual(len(result.songs), 6)  # Number of songs from Tyler, The Creator
        self.assertEqual(result.songs[0].title, "New Magic Wand")
        self.assertEqual(result.songs[0].artist, "Tyler, The Creator")
        
        # Verify the model was called with the correct parameters
        mock_model.generate_content.assert_called_once()
        # First argument should be a list with a prompt and an image
        call_args = mock_model.generate_content.call_args[0][0]
        self.assertEqual(len(call_args), 2)
        self.assertIsInstance(call_args[0], str)  # Prompt
        self.assertIsInstance(call_args[1], dict)  # Image data
        self.assertEqual(call_args[1]['mime_type'], 'image/jpeg')
    
    @patch('google.generativeai.GenerativeModel')
    def test_process_file_text_response(self, mock_model_class):
        """Test processing a file with a text response (no proper JSON)."""
        # Mock the model response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with text format - use realistic data from IMG_5334.jpg
        mock_response = MagicMock()
        mock_response.text = """
        I found the following songs in the image:
        
        Title: New Magic Wand
        Artist: Tyler, The Creator
        
        Title: Earfquake
        Artist: Tyler, The Creator
        
        Title: I Think
        Artist: Tyler, The Creator
        
        There's also Running Out of Time by Tyler, The Creator visible at the bottom.
        """
        mock_model.generate_content.return_value = mock_response
        
        # Process the file
        result = self.extractor.process_file(self.test_image_path)
        
        # Assertions
        self.assertIsInstance(result, SongList)
        # Should find songs from Title/Artist format
        self.assertGreater(len(result.songs), 0)
        
        # Verify Title/Artist format detection
        title_artist_songs = [s for s in result.songs if s.title == "New Magic Wand" and s.artist == "Tyler, The Creator"]
        self.assertGreaterEqual(len(title_artist_songs), 1)
    
    def test_validate_token_usage(self):
        """Test token usage validation."""
        # Get the file size (either of the real file or mock file)
        file_size = os.path.getsize(self.test_image_path)
        print(f"Test image file size: {file_size} bytes")
        
        # For the mock file, we'll use the actual size of IMG_5334.jpg
        if self.mock_file_created:
            file_size = 493133  # 493KB - the actual size of IMG_5334.jpg
            
        self.assertTrue(self.extractor.validate_token_usage(file_size), 
                       f"File size {file_size} bytes should be within token limits")
        
        # Test with a file size that exceeds the token limit (100MB)
        self.assertFalse(self.extractor.validate_token_usage(100000000))  # 100MB
        
if __name__ == '__main__':
    unittest.main() 