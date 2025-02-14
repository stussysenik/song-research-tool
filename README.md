# Playlist Downloader

This script helps you download a playlist of songs from your CSV file in high quality MP3 format.

## Prerequisites

1. Python 3.6 or higher
2. FFmpeg installed on your system

### Installing FFmpeg

- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg
  ```

- **Fedora:**
  ```bash
  sudo dnf install ffmpeg
  ```

## Setup

1. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Make the script executable:
   ```bash
   chmod +x download_playlist.py
   ```

## Usage

Simply run:
```bash
./download_playlist.py
```

The script will:
1. Create a 'playlist' directory if it doesn't exist
2. Read songs from song.txt
3. Download each song in high quality (320kbps MP3 when available)
4. Save the files in the 'playlist' directory

## Features

- Downloads high quality audio (320kbps MP3 when available)
- Handles special characters in filenames
- Downloads multiple songs concurrently
- Shows progress for each download
- Creates clean, organized filenames

## Notes

- The script uses yt-dlp to search and download audio from various sources
- Downloads are limited to 3 concurrent downloads to avoid rate limiting
- Failed downloads will be reported but won't stop the script 