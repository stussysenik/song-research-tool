import asyncio
from song_research.core.downloader import PlaylistDownloader
from song_research.models.song import Song

async def test_download():
    """Test function to verify the downloader works"""
    downloader = PlaylistDownloader()
    
    # Test with a well-known song that should be easy to find
    song = Song(title="Bohemian Rhapsody", artist="Queen")
    
    try:
        result = await downloader.download_song(song)
        print(f"Download result: {result}")
        print(f"Status: {result.status}")
        print(f"Progress: {result.progress}%")
        if result.error:
            print(f"Error: {result.error}")
        return True
    except Exception as e:
        print(f"Download failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_download())
    print(f"Download {'succeeded' if success else 'failed'}") 