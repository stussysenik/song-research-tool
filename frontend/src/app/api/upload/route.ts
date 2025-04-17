import { NextRequest, NextResponse } from "next/server"
import type { UploadResponse } from "@/types/api"

export const maxDuration = 300 // 5 minutes max for file processing

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000"

// Test the API connection
async function testApiConnection() {
  try {
    const response = await fetch(`${PYTHON_API_URL}/api/test`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    })
    return response.ok
  } catch (error) {
    console.error("API connection test failed:", error)
    return false
  }
}

export async function POST(req: NextRequest) {
  console.log("Starting upload process")
  console.log("Python API URL:", PYTHON_API_URL)
  
  try {
    // Test API connection first
    const isApiConnected = await testApiConnection()
    if (!isApiConnected) {
      console.error("Cannot connect to Python backend")
      return NextResponse.json(
        { error: "Cannot connect to the server. Please ensure the Python backend is running." },
        { status: 503 }
      )
    }

    const formData = await req.formData()
    const file = formData.get("file") as File | null

    if (!file) {
      console.error("No file provided in request")
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      )
    }

    console.log("File details:", {
      name: file.name,
      type: file.type,
      size: `${(file.size / 1024 / 1024).toFixed(2)}MB`
    })

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png']
    if (!allowedTypes.includes(file.type)) {
      console.error("Invalid file type:", file.type)
      return NextResponse.json(
        { error: "Invalid file type. Please upload a PDF, JPG, or PNG file" },
        { status: 400 }
      )
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024 // 10MB
    if (file.size > maxSize) {
      console.error("File too large:", `${(file.size / 1024 / 1024).toFixed(2)}MB`)
      return NextResponse.json(
        { error: "File size must be less than 10MB" },
        { status: 400 }
      )
    }

    // Forward to Python backend
    const pythonFormData = new FormData()
    pythonFormData.append("file", file)

    console.log("Sending request to Python backend:", `${PYTHON_API_URL}/api/extract-songs`)
    
    try {
      const response = await fetch(`${PYTHON_API_URL}/api/extract-songs`, {
        method: "POST",
        body: pythonFormData,
        headers: {
          'Accept': 'application/json',
        },
      })

      console.log("Python backend response status:", response.status)
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error("Python backend error:", errorData)
        throw new Error(errorData.detail || "Failed to process file")
      }

      const data: UploadResponse = await response.json()
      console.log("Python backend response data:", data)

      return NextResponse.json(data)

    } catch (error) {
      console.error("Error communicating with Python backend:", error)
      if (error instanceof TypeError && error.message.includes('fetch failed')) {
        return NextResponse.json(
          { error: "Could not connect to the server. Please ensure the Python backend is running." },
          { status: 503 }
        )
      }
      throw error
    }

  } catch (error) {
    console.error("Error processing file:", error)
    const message = error instanceof Error ? error.message : "Failed to process file"
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    )
  }
} 