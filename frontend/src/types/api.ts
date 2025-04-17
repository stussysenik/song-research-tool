export interface Song {
  title: string
  artist: string
}

export interface UploadResponse {
  success: boolean
  songs?: Song[]
  error?: string
  download_path?: string
}

export interface ApiError {
  error: string
} 