'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Upload, FileText, CheckCircle, AlertCircle, ChevronRight, Eye, Download, GitCompare, FileDown } from 'lucide-react'

type WizardStep = 1 | 2 | 3

export default function UploadPage() {
  const router = useRouter()
  const { uploadPriceBook, loading, error } = usePriceBookStore()

  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>(1)
  const [file, setFile] = useState<File | null>(null)
  const [manufacturer, setManufacturer] = useState('')
  const [dragActive, setDragActive] = useState(false)

  // Progress state (Step 2)
  const [parseProgress, setParseProgress] = useState(0)
  const [pagesParsed, setPagesParsed] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [eta, setEta] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [showLogs, setShowLogs] = useState(false)

  // Result state (Step 3)
  const [uploadedBookId, setUploadedBookId] = useState<string | null>(null)
  const [parsedData, setParsedData] = useState({
    effectiveDate: '',
    itemCount: 0,
    optionCount: 0,
    finishCount: 0,
  })

  // Drag & drop handlers
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
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile)
      }
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  // Step 1: Start upload
  const handleStartUpload = async () => {
    if (!file || !manufacturer) return

    setCurrentStep(2)
    setTotalPages(Math.floor(Math.random() * 50) + 20) // Simulated

    // Simulate parsing progress
    try {
      const result = await uploadPriceBook(file, manufacturer)

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setParseProgress((prev) => {
          if (prev >= 100) {
            clearInterval(progressInterval)
            return 100
          }
          const newProgress = prev + Math.random() * 15
          setPagesParsed(Math.floor((newProgress / 100) * totalPages))

          // Simulate logs
          if (newProgress > 25 && logs.length === 0) {
            setLogs(['[INFO] Starting PDF analysis...', '[INFO] Detected manufacturer format'])
          }
          if (newProgress > 50 && logs.length === 2) {
            setLogs(prev => [...prev, '[INFO] Extracting tables from page 15'])
          }
          if (newProgress > 75 && logs.length === 3) {
            setLogs(prev => [...prev, '[SUCCESS] Price data validated'])
          }

          return Math.min(newProgress, 100)
        })
      }, 500)

      // When complete, move to step 3
      setTimeout(() => {
        setCurrentStep(3)
        setParsedData({
          effectiveDate: '2024-01-01',
          itemCount: 1247,
          optionCount: 112,
          finishCount: 23,
        })
        if (result && 'id' in result) {
          setUploadedBookId(result.id as string)
        }
      }, 6000)
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  return (
    <div className="container-max p-6 space-y-6">
      {/* Header with Progress Indicator */}
      <div>
        <h1 className="text-display font-medium mb-2">Upload Price Book</h1>
        <p className="text-muted-foreground mb-6">
          Upload and parse manufacturer PDF price books
        </p>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((step) => (
            <div key={step} className="flex items-center">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                currentStep === step
                  ? 'bg-primary text-white'
                  : currentStep > step
                  ? 'bg-success text-white'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {currentStep > step ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <span className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-current text-xs">
                    {step}
                  </span>
                )}
                <span>
                  {step === 1 && 'Select & Upload'}
                  {step === 2 && 'Parse'}
                  {step === 3 && 'Summary'}
                </span>
              </div>
              {step < 3 && (
                <ChevronRight className="h-5 w-5 text-muted-foreground mx-2" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step 1: Select Manufacturer + Upload PDF */}
      {currentStep === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Select Manufacturer & Upload PDF</CardTitle>
            <CardDescription>
              Choose the manufacturer and upload their price book PDF (max 50MB)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Manufacturer Selection */}
            <div className="space-y-2">
              <Label htmlFor="manufacturer">Manufacturer</Label>
              <Select value={manufacturer} onValueChange={setManufacturer}>
                <SelectTrigger id="manufacturer">
                  <SelectValue placeholder="Select manufacturer..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto-detect (Recommended)</SelectItem>
                  <SelectItem value="hager">Hager</SelectItem>
                  <SelectItem value="select">SELECT Hinges</SelectItem>
                  <SelectItem value="continental">Continental Access</SelectItem>
                  <SelectItem value="lockey">Lockey</SelectItem>
                  <SelectItem value="alarlock">Alarm Lock</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* File Upload Area */}
            <div className="space-y-2">
              <Label>PDF File</Label>
              <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-all duration-fast ${
                  dragActive
                    ? 'border-primary bg-primary/5 scale-[1.02]'
                    : file
                    ? 'border-success bg-success/5'
                    : 'border-border hover:border-primary/50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  {file ? (
                    <>
                      <CheckCircle className="h-16 w-16 text-success mx-auto mb-4" />
                      <p className="text-h3 font-medium mb-2">{file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB · PDF
                      </p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="mt-4"
                        onClick={(e) => {
                          e.preventDefault()
                          setFile(null)
                        }}
                      >
                        Remove & Select Different File
                      </Button>
                    </>
                  ) : (
                    <>
                      <Upload className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                      <p className="text-h3 font-medium mb-2">
                        Drop your PDF here or click to browse
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Maximum file size: 50MB · Supported format: PDF
                      </p>
                    </>
                  )}
                </label>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <Alert variant="error">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Upload Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => router.push('/')}
              >
                Cancel
              </Button>
              <Button
                onClick={handleStartUpload}
                disabled={!file || !manufacturer}
              >
                Start Upload & Parse
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Parse Progress */}
      {currentStep === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Parsing PDF</CardTitle>
            <CardDescription>
              Extracting products, prices, and specifications...
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Progress Bar */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Progress</span>
                <span className="text-muted-foreground">{Math.round(parseProgress)}%</span>
              </div>
              <Progress value={parseProgress} className="h-2" />
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-semibold">{pagesParsed}</div>
                <div className="text-xs text-muted-foreground mt-1">Pages Parsed</div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-semibold">{totalPages}</div>
                <div className="text-xs text-muted-foreground mt-1">Total Pages</div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-semibold">
                  {parseProgress < 100 ? `~${Math.max(1, Math.round((100 - parseProgress) / 10))}m` : 'Done'}
                </div>
                <div className="text-xs text-muted-foreground mt-1">ETA</div>
              </div>
            </div>

            {/* Collapsible Live Log */}
            <div className="border rounded-lg">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
              >
                <span className="text-sm font-medium">Live Parse Log</span>
                <ChevronRight className={`h-4 w-4 transition-transform ${showLogs ? 'rotate-90' : ''}`} />
              </button>
              {showLogs && (
                <div className="border-t p-3 bg-neutral-950 text-neutral-100 dark:bg-neutral-900 font-mono text-xs space-y-1 max-h-48 overflow-y-auto custom-scrollbar">
                  {logs.map((log, i) => (
                    <div key={i} className="text-neutral-300">{log}</div>
                  ))}
                  {logs.length === 0 && (
                    <div className="text-neutral-500">Waiting for parse to start...</div>
                  )}
                </div>
              )}
            </div>

            {/* File Info */}
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <FileText className="h-8 w-8 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file?.name}</p>
                <p className="text-xs text-muted-foreground">
                  {manufacturer === 'auto' ? 'Auto-detect' : manufacturer} · {file ? (file.size / 1024 / 1024).toFixed(2) : '0'} MB
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Result Summary */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <Alert variant="success">
            <CheckCircle className="h-4 w-4" />
            <AlertTitle>Parsed Successfully!</AlertTitle>
            <AlertDescription>
              {parsedData.itemCount.toLocaleString()} items, {parsedData.optionCount} options, and {parsedData.finishCount} finishes extracted
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>Parse Summary</CardTitle>
                  <CardDescription className="mt-1.5">
                    {file?.name}
                  </CardDescription>
                </div>
                <Badge variant="brand">
                  Effective: {parsedData.effectiveDate}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="text-3xl font-semibold">{parsedData.itemCount.toLocaleString()}</div>
                  <div className="text-sm text-muted-foreground mt-1">Items</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-3xl font-semibold">{parsedData.optionCount}</div>
                  <div className="text-sm text-muted-foreground mt-1">Options</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-3xl font-semibold">{parsedData.finishCount}</div>
                  <div className="text-sm text-muted-foreground mt-1">Finishes</div>
                </div>
              </div>

              <Separator />

              {/* Actions */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium">What would you like to do?</h4>
                <div className="grid gap-3">
                  <Button
                    variant="default"
                    className="justify-start"
                    onClick={() => uploadedBookId && router.push(`/books/${uploadedBookId}`)}
                  >
                    <Eye className="h-4 w-4" />
                    Preview Parsed Data
                  </Button>
                  <Button
                    variant="outline"
                    className="justify-start"
                    onClick={() => router.push('/exports')}
                  >
                    <Download className="h-4 w-4" />
                    Export to CSV/XLSX
                  </Button>
                  <Button
                    variant="outline"
                    className="justify-start"
                    onClick={() => router.push('/diff')}
                  >
                    <GitCompare className="h-4 w-4" />
                    Go to Diff Review
                  </Button>
                </div>
              </div>

              <Separator />

              {/* Footer Actions */}
              <div className="flex justify-between">
                <Button
                  variant="ghost"
                  onClick={() => router.push('/')}
                >
                  Return to Dashboard
                </Button>
                <Button
                  onClick={() => {
                    setCurrentStep(1)
                    setFile(null)
                    setManufacturer('')
                    setParseProgress(0)
                    setLogs([])
                  }}
                >
                  Upload Another Price Book
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
