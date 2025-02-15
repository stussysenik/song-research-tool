import sys
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to Python path
src_path = Path(__file__).parent
sys.path.append(str(src_path.parent))

from song_research.api import app

if __name__ == "__main__":
    print("Starting server...")
    print(f"Python path: {sys.path}")
    uvicorn.run(
        "song_research.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload for development
    ) 