#!/usr/bin/env python3
import argparse
import os
from dotenv import load_dotenv
from song_research.ocr.gemini_extractor import GeminiExtractor

def main():
    """Main entry point for OCR song list extraction."""
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Extract song list from PDF/image using OCR')
    parser.add_argument('input_file', help='Path to PDF or image file containing song list')
    parser.add_argument('--output', '-o', help='Output CSV file path', default='song.txt')
    args = parser.parse_args()
    
    try:
        # Initialize extractor
        extractor = GeminiExtractor()
        
        # Validate file size
        file_size = os.path.getsize(args.input_file)
        if not extractor.validate_token_usage(file_size):
            print("Error: File too large for processing")
            return 1
            
        # Process file
        print(f"Processing {args.input_file}...")
        song_list = extractor.process_file(args.input_file)
        
        # Save results
        song_list.to_csv(args.output)
        print(f"Successfully extracted {len(song_list.songs)} songs to {args.output}")
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == '__main__':
    exit(main()) 