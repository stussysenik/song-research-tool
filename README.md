# How to run:

## Terminal 1: Start the backend (Python)
```bash
cd ~/Desktop/school/dev\ playground/DJ\ tools/valentines-playlist
export PYTHONPATH="$PWD"
python3 src/run.py
```

## Terminal 2: Start the frontend (Next.js)
```bash
cd ~/Desktop/school/dev\ playground/DJ\ tools/valentines-playlist/song-research-ui
bun dev
```

## Handling Port Conflicts

If you see the error: `ERROR: [Errno 98] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`, try one of these solutions:

### Option 1: Use a different port
```bash
# Start the backend on port 8001 instead of 8000
python3 src/run.py --port 8001
```

### Option 2: Find and kill the process using port 8000
```bash
# Find the process using port 8000
sudo lsof -i :8000

# Kill the process (replace PID with the process ID from the output above)
kill PID

# Then try running again
python3 src/run.py
```

### Option 3: Restart your computer
This will terminate all running processes and free up the port.


# Documentation: Valentine's Playlist Generator

A full-stack application for extracting song lists from images and downloading them as MP3s. Features both a web interface and CLI support.

## Features

### Core Functionality
- 📷 OCR Support: Extract song lists from images using Google's Gemini Vision API
- 🎵 Music Download: Download songs as high-quality MP3s
- 🌐 Web Interface: Modern React-based UI for easy interaction
- 💻 CLI Support: Command-line interface for automation
- 📊 Real-time Progress: Live download progress tracking

### Input Methods
- Image files (JPG, PNG)
- PDF documents
- Text files (CSV, TXT)
  - Supports "Title,Artist" format
  - Supports "Title - Artist" format

### Technical Features
- Frontend:
  - Next.js-based UI
  - Real-time progress updates
  - Error handling and display
  - Responsive design
  - File upload support
  - Progress visualization

- Backend:
  - FastAPI server
  - Async download support
  - Concurrent processing
  - Resource cleanup
  - Duplicate detection
  - Empty instance handling

## Setup

1. Install dependencies:
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd song-research-ui
npm install
```

2. Configure environment:
- Create `.env` file in root directory:
```
GOOGLE_AI_API_KEY=your_gemini_api_key
```
- Create `.env.local` in `song-research-ui`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Start the services:
```bash
# Backend
python3 src/run.py

# Frontend
cd song-research-ui
bun dev
```

## Usage

### Web Interface
1. Visit `http://localhost:3000`
2. Upload an image, PDF, or text file containing your song list
3. Monitor download progress in real-time
4. Find downloaded MP3s in the `playlist` directory

### CLI
```bash
# Process an image file
python src/run.py process image.jpg

# Process a text file
python src/run.py process songs.txt
```

## Current Status
- ✅ Working OCR with Gemini Vision API
- ✅ Functional song downloading
- ✅ Real-time progress tracking
- ✅ Error handling and recovery
- ✅ Resource cleanup
- ✅ Duplicate detection
- ✅ Empty instance handling
- ✅ Frontend-backend integration

## Dependencies
- Backend:
  - FastAPI
  - yt-dlp
  - Google Generative AI
  - Python 3.8+
  - uvicorn
  
- Frontend:
  - Next.js
  - React
  - Tailwind CSS
  - Bun (for development)

## Notes
- Requires a valid Google Gemini API key
- Downloads are processed concurrently (up to 4 at a time)
- Progress updates every second
- Automatic MP3 conversion
- High-quality audio (320kbps) 