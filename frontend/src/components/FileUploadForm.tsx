import React, { useState } from 'react';
import { extractSongsFromFile } from '@/lib/api';
import toast from 'react-hot-toast';

interface FileUploadFormProps {
  onSongsExtracted: (songs: string) => void;
}

export default function FileUploadForm({ onSongsExtracted }: FileUploadFormProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFile(files[0]);
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
      
      // Check if file has an accepted format
      const validExtensions = ['.jpg', '.jpeg', '.png', '.pdf', '.txt', '.csv'];
      const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      if (!validExtensions.includes(fileExtension)) {
        throw new Error(`File type ${fileExtension} is not supported. Please use JPG, PNG, PDF, TXT, or CSV files.`);
      }

      // Check file size (limit to 10MB)
      const maxSize = 10 * 1024 * 1024; // 10MB in bytes
      if (file.size > maxSize) {
        throw new Error(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum size is 10MB.`);
      }

      const result = await extractSongsFromFile(file);
      console.log('Raw extraction result:', result);
      
      if (result && result.length > 0) {
        // Create a raw string representation of the songs data
        // This preserves the original structure from the OCR
        const rawSongData = result.map(song => {
          const title = song.title || 'Unknown';
          const artist = song.artist || 'Unknown';
          return `${title},${artist}`;
        }).join('\n');
        
        console.log('Raw OCR output being passed:', rawSongData);
        toast.success(`Found ${result.length} songs in your file`);
        
        // Pass the raw song data to the callback
        onSongsExtracted(rawSongData);
      } else {
        setError('No songs could be extracted from the file. Please try a different file or format.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload file');
      toast.error(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <div className="p-6 bg-blue-50 rounded-lg mb-6 border border-blue-100">
        <h3 className="font-semibold text-blue-800 mb-3">Upload your playlist in any of these formats:</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
          <li>Image files (.jpg, .jpeg, .png)</li>
          <li>PDF documents (.pdf)</li>
          <li>Text files (.txt)</li>
          <li>CSV files (.csv)</li>
        </ul>
        <p className="text-xs mt-3 text-blue-600">
          For text/CSV files, use format: &quot;Title,Artist&quot; or &quot;Title - Artist&quot;
        </p>
      </div>

      <div className="flex items-center gap-4">
        <input
          id="file-upload-input"
          type="file"
          accept=".jpg,.jpeg,.png,.pdf,.txt,.csv"
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />

        <label 
          htmlFor="file-upload-input"
          className={`inline-block px-5 py-2 bg-white text-blue-700 border border-blue-300 rounded-md text-sm font-medium cursor-pointer hover:bg-blue-50 transition-colors ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          aria-label="Browse files"
        >
          Browse...
        </label>

        <span className="text-sm text-gray-600 flex-1 truncate">
          {file ? file.name : 'No file selected'}
        </span>

        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className="px-6 py-2 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary-hover
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label={isUploading ? "Processing..." : "Upload File"}
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
        <div className="mt-4 p-3 bg-red-100 text-red-700 border border-red-200 rounded-lg text-sm">
          <p>{error}</p>
        </div>
      )}
    </div>
  );
} 