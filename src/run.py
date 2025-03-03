#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import webbrowser
import time
import socket

def start_backend(port=8000):
    """Start the backend server process"""
    print("Starting backend server...")
    
    # Construct the command to run uvicorn with the specified port
    cmd = [
        "uvicorn", 
        "src.song_research.main_api:app", 
        "--port", str(port)
    ]
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(2)
        
        # Check if the process is still running
        if process.poll() is not None:
            # Process terminated, get the error output
            stdout, stderr = process.communicate()
            print("\n❌ Backend failed to start!\n")
            print("Output:\n", stdout)
            print("\nErrors:\n", stderr)
            sys.exit(1)
        
        return process
    except Exception as e:
        print(f"\n❌ Error starting backend: {str(e)}")
        sys.exit(1)

def open_frontend(port=8000):
    """Open the frontend in the default browser with port parameter"""
    # Include port as query parameter
    url = f"http://localhost:3000?port={port}"
    
    try:
        # Try to open the browser
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser: {str(e)}")
        print(f"Please manually open {url} in your browser")

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port+max_attempts-1}")

def main():
    parser = argparse.ArgumentParser(description="Valentine's Playlist Generator")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the backend server on")
    args = parser.parse_args()
    
    # Find an available port
    port = find_available_port()
    print(f"Starting server on port {port}")
    
    # Start the backend server with the specified port
    backend_process = start_backend(port=port)
    
    try:
        if not args.no_browser:
            # Open frontend, not backend URL
            open_frontend(port=port)
        
        print("\n🎵 Valentine's Playlist Generator is running!")
        print(f"* Backend API: http://localhost:{port}")
        print("* Frontend UI: http://localhost:3000 (start with: cd song-research-ui && npm run dev)")
        print("\nPress Ctrl+C to stop the server")
        
        # Keep the script running until interrupted
        backend_process.wait()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_process.terminate()
        backend_process.wait()
        print("Server stopped")

if __name__ == "__main__":
    main() 