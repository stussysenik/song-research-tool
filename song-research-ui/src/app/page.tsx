"use client"

import PlaylistWorkflow from '@/components/PlaylistWorkflow';

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Valentine's Playlist Downloader</h1>
        <div className="bg-white rounded-lg shadow-lg">
          <PlaylistWorkflow />
        </div>
      </div>
    </main>
  );
}
