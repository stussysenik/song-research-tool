import { useState } from 'react';

export default function UploadForm({ onSubmit, isLoading }) {
  const [file, setFile] = useState(null);
  const [directUrl, setDirectUrl] = useState('');
  const [songText, setSongText] = useState('');
  const [platform, setPlatform] = useState('');  // New state for platform
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    if (file) formData.append('file', file);
    if (directUrl) formData.append('direct_url', directUrl);
    if (songText) formData.append('song_text', songText);
    if (platform) formData.append('platform', platform);  // Add platform if selected
    
    onSubmit(formData);
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Existing form elements... */}
      
      {/* New platform selector */}
      <div>
        <label className="block text-sm font-medium">
          Platform (Optional - helps with accuracy)
        </label>
        <select
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
        >
          <option value="">Auto-detect</option>
          <option value="soundcloud">SoundCloud</option>
          <option value="youtube">YouTube</option>
          <option value="spotify">Spotify</option>
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Selecting a platform can improve download accuracy
        </p>
      </div>
      
      {/* Existing submit button... */}
    </form>
  );
} 