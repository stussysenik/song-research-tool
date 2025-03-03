import React, { useState, useEffect } from 'react';
import { downloadSongPlaylist, getProgress, DownloadProgress } from '@/lib/api';
import toast from 'react-hot-toast';

interface DownloadManagerProps {
    songList?: string;
    onComplete?: () => void;
}

export default function DownloadManager({ songList, onComplete }: DownloadManagerProps) {
    const [isDownloading, setIsDownloading] = useState(false);
    const [progress, setProgress] = useState<Record<string, DownloadProgress>>({});
    const [error, setError] = useState<string | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [failedSongs, setFailedSongs] = useState<string[]>([]);
    const [totalSongs, setTotalSongs] = useState(0);
    const [completedSongs, setCompletedSongs] = useState(0);

    useEffect(() => {
        // If songList is provided directly, process it
        if (songList) {
            handleSongListDownload(songList);
        }
    }, [songList]);

    // Add a function to check if all downloads are complete
    const isAllComplete = (progressValues: Record<string, DownloadProgress>) => {
        const values = Object.values(progressValues);
        if (values.length === 0) return false;
        
        // Count completed and failed songs
        let completed = 0;
        let failed = 0;
        const newFailedSongs: string[] = [];
        
        values.forEach(item => {
            if (item.status === 'finished') {
                completed++;
            } else if (item.status === 'error') {
                failed++;
                newFailedSongs.push(item.song);
            }
        });
        
        // Update state with completed count and failed songs
        setCompletedSongs(completed);
        setFailedSongs(newFailedSongs);
        
        // All downloads are complete when all songs have either finished or failed
        return (completed + failed) === values.length && values.length > 0;
    };

    // Poll for progress updates
    useEffect(() => {
        let interval: NodeJS.Timeout;
        
        if (isDownloading) {
            interval = setInterval(async () => {
                try {
                    const currentProgress = await getProgress();
                    if (currentProgress && typeof currentProgress === 'object') {
                        // Filter out any invalid progress entries
                        const validProgress = Object.entries(currentProgress).reduce((acc, [key, value]) => {
                            if (value && value.song && value.status) {
                                acc[key] = value;
                            }
                            return acc;
                        }, {} as Record<string, DownloadProgress>);
                        
                        setProgress(validProgress);
                        
                        // Check if all downloads are complete
                        if (isAllComplete(validProgress)) {
                            setIsDownloading(false);
                            
                            // Show toast with completion info
                            if (failedSongs.length > 0) {
                                toast.error(`${completedSongs} songs downloaded, ${failedSongs.length} songs failed`);
                            } else {
                                toast.success(`All ${completedSongs} songs downloaded successfully`);
                            }
                            
                            onComplete?.();
                            // Clear the interval immediately
                            clearInterval(interval);
                        }
                    }
                } catch (err) {
                    console.error('Error fetching progress:', err);
                    setError(err instanceof Error ? err.message : 'Failed to fetch progress');
                }
            }, 1000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isDownloading, onComplete, completedSongs, failedSongs]);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (files && files.length > 0) {
            setFile(files[0]);
            setError(null);
        }
    };

    // Helper function to format song data, with special handling for SoundCloud 
    const formatSongData = (songLine: string): {title: string, artist: string} => {
        // Check if this is a SoundCloud URL
        if (songLine.includes('soundcloud.com')) {
            // Extract artist and title from SoundCloud URL format
            // Format: soundcloud.com/artist-name/song-title
            const match = songLine.match(/soundcloud\.com\/([^\/]+)\/([^\/\s]+)/);
            if (match) {
                const [_, artistSlug, titleSlug] = match;
                return {
                    title: titleSlug.replace(/-/g, ' '),
                    artist: artistSlug.replace(/-/g, ' ')
                };
            }
        }
        
        // Handle regular format
        let title, artist;
        if (songLine.includes(',')) {
            [title, artist] = songLine.split(',', 2);
        } else if (songLine.includes(' - ')) {
            [title, artist] = songLine.split(' - ', 2);
        } else {
            title = songLine;
            artist = 'Unknown';
        }
        
        return { 
            title: title.trim(), 
            artist: artist.trim() 
        };
    };

    const handleSongListDownload = async (content: string) => {
        try {
            setIsDownloading(true);
            setError(null);
            setFailedSongs([]);
            setCompletedSongs(0);
            
            console.log("Preparing to download songs:", content.split('\n').length);
            
            // Format the song data properly
            const songs = content.split('\n')
                .filter(line => line.trim()) // Remove empty lines
                .map(line => formatSongData(line));
                
            setTotalSongs(songs.length);
            console.log("Formatted songs data:", songs);
            
            // Make sure we're sending the proper structure
            const response = await downloadSongPlaylist({ songs: songs });
            
            if (!response.success) {
                throw new Error(response.message || 'Download failed');
            }
            
            toast.success(`Downloading ${songs.length} songs in the background`);
        } catch (err) {
            console.error("Download error:", err);
            setError(err instanceof Error ? err.message : 'An error occurred during download');
            
            toast.error(err instanceof Error ? err.message : 'Check console for details');
            setIsDownloading(false);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        
        try {
            const content = await file.text();
            handleSongListDownload(content);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to read file');
        }
    };

    if (isDownloading || Object.keys(progress).length > 0) {
        // Show download progress for songs
        return (
            <div className="space-y-6">
                <div className="flex justify-between items-center border-b pb-2">
                    <h2 className="text-xl font-semibold">
                        {isDownloading ? 'Downloading Songs...' : 'Download Complete'}
                    </h2>
                    <div className="text-text-secondary">
                        {completedSongs} of {totalSongs} complete
                        {failedSongs.length > 0 && ` (${failedSongs.length} failed)`}
                    </div>
                </div>
                
                <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
                    {Object.entries(progress).map(([key, item]) => {
                        const { song, status, progress: downloadProgress, error: songError } = item;
                        const [artist, title] = song.split(' - ');
                        
                        return (
                            <div key={key} className="border rounded-lg p-3 bg-white shadow-sm">
                                <div className="flex justify-between items-start">
                                    <div className="space-y-1">
                                        <div className="font-medium">{title}</div>
                                        <div className="text-sm text-text-secondary">{artist}</div>
                                    </div>
                                    <div className={`text-xs px-2 py-1 rounded-full ${
                                        status === 'error' ? 'bg-red-100 text-red-800' :
                                        status === 'finished' ? 'bg-green-100 text-green-800' :
                                        'bg-blue-100 text-blue-800'
                                    }`}>
                                        {status === 'error' ? 'Failed' :
                                         status === 'finished' ? 'Complete' :
                                         status === 'downloading' ? 'Downloading' :
                                         status === 'processing' ? 'Processing' :
                                         'Starting'}
                                    </div>
                                </div>
                                
                                {status === 'error' && (
                                    <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                                        {songError || 'Download failed'}
                                    </div>
                                )}
                                
                                {status !== 'error' && (
                                    <div className="mt-2">
                                        <div className="flex justify-between items-center text-xs mb-1">
                                            <span>{status}</span>
                                            <span>{Math.min(Math.round(downloadProgress * 100), 100)}%</span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                            <div
                                                className="bg-primary h-2 rounded-full transition-all duration-300"
                                                style={{ width: `${Math.min(downloadProgress * 100, 100)}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
                
                {failedSongs.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 animate-fade-in">
                        <h3 className="font-medium text-amber-800 mb-2">Failed Downloads ({failedSongs.length})</h3>
                        <ul className="list-disc pl-5 text-sm text-amber-700 space-y-1">
                            {failedSongs.map((song, idx) => (
                                <li key={idx}>{song}</li>
                            ))}
                        </ul>
                        <p className="text-xs text-amber-600 mt-2">
                            You may need to download these songs manually or try again later.
                        </p>
                    </div>
                )}
                
                {error && (
                    <div className="text-red-600 bg-red-50 p-4 rounded-lg border border-red-100 animate-fade-in">
                        {error}
                    </div>
                )}
            </div>
        );
    }

    // Show upload form when not downloading
    return (
        <div className="space-y-4 p-4">
            <div className="flex gap-4 items-center">
                <input
                    type="file"
                    accept=".csv,.txt"
                    onChange={handleFileChange}
                    className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100"
                    disabled={isDownloading}
                />
                <button
                    onClick={handleUpload}
                    disabled={!file || isDownloading}
                    className="px-4 py-2 bg-violet-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-violet-700"
                >
                    {isDownloading ? 'Downloading...' : 'Start Download'}
                </button>
            </div>

            {error && (
                <div className="text-red-600 bg-red-50 p-3 rounded-lg">
                    {error}
                </div>
            )}
            
            {songList && (
                <div className="mt-4">
                    <h3 className="font-medium mb-2">Ready to download {songList.split('\n').length} songs</h3>
                    <button
                        onClick={() => handleSongListDownload(songList)}
                        className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
                    >
                        Start Download
                    </button>
                </div>
            )}
        </div>
    );
} 