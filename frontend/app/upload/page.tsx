'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'

export default function UploadPage() {
  const router = useRouter()
  const { uploadPriceBook, loading, error } = usePriceBookStore()
  const [file, setFile] = useState<File | null>(null)
  const [manufacturer, setManufacturer] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
    } else {
      alert('Please select a PDF file')
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!file || !manufacturer) {
      alert('Please select a file and manufacturer')
      return
    }

    try {
      await uploadPriceBook(file, manufacturer)
      router.push('/')
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload PDF Price Book</h1>
          <p className="text-muted-foreground">
            Upload and parse manufacturer PDF price books
          </p>
        </div>

        {/* Upload Form */}
        <Card>
          <CardHeader>
            <CardTitle>Upload PDF</CardTitle>
            <CardDescription>
              Select a manufacturer and upload your PDF price book for parsing
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Manufacturer Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Manufacturer</label>
                <select
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  className="w-full p-2 border border-input rounded-md bg-background"
                  required
                >
                  <option value="">Select Manufacturer</option>
                  <option value="hager">Hager</option>
                  <option value="select_hinges">SELECT Hinges</option>
                  <option value="auto">Auto-detect</option>
                </select>
              </div>

              {/* File Upload */}
              <div className="space-y-2">
                <label className="text-sm font-medium">PDF File</label>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    dragActive 
                      ? 'border-primary bg-primary/5' 
                      : 'border-muted-foreground/25 hover:border-primary/50'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Upload className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <div className="space-y-2">
                      <p className="text-lg font-medium">
                        {file ? file.name : 'Drop your PDF here or click to browse'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Maximum file size: 50MB
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {/* File Preview */}
              {file && (
                <div className="flex items-center space-x-2 p-3 bg-muted rounded-lg">
                  <FileText className="h-5 w-5 text-primary" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setFile(null)}
                  >
                    Remove
                  </Button>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="flex items-center space-x-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-destructive" />
                  <p className="text-sm text-destructive">{error}</p>
                </div>
              )}

              {/* Submit Button */}
              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.back()}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!file || !manufacturer || loading}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload & Parse
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Supported Formats */}
        <Card>
          <CardHeader>
            <CardTitle>Supported Formats</CardTitle>
            <CardDescription>
              Information about supported manufacturers and formats
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <h4 className="font-semibold mb-3 flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  Hager Price Books
                </h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Finish codes (US3, US4, US10B, etc.)</li>
                  <li>• Adder rules and pricing</li>
                  <li>• Product SKUs and descriptions</li>
                  <li>• Effective dates</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  SELECT Hinges
                </h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Net-add options (CTW, EPT, EMS)</li>
                  <li>• TIPIT and Hospital Tip rules</li>
                  <li>• UL FR3 fire rating options</li>
                  <li>• Product specifications</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tips */}
        <Card>
          <CardHeader>
            <CardTitle>Tips for Best Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="font-semibold mb-2">For Digital PDFs:</h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Ensure text is selectable</li>
                  <li>• Tables should be properly formatted</li>
                  <li>• Use original PDF files when possible</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-2">For Scanned PDFs:</h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Ensure good image quality (300+ DPI)</li>
                  <li>• Text should be clearly readable</li>
                  <li>• OCR fallback will be used automatically</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
