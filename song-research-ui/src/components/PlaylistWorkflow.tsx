'use client';

import { useState } from 'react';
import DownloadManager from './DownloadManager';

interface Song {
    title: string;
    artist: string;
}

export default function PlaylistWorkflow() {
    const [step, setStep] = useState<'upload' | 'download'>('upload');
    const [songList, setSongList] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const checkBackendHealth = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/health`);
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
        const file = event.target.files?.[0];
        if (!file) return;

        try {
            setLoading(true);
            setError(null);
            
            // Check backend health first
            const isHealthy = await checkBackendHealth();
            if (!isHealthy) {
                throw new Error(
                    'Cannot connect to backend server. Please ensure it is running on http://localhost:8000 and try again.'
                );
            }

            console.log('Processing file:', file.name, 'Type:', file.type);

            const fileName = file.name.toLowerCase();
            
            // Handle different file types
            if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg') || 
                fileName.endsWith('.png') || fileName.endsWith('.pdf')) {
                // Image/PDF path - use OCR
                console.log('Using OCR for:', fileName);
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/extract`, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            // Don't set Content-Type header - browser will set it with boundary
                            'Accept': 'application/json',
                        },
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error('Server Error:', response.status, errorText);
                        
                        // Try to parse error as JSON
                        try {
                            const errorJson = JSON.parse(errorText);
                            throw new Error(errorJson.detail || 'Failed to process image');
                        } catch {
                            throw new Error(errorText || `Server error: ${response.status}`);
                        }
                    }

                    const data = await response.json();
                    console.log('OCR Results:', data);

                    if (!data.songs || data.songs.length === 0) {
                        throw new Error('No songs could be extracted from the image');
                    }

                    // Convert to CSV format
                    const csvContent = 'Title,Artist\n' + 
                        data.songs.map((song: Song) => `${song.title},${song.artist}`).join('\n');
                    
                    setSongList(csvContent);
                    setStep('download');
                    return;
                } catch (error) {
                    console.error('Error processing image:', error);
                    setError(error instanceof Error ? error.message : 'Failed to process image');
                }
            }

            // Text/CSV path
            if (fileName.endsWith('.txt') || fileName.endsWith('.csv')) {
                const content = await file.text();
                console.log('Parsing text file:', content.slice(0, 100) + '...');

                // Validate format
                const lines = content.trim().split('\n');
                if (lines.length === 0) {
                    throw new Error('File is empty');
                }

                const isValid = lines.every(line => {
                    return line.includes(',') || line.includes(' - ');
                });

                if (!isValid) {
                    throw new Error('Invalid format. Expected: "Title,Artist" or "Title - Artist" on each line');
                }

                setSongList(content);
                setStep('download');
                return;
            }

            throw new Error('Unsupported file type. Please use image, PDF, TXT, or CSV files.');

        } catch (err) {
            console.error('File processing error:', err);
            setError(err instanceof Error ? err.message : 'Failed to process file');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            {step === 'upload' ? (
                <div className="space-y-4">
                    <div className="p-4 bg-violet-50 rounded-lg">
                        <p className="text-sm text-violet-700">
                            Upload your playlist in any of these formats:
                        </p>
                        <ul className="mt-2 text-sm text-violet-600 list-disc list-inside">
                            <li>Image files (.jpg, .jpeg, .png)</li>
                            <li>PDF documents (.pdf)</li>
                            <li>Text files (.txt)</li>
                            <li>CSV files (.csv)</li>
                        </ul>
                        <p className="mt-2 text-xs text-violet-500">
                            For text/CSV files, use format: "Title,Artist" or "Title - Artist"
                        </p>
                    </div>
                    <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.pdf,.txt,.csv"
                        onChange={handleFileUpload}
                        disabled={loading}
                        className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100"
                    />
                    {loading && (
                        <div className="animate-pulse">
                            <p className="text-violet-500">Processing file...</p>
                        </div>
                    )}
                    {error && (
                        <div className="text-red-600 bg-red-50 p-3 rounded-lg">
                            {error}
                        </div>
                    )}
                </div>
            ) : (
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
                            alert('All downloads complete!');
                        }}
                    />
                </div>
            )}
        </div>
    );
} 