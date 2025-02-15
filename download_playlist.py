#!/usr/bin/env python3
import csv
import os
from pathlib import Path
import yt_dlp
import ssl

# Create unverified SSL context
ssl._create_default_https_context = ssl._create_unverified_context

def download_songs(songs, output_dir="playlist"):
    """Download songs from YouTube."""
    Path(output_dir).mkdir(exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': '%(title)s.%(ext)s',
        'paths': {'home': output_dir},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for title, artist in songs:
            try:
                print(f"\nDownloading: {artist} - {title}")
                ydl.download([f"ytsearch1:{artist} {title} audio"])
            except Exception as e:
                print(f"Failed: {str(e)}")
                continue

def main():
    try:
        # Read song list
        with open('song.txt', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            songs = []
            for row in reader:
                if len(row) >= 2:
                    songs.append((row[0].strip(), row[1].strip()))
                elif len(row) == 1 and ' - ' in row[0]:
                    title, artist = row[0].split(' - ', 1)
                    songs.append((title.strip(), artist.strip()))
        
        if not songs:
            print("No valid songs found in song.txt")
            return
        
        print(f"Found {len(songs)} songs to download...")
        download_songs(songs)
        print("\nDownload complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 