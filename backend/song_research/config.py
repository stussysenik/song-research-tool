"""Configuration for song download and search strategies."""

# Platform-specific search prefixes
PLATFORM_SEARCH_PREFIXES = {
    "youtube": "ytsearch:",
    "soundcloud": "scsearch:",
    "spotify": "spsearch:",
    "auto": ""  # Let yt-dlp auto-detect
}

# Platform-specific URL patterns for validation
PLATFORM_URL_PATTERNS = {
    "youtube": r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=)?([a-zA-Z0-9_-]{11})',
    "soundcloud": r'https?://(www\.)?soundcloud\.com/([^/]+)/([^/]+)(?:/)?(\S*)',
    "spotify": r'https?://(open\.)?spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)',
}

# Search strategies in order of preference
SEARCH_STRATEGIES = [
    {
        "name": "exact_match",
        "query_template": '{platform}"{title}" "{artist}"',
        "description": "Exact match with quotes around title and artist"
    },
    {
        "name": "official_version",
        "query_template": '{platform}"{title}" "{artist}" official',
        "description": "Search for official version"
    },
    {
        "name": "platform_specific",
        "query_template": '{platform_specific}"{title}" "{artist}"',
        "description": "Platform-specific search"
    },
    {
        "name": "url_construction",
        "description": "Try to construct a direct URL",
        "platforms": ["soundcloud", "youtube"]
    },
    {
        "name": "fallback",
        "query_template": '{platform}{title} {artist}',
        "description": "Simple search without quotes",
        "require_validation": True
    }
]

# yt-dlp configuration defaults
DEFAULT_YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'extract_flat': False,
    'skip_download': False,
    'outtmpl': '%(title)s - %(uploader)s.%(ext)s'
}

# Similarity thresholds for validation
SIMILARITY_THRESHOLDS = {
    "title": 0.7,    # Minimum similarity score for title
    "artist": 0.6,   # Minimum similarity score for artist
    "combined": 0.65  # Minimum combined score
} 