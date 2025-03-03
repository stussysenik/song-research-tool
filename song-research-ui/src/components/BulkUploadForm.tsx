import React, { useState } from 'react';
import { extractSongsBulk } from '@/lib/api';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui/button';

interface BulkUploadFormProps {
  onSongsExtracted: (songs: string) => void;
}

export default function BulkUploadForm({ onSongsExtracted }: BulkUploadFormProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const fileArray = Array.from(e.target.files);
      setFiles(fileArray);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      console.log(`Starting bulk upload of ${files.length} files`);
      
      // Show initial progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 5;
          return newProgress > 90 ? 90 : newProgress; // Cap at 90% until completion
        });
      }, 500);
      
      const result = await extractSongsBulk(files);
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      console.log('Extraction result:', result);
      
      if (result.songs && result.songs.length > 0) {
        // Convert songs array to string format
        const songListText = result.songs
          .map(song => `${song.title},${song.artist}`)
          .join('\n');
          
        console.log('Converted song list:', songListText);
        toast.success(`Found ${result.songs.length} songs in your files`);
        onSongsExtracted(songListText);
      } else {
        setError('No songs could be extracted from the files.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload files');
    } finally {
      setIsUploading(false);
    }
  };

  // Function to get a readable file size display
  const getFileSize = (size: number): string => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col space-y-2">
        <label className="text-sm font-medium text-gray-700">Upload Playlist Files</label>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => document.getElementById('bulk-file-upload')?.click()}
            variant="outline"
            className="w-40"
          >
            Select Files
          </Button>
          <input
            id="bulk-file-upload"
            type="file"
            multiple
            className="hidden"
            onChange={handleFileChange}
            accept=".jpg,.jpeg,.png,.pdf,.txt,.csv"
          />
          <span className="text-sm text-gray-500">
            {files.length > 0 ? `${files.length} file(s) selected` : 'No files chosen'}
          </span>
        </div>
      </div>

      {files.length > 0 && (
        <div className="p-4 max-h-60 overflow-y-auto border rounded-md shadow-sm bg-white">
          <h3 className="text-sm font-medium mb-2">Selected Files:</h3>
          <ul className="space-y-1">
            {files.map((file, index) => (
              <li key={index} className="text-xs flex justify-between">
                <span className="truncate max-w-[250px]">{file.name}</span>
                <span className="text-gray-500">{getFileSize(file.size)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={isUploading || files.length === 0}
        className="w-full"
      >
        {isUploading ? 'Processing...' : 'Extract Songs'}
      </Button>

      {isUploading && (
        <div className="space-y-2">
          {/* Simple progress bar made with Tailwind */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="text-xs text-center text-gray-500">
            Extracting songs using Gemini Vision API...
          </p>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
          {error}
        </div>
      )}
    </div>
  );
} 