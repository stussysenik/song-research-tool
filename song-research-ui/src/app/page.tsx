"use client"

import { useState } from "react"
import { useToast } from "@/hooks/use-toast"
import type { Song } from "@/types/api"

interface DownloadResult {
  song: string
  artist: string
  status: "success" | "error"
  message: string
  filename?: string
  path?: string
}

function SongExtractor() {
  const [loading, setLoading] = useState(false)
  const [songs, setSongs] = useState<Song[]>([])
  const [downloading, setDownloading] = useState(false)
  const [downloadResults, setDownloadResults] = useState<DownloadResult[]>([])
  const { toast } = useToast()

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    try {
      const file = e.target.files?.[0]
      if (!file) return

      setLoading(true)
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || "Failed to process file")
      }

      const data = await response.json()
      setSongs(data.songs || [])

      toast({
        title: "Success",
        description: `Extracted ${data.songs.length} songs from ${file.name}`,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to process file"
      toast({
        variant: "destructive",
        title: "Error",
        description: message,
      })
    } finally {
      setLoading(false)
    }
  }

  const downloadAllSongs = async () => {
    if (downloading || !songs.length) return
    
    try {
      setDownloading(true)
      setDownloadResults([])
      
      const response = await fetch("/api/download-song", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(songs),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || "Failed to download songs")
      }

      const data = await response.json()
      if (data.results) {
        setDownloadResults(data.results)
      }

      toast({
        title: "Success",
        description: data.message || `Started downloading ${songs.length} songs`,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to download songs"
      toast({
        variant: "destructive",
        title: "Error",
        description: message,
      })
    } finally {
      setDownloading(false)
    }
  }

  const downloadFile = async (filename: string) => {
    try {
      const response = await fetch(`/api/download/file/${filename}`)
      if (!response.ok) {
        throw new Error("Failed to download file")
      }

      // Create a blob from the response
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      
      // Create a temporary link and click it
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      
      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to download file",
      })
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="space-y-8">
        {/* File Upload Section */}
        <div className="space-y-4">
          <h1 className="text-2xl font-bold">Song Extractor</h1>
          <div className="p-4 bg-blue-50 rounded-lg">
            <p className="text-sm">Upload an image of your playlist to extract songs</p>
          </div>
          <input
            type="file"
            accept=".jpg,.jpeg,.png"
            onChange={handleFileUpload}
            disabled={loading}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
          />
          {loading && (
            <div className="animate-pulse">
              <p className="text-blue-500">Processing file...</p>
            </div>
          )}
        </div>

        {/* Song List Section */}
        {songs.length > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold">
                {songs.length} Songs Found
              </h2>
              <button
                onClick={downloadAllSongs}
                disabled={downloading}
                className={`px-4 py-2 rounded-full text-white ${
                  downloading 
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {downloading ? 'Downloading...' : 'Download All Songs'}
              </button>
            </div>
            <div className="space-y-2">
              {songs.map((song, index) => {
                const downloadResult = downloadResults.find(
                  r => r.song === song.title && r.artist === song.artist
                )
                
                return (
                  <div key={index} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{song.title}</p>
                        <p className="text-sm text-gray-600">{song.artist}</p>
                      </div>
                      {downloadResult && (
                        <div className="flex items-center gap-2">
                          {downloadResult.status === "success" ? (
                            <button
                              onClick={() => downloadResult.filename && downloadFile(downloadResult.filename)}
                              className="px-3 py-1 text-sm bg-green-500 text-white rounded-full hover:bg-green-600"
                            >
                              Download MP3
                            </button>
                          ) : (
                            <span className="text-sm text-red-500">
                              {downloadResult.message}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Page() {
  return <SongExtractor />
}
