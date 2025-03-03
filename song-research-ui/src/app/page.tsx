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
    console.log('Songs extracted:', songList);
    setExtractedSongs(songList);
    setShowDownloader(true);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-orange-50 p-8">
      <div className="container mx-auto max-w-4xl">
        <h1 className="text-4xl font-bold text-center mb-10 text-blue-800">
          Song Research Tool
        </h1>
        
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8 border border-blue-100">
          <h2 className="text-2xl font-semibold mb-6 text-blue-700">Upload Playlist</h2>
          
          <div className="w-full mb-6">
            <div className="grid w-full grid-cols-2 gap-2 rounded-lg p-1 bg-gray-100">
              <button
                onClick={() => setActiveTab('single')}
                className={`rounded-md py-2 text-sm font-medium transition-colors ${
                  activeTab === 'single' 
                    ? 'bg-white shadow-sm text-primary' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Single File
              </button>
              <button
                onClick={() => setActiveTab('bulk')}
                className={`rounded-md py-2 text-sm font-medium transition-colors ${
                  activeTab === 'bulk' 
                    ? 'bg-white shadow-sm text-primary' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Bulk Upload
              </button>
            </div>
          </div>
          
          <div className="mt-2">
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
            <h2 className="text-2xl font-semibold mb-6 text-orange-700">Download Songs</h2>
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
