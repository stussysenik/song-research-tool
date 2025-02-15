import { NextRequest, NextResponse } from "next/server"
import type { Song } from "@/types/api"

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000"

export async function POST(req: NextRequest) {
  console.log("Starting download process")
  console.log("Python API URL:", PYTHON_API_URL)
  
  try {
    const body = await req.json()
    const songs: Song[] = Array.isArray(body) ? body : [body]
    
    console.log("Download request:", {
      songCount: songs.length,
      songs: songs.map(s => `${s.title} - ${s.artist}`)
    })

    // Forward to Python backend
    const response = await fetch(`${PYTHON_API_URL}/api/download-song`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(songs),
    })

    console.log("Python backend response status:", response.status)

    const data = await response.json()
    
    if (!response.ok) {
      console.error("Python backend error:", data)
      throw new Error(data.detail || "Failed to download song(s)")
    }

    console.log("Download response:", data)
    return NextResponse.json(data)
    
  } catch (error) {
    console.error("Error downloading song(s):", error)
    const message = error instanceof Error ? error.message : "Failed to download song(s)"
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
}

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url)
    const filename = url.pathname.split('/').pop()
    
    if (!filename) {
      return NextResponse.json(
        { error: "No filename provided" },
        { status: 400 }
      )
    }

    // Forward to Python backend
    const response = await fetch(`${PYTHON_API_URL}/api/download/file/${filename}`)
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to get file")
    }

    // Get the file content as a blob
    const blob = await response.blob()
    
    // Create response with appropriate headers
    return new NextResponse(blob, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  } catch (error) {
    console.error("Error serving file:", error)
    const message = error instanceof Error ? error.message : "Failed to serve file"
    return NextResponse.json(
      { error: message },
      { status: 500 }
    )
  }
} 