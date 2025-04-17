"use client"

import { useState } from 'react';
import FileUploadForm from '@/components/FileUploadForm';
import BulkUploadForm from '@/components/BulkUploadForm';
import DownloadManager from '@/components/DownloadManager';

export default function Home() {
  const [extractedSongs, setExtractedSongs] = useState<string | null>(null);
  const [showDownloader, setShowDownloader] = useState(false);
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single');

  const handleSongsExtracted = (songList: string) => {
    console.log('OCR extraction completed with results:', songList);
    setExtractedSongs(songList);
    setShowDownloader(true);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-orange-50 p-8">
      <div className="container mx-auto max-w-4xl">
        <h1 className="text-4xl font-bold text-center mb-10 text-blue-800">
          Song Research Tool
        </h1>
        
        <div className="bg-blue-100 rounded-lg p-4 mb-8 border border-blue-200">
          <h2 className="text-lg font-medium text-blue-800 mb-2">How this works:</h2>
          <ol className="list-decimal ml-5 text-sm text-blue-700">
            <li className="mb-2">
              <strong>OCR Stage:</strong> Upload a playlist image and our AI will extract song information
            </li>
            <li>
              <strong>Download Stage:</strong> We'll search for the extracted songs on streaming platforms
            </li>
          </ol>
          <p className="text-xs mt-2 text-blue-600">
            The process happens in two separate stages so you can see exactly what was extracted before attempting to download
          </p>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8 border border-blue-100">
          <h2 className="text-2xl font-semibold mb-6 text-blue-700">Upload Playlist</h2>
          
          <div className="w-full mb-6">
            <div className="flex space-x-1 rounded-lg p-1 bg-gray-100">
              <button
                onClick={() => setActiveTab('single')}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  activeTab === 'single' 
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-500 hover:bg-gray-200 hover:text-gray-700'
                }`}
              >
                Single File
              </button>
              <button
                onClick={() => setActiveTab('bulk')}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  activeTab === 'bulk' 
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-500 hover:bg-gray-200 hover:text-gray-700'
                }`}
              >
                Bulk Upload
              </button>
            </div>
          </div>
          
          <div className="mt-4">
            {activeTab === 'single' && (
              <FileUploadForm onSongsExtracted={handleSongsExtracted} />
            )}
            
            {activeTab === 'bulk' && (
              <BulkUploadForm onSongsExtracted={handleSongsExtracted} />
            )}
          </div>
        </div>
        
        {showDownloader && (
          <div className="bg-white rounded-xl shadow-lg p-8 border border-orange-100 animate-fade-in">
            <h2 className="text-2xl font-semibold mb-2 text-orange-700">Download Songs</h2>
            <p className="text-sm text-gray-600 mb-6">
              The OCR extraction is complete. You can now review the extracted songs and download them.
            </p>
            <DownloadManager 
              songList={extractedSongs || undefined} 
              onComplete={() => console.log('Download complete!')} 
            />
          </div>
        )}
      </div>
    </main>
  );
}
