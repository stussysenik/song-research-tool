import React, { useState, useEffect } from 'react';
import { downloadSongPlaylist, getProgress, DownloadProgress, Song } from '@/lib/api';
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
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
    const [songsParsed, setSongsParsed] = useState<Song[]>([]);
    const [downloadStarted, setDownloadStarted] = useState(false);
    
    // New state to store the raw OCR results
    const [rawOcrResults, setRawOcrResults] = useState<string | null>(null);

    useEffect(() => {
        // If songList is provided directly, process it
        if (songList) {
            console.log('DownloadManager received songList prop:', songList);
            setRawOcrResults(songList); // Store the raw OCR results
            parseSongList(songList);
        }
    }, [songList]);

    const parseSongList = (songListText: string) => {
        if (!songListText.trim()) return;
        
        const songLines = songListText.split('\n').filter(line => line.trim());
        setTotalSongs(songLines.length);
        
        // Create Song objects from the text
        const parsedSongs = songLines.map(line => {
            return formatSongData(line);
        });
        
        setSongsParsed(parsedSongs);
        console.log('Parsed songs:', parsedSongs);
    };

    // Add a function to check if all downloads are complete
    const isAllComplete = (progressValues: Record<string, DownloadProgress>) => {
        const values = Object.values(progressValues);
        if (values.length === 0 || values.length < totalSongs) return false;
        
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
        return (completed + failed) === totalSongs && totalSongs > 0;
    };

    // Poll for progress updates
    useEffect(() => {
        let interval: NodeJS.Timeout;
        
        if (isDownloading && currentTaskId) {
            interval = setInterval(async () => {
                try {
                    const currentProgress = await getProgress(currentTaskId);
                    
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
                            setCurrentTaskId(null);
                            
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
                    toast.error('Could not update progress. Retrying...');
                }
            }, 2000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isDownloading, currentTaskId, onComplete, completedSongs, failedSongs, totalSongs]);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (files && files.length > 0) {
            setFile(files[0]);
            setError(null);
        }
    };

    // Helper function to format song data, with special handling for SoundCloud 
    const formatSongData = (songLine: string): Song => {
        // Check if this is a SoundCloud URL
        if (songLine.includes('soundcloud.com')) {
            // Extract artist and title from SoundCloud URL format
            // Format: soundcloud.com/artist-name/song-title
            const match = songLine.match(/soundcloud\.com\/([^\/]+)\/([^\/\s]+)/);
            if (match) {
                const [, artistSlug, titleSlug] = match;
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
            artist: artist ? artist.trim() : 'Unknown' 
        };
    };

    const handleStartDownload = async () => {
        try {
            setDownloadStarted(true);
            setIsDownloading(true);
            setError(null);
            setFailedSongs([]);
            setCompletedSongs(0);
            setProgress({});
            setCurrentTaskId(null);
            
            if (songsParsed.length === 0) {
                setError("No songs found in the provided list.");
                setIsDownloading(false);
                setDownloadStarted(false);
                return;
            }

            // Make sure we're sending the proper structure
            const response = await downloadSongPlaylist(songsParsed);
            
            if (!response.success || !response.task_id) {
                throw new Error(response.message || 'Failed to start download task.');
            }
            
            setCurrentTaskId(response.task_id);
            console.log('Download task started with ID:', response.task_id);
            toast.success(`Downloading ${songsParsed.length} songs in the background`);
        } catch (err) {
            console.error("Download error:", err);
            const errorMessage = err instanceof Error ? err.message : 'An error occurred during download';
            setError(errorMessage);
            toast.error(errorMessage);
            setIsDownloading(false);
            setDownloadStarted(false);
            setCurrentTaskId(null);
        }
    };

    // If no songList provided, return null
    if (!songList) return null;

    // If download hasn't started yet, show the initial state with OCR results and Start Download button
    if (!downloadStarted) {
        return (
            <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-blue-700">OCR Results</h2>
                
                {/* Display the raw OCR extraction */}
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                    <h3 className="font-medium text-gray-700 mb-2">Raw OCR Extraction:</h3>
                    <div className="text-xs font-mono bg-gray-100 p-3 rounded overflow-auto max-h-[200px]">
                        {rawOcrResults ? (
                            <pre>{rawOcrResults}</pre>
                        ) : (
                            <span className="text-gray-500">No OCR data available</span>
                        )}
                    </div>
                </div>
                
                <h2 className="text-2xl font-semibold text-blue-700">Parsed Songs ({songsParsed.length})</h2>
                
                <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                    <h3 className="font-medium text-blue-700 mb-2">Songs detected:</h3>
                    <div className="overflow-hidden overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-blue-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-blue-800 uppercase tracking-wider">Title</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-blue-800 uppercase tracking-wider">Artist</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {songsParsed.map((song, index) => (
                                    <tr key={index}>
                                        <td className="px-6 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{song.title || 'Unknown'}</td>
                                        <td className="px-6 py-2 whitespace-nowrap text-sm text-gray-500">{song.artist || 'Unknown'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div className="flex flex-col items-start gap-3">
                    <button 
                        onClick={handleStartDownload}
                        className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors font-medium"
                    >
                        Start Download
                    </button>
                    
                    <p className="text-sm text-gray-500">
                        This will attempt to find and download each song from YouTube or SoundCloud.
                        <br />Some songs may not be found if the extracted text is incorrect or the song is unavailable.
                    </p>
                </div>
                
                {error && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
                        <p className="font-medium">Error</p>
                        <p>{error}</p>
                    </div>
                )}
            </div>
        );
    }

    // Show download progress
    if (isDownloading || Object.keys(progress).length > 0) {
        // Show download progress for songs
        const sortedProgressEntries = Object.entries(progress)
            .sort(([, a], [, b]) => {
                // Simple sort: put downloading/processing first, then finished, then error
                const statusOrder: Record<string, number> = {
                    'downloading': 1,
                    'processing': 2,
                    'starting': 3,
                    'queued': 4,
                    'finished': 5,
                    'error': 6
                };
                // Handle unknown statuses by putting them last
                const orderA = statusOrder[a.status] ?? 99;
                const orderB = statusOrder[b.status] ?? 99;
                return orderA - orderB;
            });
            
        // Log the progress state being used for rendering
        console.log('Current progress state for rendering:', progress);
        
        return (
            <div className="space-y-6">
                {/* Header */} 
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-semibold text-orange-700">
                        {isDownloading ? 'Downloading Songs' : 'Download Complete'}
                    </h2>
                    <div className="text-sm text-gray-500">
                        {completedSongs} of {totalSongs} complete
                        {failedSongs.length > 0 && ` (${failedSongs.length} failed)`}
                    </div>
                </div>
                
                {/* Song Progress List */}
                <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
                    {sortedProgressEntries.map(([key, item]) => {
                        const { song, status, progress: downloadProgress = 0, error: songError } = item;
                        let title = 'Unknown Title';
                        let artist = 'Unknown Artist';
                        const songParts = song.split(' - ');
                        if (songParts.length >= 2) {
                            artist = songParts[0].trim();
                            title = songParts.slice(1).join(' - ').trim();
                        } else if (song.trim()) {
                            title = song.trim();
                        }
                        const percentage = Math.round(downloadProgress * 100);
                        
                        return (
                            <div key={key} className={`border rounded-lg p-4 ${status === 'error' ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex-1 mr-4">
                                        <div className="font-medium text-gray-800">{title}</div>
                                        <div className="text-sm text-gray-500">{artist}</div>
                                    </div>
                                    <div className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                                        status === 'error' ? 'bg-red-100 text-red-800' :
                                        status === 'finished' ? 'text-green-700' :
                                        'text-blue-700'
                                    }`}>
                                        {status === 'error' ? 'Failed' :
                                         status === 'finished' ? 'Complete' :
                                         status === 'downloading' ? 'Downloading' :
                                         status === 'processing' ? 'Processing' :
                                         'Pending'}
                                    </div>
                                </div>

                                {status === 'error' && (
                                    <div className="mt-1 text-sm text-red-600">
                                        {songError || 'Could not find stream'}
                                    </div>
                                )}

                                {status !== 'error' && status !== 'finished' && (
                                    <div className="mt-2">
                                        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                            <div 
                                                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                                                style={{ width: `${percentage}%` }}
                                            ></div>
                                        </div>
                                        <div className="text-right text-xs text-gray-500 mt-1">{percentage}%</div>
                                    </div>
                                )}
                                {status === 'finished' && (
                                    <div className="mt-2">
                                        <div className="w-full bg-green-100 rounded-full h-2 overflow-hidden">
                                            <div className="bg-green-500 h-2 rounded-full" style={{ width: `100%` }}></div>
                                        </div>
                                        <div className="text-right text-xs text-green-600 mt-1">100%</div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Failed Downloads Summary */}
                {failedSongs.length > 0 && (
                    <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h3 className="font-semibold text-yellow-800 mb-2">Failed Downloads ({failedSongs.length})</h3>
                        <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-700">
                            {failedSongs.map((failedSong, index) => {
                                let title = 'Unknown Title';
                                let artist = 'Unknown Artist';
                                const songParts = failedSong.split(' - ');
                                if (songParts.length >= 2) {
                                    artist = songParts[0].trim();
                                    title = songParts.slice(1).join(' - ').trim();
                                } else if (failedSong.trim()) {
                                    title = failedSong.trim();
                                }
                                return (
                                    <li key={index}>{artist} - {title}</li>
                                );
                            })}
                        </ul>
                        <p className="text-xs mt-3 text-yellow-600">
                            You may need to download these songs manually or try again later.
                        </p>
                    </div>
                )}
            </div>
        );
    }

    // If not downloading and no progress, return null or a placeholder
    // This ensures the component always returns something.
    return null;
} 