"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { UploadCloud } from "lucide-react"
import { cn } from "@/lib/utils"

export interface FileUploadProps extends React.HTMLAttributes<HTMLDivElement> {
  onFileSelect?: (file: File) => void
  maxSize?: number // in bytes
  loading?: boolean
  error?: string
  accept?: string
}

export function FileUpload({
  onFileSelect,
  maxSize = 10 * 1024 * 1024, // 10MB default
  loading = false,
  error,
  accept = ".pdf,.jpg,.jpeg,.png",
  className,
  ...props
}: FileUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false)
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const handleFileSelect = React.useCallback((files: FileList | null) => {
    if (!files?.length) return

    const file = files[0]
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png']
    
    if (!allowedTypes.includes(file.type)) {
      alert('Please upload a PDF, JPG, or PNG file')
      return
    }

    if (file.size > maxSize) {
      alert(`File size must be less than ${maxSize / 1024 / 1024}MB`)
      return
    }

    setSelectedFile(file)
    onFileSelect?.(file)
  }, [maxSize, onFileSelect])

  const handleDragOver = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files)
  }, [handleFileSelect])

  return (
    <div className={cn("space-y-4", className)} {...props}>
      <div className="flex items-center gap-4">
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept={accept}
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={loading}
        />
        <Button 
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="gap-2"
        >
          <UploadCloud className="h-4 w-4" />
          {loading ? "Uploading..." : "Upload File"}
        </Button>
        <p className="text-sm text-muted-foreground">
          Supported formats: PDF, JPG, PNG
        </p>
      </div>

      <div 
        className={cn(
          "h-[300px] rounded-lg border-2 border-dashed transition-colors flex flex-col items-center justify-center gap-4",
          isDragging ? "border-primary bg-primary/5" : "border-muted",
          error && "border-destructive",
          className
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <UploadCloud 
          className={cn(
            "h-8 w-8",
            error ? "text-destructive" : "text-muted-foreground"
          )} 
        />
        {error ? (
          <div className="text-center">
            <p className="text-destructive font-medium">{error}</p>
            <p className="text-sm text-muted-foreground">
              Please try again
            </p>
          </div>
        ) : selectedFile ? (
          <div className="text-center">
            <p className="font-medium">{selectedFile.name}</p>
            <p className="text-sm text-muted-foreground">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <p className="text-muted-foreground text-center">
            Drag and drop a file here, or click upload
            <br />
            <span className="text-sm">
              PDF, JPG, or PNG up to {maxSize / 1024 / 1024}MB
            </span>
          </p>
        )}
      </div>
    </div>
  )
} 