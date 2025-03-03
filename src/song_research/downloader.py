import re
import requests
from urllib.parse import urlparse
import os
import yt_dlp
import logging
from .metadata_enricher import MetadataEnricher
from .download_verification import DownloadVerifier

logger = logging.getLogger(__name__)

class SongDownloader:
    def __init__(self, platform_preference=None, output_dir='playlist'):
        self.output_dir = output_dir
        self.metadata_enricher = MetadataEnricher()
        self.download_verifier = DownloadVerifier()
    
    def process_song(self, song_data):
        """Process a song for download, handling both URLs and text queries."""
        if isinstance(song_data, str) and self._is_valid_url(song_data):
            return self.download_from_url(song_data)
        
        # Handle traditional title+artist format
        title, artist = self._parse_song_info(song_data)
        return self.download_song(title, artist)
    
    def _is_valid_url(self, text):
        """Check if the provided text is a valid URL."""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def download_from_url(self, url):
        """Download song directly from URL without search."""
        # Direct URL download is more reliable than search
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        
        ydl_opts = self.get_ydl_opts(output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'title': info.get('title', 'Unknown'),
                    'artist': info.get('uploader', 'Unknown'),
                    'success': True,
                    'filepath': f"{info.get('title', 'Unknown')} - {info.get('uploader', 'Unknown')}.mp3"
                }
        except Exception as e:
            return {
                'title': url,
                'artist': 'Unknown',
                'success': False,
                'error': str(e)
            }

    def download_song(self, title, artist):
        """Download a song using a multi-strategy approach."""
        # Try different search strategies in order of reliability
        result = None
        
        # Strategy 1: Exact phrase with artist and title
        exact_search_query = f'ytsearch:"${title}" "${artist}"'
        result = self._try_download(exact_search_query, title, artist)
        if result and result['success']:
            return result
        
        # Strategy 2: Try with unique identifiers for disambiguation
        if not title.endswith('"') and not artist.endswith('"'):
            unique_search = f'ytsearch:"{title} {artist} official"'
            result = self._try_download(unique_search, title, artist)
            if result and result['success']:
                return result
        
        # Strategy 3: Platform-specific search for SoundCloud
        soundcloud_search = f'scsearch:"{title} {artist}"'
        result = self._try_download(soundcloud_search, title, artist)
        if result and result['success']:
            return result
        
        # Strategy 4: Fallback to direct URL construction for SoundCloud
        # Convert artist and title to URL-friendly format
        sc_artist = self._to_url_format(artist)
        sc_title = self._to_url_format(title)
        soundcloud_url = f"https://soundcloud.com/{sc_artist}/{sc_title}"
        
        # Check if this URL exists before trying to download
        if self._url_exists(soundcloud_url):
            result = self.download_from_url(soundcloud_url)
            if result and result['success']:
                return result
        
        # Final strategy: Basic search and validate results
        basic_search = f'ytsearch:{title} {artist}'
        result = self._try_download_with_validation(basic_search, title, artist)
        
        # If download was successful, verify and enrich
        if result and result['success'] and 'filepath' in result:
            # Verify the download
            verification = self.download_verifier.verify_download(
                result['filepath'], 
                title, 
                artist,
                download_info=result
            )
            
            result['verification'] = verification
            
            # If verification passed, enrich metadata
            if verification['verified']:
                enriched = self.metadata_enricher.enrich_file(
                    result['filepath'],
                    result['title'],
                    result['artist']
                )
                result['metadata_enriched'] = enriched
                
            # If verification failed badly, retry with next strategy
            elif verification['confidence'] < 0.4:
                # Log the issue
                logger.warning(f"Low confidence match ({verification['confidence']:.2f}) for {title} by {artist}")
                
                # Delete the bad download
                try:
                    os.remove(result['filepath'])
                except:
                    pass
                    
                # Try next strategy (recursive call with modified title/artist)
                # This is optional and would need careful implementation to avoid infinite loops
                if not title.endswith('"') and not artist.endswith('"'):
                    return self.download_song(f'"{title}"', f'"{artist}"')
        
        return result

    def _to_url_format(self, text):
        """Convert text to URL-friendly format for SoundCloud URLs."""
        # Remove special characters, convert to lowercase, replace spaces with hyphens
        url_text = re.sub(r'[^\w\s]', '', text).lower().strip().replace(' ', '-')
        return url_text

    def _url_exists(self, url):
        """Check if a URL exists and returns a valid response."""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code < 400
        except:
            return False

    def _try_download(self, search_query, title, artist):
        """Try downloading with a specific search query."""
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        ydl_opts = self.get_ydl_opts(output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                return {
                    'title': info.get('title', title),
                    'artist': info.get('uploader', artist),
                    'success': True,
                    'filepath': f"{info.get('title', title)} - {info.get('uploader', artist)}.mp3"
                }
        except Exception as e:
            return {
                'title': title,
                'artist': artist,
                'success': False,
                'error': str(e)
            }

    def _try_download_with_validation(self, search_query, expected_title, expected_artist):
        """Try downloading with validation of results against expected title/artist."""
        output_template = os.path.join(self.output_dir, '%(title)s - %(uploader)s.%(ext)s')
        ydl_opts = self.get_ydl_opts(output_template, download=False)  # Don't download yet
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info_dict:
                    # It's a playlist or a list of videos
                    entries = info_dict['entries']
                    if not entries:
                        return {'title': expected_title, 'artist': expected_artist, 'success': False, 
                                'error': 'No results found'}
                        
                    # Find the best matching entry
                    best_match = self._find_best_match(entries, expected_title, expected_artist)
                    
                    if best_match:
                        # Now download the best match
                        ydl_opts = self.get_ydl_opts(output_template, download=True)
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                            info = ydl2.extract_info(best_match['webpage_url'], download=True)
                            return {
                                'title': info.get('title', expected_title),
                                'artist': info.get('uploader', expected_artist),
                                'success': True,
                                'filepath': f"{info.get('title', expected_title)} - {info.get('uploader', expected_artist)}.mp3",
                                'match_score': best_match.get('match_score', 0)
                            }
                
                return {'title': expected_title, 'artist': expected_artist, 'success': False, 
                        'error': 'Could not find a good match'}
                    
        except Exception as e:
            return {
                'title': expected_title,
                'artist': expected_artist,
                'success': False,
                'error': str(e)
            }

    def _find_best_match(self, entries, expected_title, expected_artist):
        """Find the best matching entry based on title and artist similarity."""
        best_match = None
        best_score = 0
        
        for entry in entries:
            title = entry.get('title', '').lower()
            uploader = entry.get('uploader', '').lower()
            
            expected_title_lower = expected_title.lower()
            expected_artist_lower = expected_artist.lower()
            
            # Calculate similarity scores
            title_score = self._similarity_score(title, expected_title_lower)
            artist_score = self._similarity_score(uploader, expected_artist_lower)
            
            # Combined score with more weight on artist match
            combined_score = (title_score * 0.6) + (artist_score * 0.4)
            
            if combined_score > best_score and combined_score > 0.6:  # Threshold for acceptance
                best_score = combined_score
                entry['match_score'] = combined_score
                best_match = entry
        
        return best_match

    def _similarity_score(self, text1, text2):
        """Calculate similarity between two strings."""
        # Simple implementation - can be replaced with more sophisticated methods
        if text1 in text2 or text2 in text1:
            return 0.8
        
        # Count matching words
        words1 = set(text1.split())
        words2 = set(text2.split())
        common_words = words1.intersection(words2)
        
        if not words1 or not words2:
            return 0
        
        return len(common_words) / max(len(words1), len(words2)) 