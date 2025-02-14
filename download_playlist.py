#!/usr/bin/env python3
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import yt_dlp

def sanitize_filename(filename):
    """Remove invalid characters from filename."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()

def create_download_options(output_path):
    """Create yt-dlp options with quality preferences."""
    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extract_audio': True,
        'audio_quality': 0,  # Highest quality
        'prefer_ffmpeg': True,
        'keepvideo': False,
    }

def download_song(song_info, output_path):
    """Download a single song using yt-dlp."""
    title, artist = song_info
    search_query = f"{title} {artist} audio"
    
    # Create sanitized filename
    safe_filename = sanitize_filename(f"{title} - {artist}")
    
    options = create_download_options(output_path)
    options['outtmpl'] = os.path.join(output_path, safe_filename + '.%(ext)s')
    
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            # Search for the video
            result = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            print(f"✓ Downloaded: {title} - {artist}")
            return True
    except Exception as e:
        print(f"✗ Failed to download {title} - {artist}: {str(e)}")
        return False

def main():
    # Create playlist directory if it doesn't exist
    output_path = "playlist"
    Path(output_path).mkdir(exist_ok=True)
    
    # Read the song list
    with open('song.txt', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        songs = list(reader)
    
    print(f"Found {len(songs)} songs to download...")
    print("Starting downloads (this may take a while)...")
    
    # Download songs in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_song, song, output_path) for song in songs]
        
        # Wait for all downloads to complete
        successful = sum(1 for future in futures if future.result())
    
    print(f"\nDownload complete!")
    print(f"Successfully downloaded: {successful}/{len(songs)} songs")
    print(f"Files saved in: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    main() 