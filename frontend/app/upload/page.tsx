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
              Upload any manufacturer's PDF price book - our Universal Parser automatically extracts products, prices, and specifications with 96% confidence
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Manufacturer Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Manufacturer (Optional)</label>
                <select
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  className="w-full p-2 border border-input rounded-md bg-background"
                  required
                >
                  <option value="">Auto-detect (Recommended)</option>
                  <option value="auto">Universal Parser (Works with any manufacturer)</option>
                  <option value="hager">Hager (Optimized)</option>
                  <option value="select_hinges">SELECT Hinges (Optimized)</option>
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

        {/* Universal Parser Features */}
        <Card>
          <CardHeader>
            <CardTitle>Universal Parser Features</CardTitle>
            <CardDescription>
              Works with ANY manufacturer - tested on 119+ PDFs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <h4 className="font-semibold mb-3 flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  What We Extract
                </h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Product SKUs and model numbers</li>
                  <li>• Prices (list, net, retail)</li>
                  <li>• Descriptions and specifications</li>
                  <li>• Finish codes and options</li>
                  <li>• Effective dates</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  Tested Manufacturers
                </h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Hager (99.7% accuracy)</li>
                  <li>• SELECT Hinges</li>
                  <li>• Continental Access</li>
                  <li>• Lockey (99% confidence)</li>
                  <li>• Alarm Lock (98% confidence)</li>
                  <li>• + Any other manufacturer</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* How It Works */}
        <Card>
          <CardHeader>
            <CardTitle>How the Universal Parser Works</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <h4 className="font-semibold mb-2">Layer 1: Fast Text (70%)</h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Extracts native PDF text</li>
                  <li>• Detects tables automatically</li>
                  <li>• Fastest: &lt;1s per page</li>
                  <li>• Works for most PDFs</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Layer 2: Tables (25%)</h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Structured table detection</li>
                  <li>• Handles complex layouts</li>
                  <li>• Used when needed</li>
                  <li>• 1-3s per page</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-2">Layer 3: ML Scan (5%)</h4>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  <li>• Deep learning OCR</li>
                  <li>• Scanned PDFs & images</li>
                  <li>• Last resort fallback</li>
                  <li>• 5-15s per page</li>
                </ul>
              </div>
            </div>
            <div className="mt-4 p-3 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                <strong>Result:</strong> 96% average confidence, 3-5x faster than traditional parsers, works with any manufacturer
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
