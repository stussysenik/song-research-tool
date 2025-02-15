# Valentine's Playlist Downloader

Downloads songs from a list into MP3 format.

## Setup

```bash
pip install yt-dlp
```

## Usage

1. Create `song.txt` with your songs (CSV format):
```
Title,Artist
GANMA,Lexie Liu
Midnight City,M83
```

2. Run:
```bash
python3 download_playlist.py
```

Songs will be downloaded to `playlist/` directory in MP3 format. 