'use client';

import { useState } from 'react';
import DownloadManager from './DownloadManager';
import { toast } from 'react-hot-toast';

interface Song {
    title: string;
    artist: string;
}

export default function PlaylistWorkflow() {
    const [step, setStep] = useState<'upload' | 'download'>('upload');
    const [songList, setSongList] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [files, setFiles] = useState<File[] | null>(null);

    const checkBackendHealth = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/health`);
            if (!response.ok) {
                throw new Error(`Health check failed: ${response.status}`);
            }
            return true;
        } catch (error) {
            console.error('Backend health check failed:', error);
            return false;
        }
    };

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        setLoading(true);
        setError(null);
        setFiles(Array.from(files));
        
        try {
            // Verify backend is available
            const isHealthy = await checkBackendHealth();
            if (!isHealthy) {
                throw new Error("Backend service is not available. Please try again later.");
            }
            
            // Create a FormData object with the file
            const formData = new FormData();
            formData.append('file', files[0]);
            
            // Display feedback about processing
            toast.success("Processing your file. This may take a moment...");
            
            // Call the extraction endpoint
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/extract`, {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to process file');
            }
            
            const data = await response.json();
            
            // Handle the extracted songs
            if (data.songs && data.songs.length > 0) {
                // Format songs for the DownloadManager
                const formattedSongs = data.songs.map((song: any) => 
                    `${song.title},${song.artist}`
                ).join('\n');
                
                setSongList(formattedSongs);
                setStep('download');
                toast.success(`Successfully extracted ${data.songs.length} songs`);
            } else {
                throw new Error('No songs could be extracted from the provided file');
            }
        } catch (err) {
            console.error("Upload error:", err);
            setError(err instanceof Error ? err.message : 'An error occurred');
            toast.error(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            {step === 'upload' && (
                <div className="space-y-6">
                    <div className="bg-blue-50 text-text-primary p-6 rounded-lg border border-blue-100 transition-all hover:shadow-md">
                        <h2 className="text-lg font-medium mb-3 text-primary">Upload your playlist in any of these formats:</h2>
                        <ul className="space-y-2 ml-5 text-text-secondary">
                            <li className="flex items-center gap-2">
                                <span className="text-accent">•</span> Image files (.jpg, .jpeg, .png)
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-accent">•</span> PDF documents (.pdf)
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-accent">•</span> Text files (.txt)
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="text-accent">•</span> CSV files (.csv)
                            </li>
                        </ul>
                        <p className="text-sm mt-3 text-text-secondary italic">For text/CSV files, use format: "Title,Artist" or "Title - Artist"</p>
                    </div>
                    
                    <div className="mt-6">
                        <button 
                            onClick={() => document.getElementById('file-upload')?.click()}
                            className="px-6 py-3 bg-primary text-white rounded-md hover:bg-primary-hover transition-all duration-200 font-medium"
                        >
                            Choose Files
                        </button>
                        <input
                            id="file-upload"
                            type="file"
                            className="hidden"
                            onChange={handleFileUpload}
                            accept=".jpg,.jpeg,.png,.pdf,.txt,.csv"
                        />
                        <span className="ml-3 text-text-secondary">{files?.length ? `${files.length} file(s) selected` : 'No file chosen'}</span>
                    </div>

                    {loading && (
                        <div className="flex items-center justify-center py-8 animate-fade-in">
                            <div className="relative">
                                <div className="h-16 w-16 rounded-full border-4 border-primary/30 border-t-primary animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-xs font-medium text-primary-hover">OCR</span>
                                </div>
                            </div>
                            <div className="ml-4">
                                <p className="font-medium text-primary">Processing your file</p>
                                <p className="text-sm text-text-secondary">Using Gemini Vision API to extract songs...</p>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="p-4 mt-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                            <p className="font-medium">Error</p>
                            <p>{error}</p>
                        </div>
                    )}
                </div>
            )}
            
            {step === 'download' && (
                <div>
                    <button
                        onClick={() => setStep('upload')}
                        className="mb-4 text-violet-600 hover:text-violet-700"
                    >
                        ← Back to Upload
                    </button>
                    <DownloadManager
                        songList={songList}
                        onComplete={() => {
                            toast.success('All downloads complete!');
                        }}
                    />
                </div>
            )}
        </div>
    );
} 