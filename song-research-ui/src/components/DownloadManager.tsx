import { useState, useEffect } from 'react';
import { downloadPlaylist, getProgress, DownloadProgress } from '@/lib/api';

interface DownloadManagerProps {
    songList?: string;
    onComplete?: () => void;
}

export default function DownloadManager({ songList, onComplete }: DownloadManagerProps) {
    const [isDownloading, setIsDownloading] = useState(false);
    const [progress, setProgress] = useState<Record<string, DownloadProgress>>({});
    const [error, setError] = useState<string | null>(null);
    const [file, setFile] = useState<File | null>(null);

    // Start download when songList is provided
    useEffect(() => {
        if (songList) {
            handleSongListDownload(songList);
        }
    }, [songList]);

    // Check if all downloads are complete or errored
    const isAllComplete = (progress: Record<string, DownloadProgress>) => {
        const progressValues = Object.values(progress);
        // First check if we have any valid progress entries
        if (!progressValues.length) {
            return false;
        }
        return progressValues.every(
            p => p && p.status && (p.status === 'finished' || p.status === 'error')
        ) && progressValues.some(p => p && p.status === 'finished');
    };

    // Poll for progress updates
    useEffect(() => {
        let interval: NodeJS.Timeout;
        
        if (isDownloading) {
            interval = setInterval(async () => {
                try {
                    const currentProgress = await getProgress();
                    if (currentProgress && typeof currentProgress === 'object' && !('song' in currentProgress)) {
                        // Filter out any invalid progress entries
                        const validProgress = Object.entries(currentProgress).reduce((acc, [key, value]) => {
                            if (value && value.song && value.status) {
                                acc[key] = value;
                            } else {
                                console.warn(`Invalid progress entry for ${key}:`, value);
                            }
                            return acc;
                        }, {} as Record<string, DownloadProgress>);
                        
                        setProgress(validProgress);
                        
                        // Check if all downloads are complete
                        if (isAllComplete(validProgress)) {
                            setIsDownloading(false);
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
    }, [isDownloading, onComplete]);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (files && files.length > 0) {
            setFile(files[0]);
            setError(null);
        }
    };

    const handleSongListDownload = async (content: string) => {
        try {
            setIsDownloading(true);
            setError(null);
            await downloadPlaylist({ songs: content });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
            setIsDownloading(false);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file first');
            return;
        }

        try {
            const content = await file.text();
            await handleSongListDownload(content);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
            setIsDownloading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'finished': return 'bg-green-600';
            case 'error': return 'bg-red-600';
            case 'processing': return 'bg-yellow-500';
            case 'downloading': return 'bg-violet-600';
            default: return 'bg-gray-400';
        }
    };

    const getStatusText = (p: DownloadProgress) => {
        if (!p || !p.status) {
            return 'Invalid status';
        }
        
        switch (p.status) {
            case 'finished': return '100% - Complete';
            case 'error': return p.error || 'Failed';
            case 'processing': return 'Converting to MP3...';
            case 'downloading': 
                return `${Math.round(p.progress || 0)}% - ${p.speed || 'N/A'} - ETA: ${p.eta || 'N/A'}`;
            case 'starting': return 'Starting...';
            default: return p.status;
        }
    };

    // If we have a songList prop, don't show the file upload UI
    if (songList) {
        return (
            <div className="space-y-4 p-4">
                {error && (
                    <div className="text-red-600 bg-red-50 p-3 rounded-lg">
                        {error}
                    </div>
                )}

                {Object.entries(progress).length > 0 && (
                    <div className="space-y-2">
                        {Object.entries(progress).map(([key, p]) => (
                            <div key={key} className="border rounded-lg p-3">
                                <div className="flex justify-between mb-1">
                                    <span className="font-medium">{p.song}</span>
                                    <span className={`text-sm ${p.status === 'error' ? 'text-red-500' : 'text-gray-500'}`}>
                                        {getStatusText(p)}
                                    </span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2.5">
                                    <div
                                        className={`h-2.5 rounded-full ${getStatusColor(p.status)} transition-all duration-300`}
                                        style={{ width: `${Math.min(100, p.progress)}%` }}
                                    />
                                </div>
                                {p.error && (
                                    <div className="mt-1 text-sm text-red-600 bg-red-50 p-2 rounded">
                                        <span className="font-medium">Error: </span>
                                        {p.error}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    }

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

            {Object.entries(progress).length > 0 && (
                <div className="space-y-2">
                    {Object.entries(progress).map(([key, p]) => (
                        <div key={key} className="border rounded-lg p-3">
                            <div className="flex justify-between mb-1">
                                <span className="font-medium">{p.song}</span>
                                <span className={`text-sm ${p.status === 'error' ? 'text-red-500' : 'text-gray-500'}`}>
                                    {getStatusText(p)}
                                </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div
                                    className={`h-2.5 rounded-full ${getStatusColor(p.status)} transition-all duration-300`}
                                    style={{ width: `${Math.min(100, p.progress)}%` }}
                                />
                            </div>
                            {p.error && (
                                <div className="mt-1 text-sm text-red-600 bg-red-50 p-2 rounded">
                                    <span className="font-medium">Error: </span>
                                    {p.error}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
} 