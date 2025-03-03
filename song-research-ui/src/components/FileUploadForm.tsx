import React, { useState } from 'react';
import { extractSongsFromFile } from '@/lib/api';
import toast from 'react-hot-toast';

interface FileUploadFormProps {
  onSongsExtracted: (songs: string) => void;
}

export default function FileUploadForm({ onSongsExtracted }: FileUploadFormProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      console.log('Starting file upload:', file.name);
      const result = await extractSongsFromFile(file);
      console.log('Extraction result:', result);
      
      if (result.songs && result.songs.length > 0) {
        // Convert songs array to string format
        const songListText = result.songs
          .map(song => `${song.title},${song.artist}`)
          .join('\n');
          
        console.log('Converted song list:', songListText);
        toast.success(`Found ${result.songs.length} songs in your image`);
        onSongsExtracted(songListText);
      } else {
        setError('No songs could be extracted from the file.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <div className="p-4 bg-blue-50 rounded-lg mb-4">
        <h3 className="font-medium text-blue-800 mb-2">Upload your playlist in any of these formats:</h3>
        <ul className="list-disc pl-5 space-y-1 text-blue-700">
          <li>Image files (.jpg, .jpeg, .png)</li>
          <li>PDF documents (.pdf)</li>
          <li>Text files (.txt)</li>
          <li>CSV files (.csv)</li>
        </ul>
        <p className="text-xs mt-2 text-blue-600">
          For text/CSV files, use format: "Title,Artist" or "Title - Artist"
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="file"
          accept=".jpg,.jpeg,.png,.pdf,.txt,.csv"
          onChange={handleFileChange}
          className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 
                    file:text-sm file:font-medium file:bg-primary file:text-white
                    hover:file:bg-primary-hover cursor-pointer"
          disabled={isUploading}
        />
        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className="py-2 px-6 bg-primary text-white rounded-md hover:bg-primary-hover
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isUploading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </span>
          ) : (
            'Upload File'
          )}
        </button>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg">
          <p>{error}</p>
        </div>
      )}
    </div>
  );
} 