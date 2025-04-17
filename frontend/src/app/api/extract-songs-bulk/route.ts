import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  console.log("Starting bulk extraction process");
  
  try {
    const formData = await req.formData();
    
    // Forward to Python backend
    const pythonFormData = new FormData();
    
    // Transfer all files from the request to the new FormData
    // FastAPI expects all files under the same parameter name 'files'
    for (const [key, value] of formData.entries()) {
      if (value instanceof File) {
        // Use 'files' as the parameter name for all files
        pythonFormData.append('files', value);
      }
    }
    
    const response = await fetch(`${PYTHON_API_URL}/api/extract-songs-bulk`, {
      method: "POST",
      body: pythonFormData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to process files");
    }
    
    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error("Error processing files:", error);
    const message = error instanceof Error ? error.message : "Failed to process files";
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
} 