'use client'

import { useEffect, useState } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Download,
  FileText,
  FileSpreadsheet,
  FileJson,
  CheckCircle2,
  Clock,
} from 'lucide-react'

type ExportFormat = 'excel' | 'csv' | 'json'

type ExportHistory = {
  id: string
  priceBookId: number
  manufacturer: string
  format: ExportFormat
  timestamp: Date
  status: 'completed' | 'processing' | 'failed'
  fileSize: string
}

export default function ExportCenterPage() {
  const { priceBooks, loading, fetchPriceBooks, exportPriceBook } = usePriceBookStore()
  const [exportHistory, setExportHistory] = useState<ExportHistory[]>([])
  const [exportingBooks, setExportingBooks] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchPriceBooks()

    // Load export history from localStorage
    const savedHistory = localStorage.getItem('export-history')
    if (savedHistory) {
      const parsed = JSON.parse(savedHistory)
      setExportHistory(parsed.map((h: any) => ({
        ...h,
        timestamp: new Date(h.timestamp)
      })))
    }
  }, [fetchPriceBooks])

  const handleExport = async (priceBookId: number, format: ExportFormat) => {
    const key = `${priceBookId}-${format}`
    setExportingBooks(prev => new Set(prev).add(key))

    try {
      await exportPriceBook(priceBookId, format)

      // Add to export history
      const book = priceBooks.find(b => b.id === priceBookId)
      if (book) {
        const newHistoryItem: ExportHistory = {
          id: `${Date.now()}-${priceBookId}`,
          priceBookId,
          manufacturer: book.manufacturer,
          format,
          timestamp: new Date(),
          status: 'completed',
          fileSize: '2.4 MB' // Placeholder
        }

        const updatedHistory = [newHistoryItem, ...exportHistory].slice(0, 10)
        setExportHistory(updatedHistory)

        // Save to localStorage
        localStorage.setItem('export-history', JSON.stringify(updatedHistory))
      }
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExportingBooks(prev => {
        const newSet = new Set(prev)
        newSet.delete(key)
        return newSet
      })
    }
  }

  const getFormatIcon = (format: ExportFormat) => {
    switch (format) {
      case 'excel':
        return <FileSpreadsheet className="h-5 w-5" />
      case 'csv':
        return <FileText className="h-5 w-5" />
      case 'json':
        return <FileJson className="h-5 w-5" />
    }
  }

  const getFormatColor = (format: ExportFormat) => {
    switch (format) {
      case 'excel':
        return 'text-success'
      case 'csv':
        return 'text-brand'
      case 'json':
        return 'text-warning'
    }
  }

  const completedBooks = priceBooks.filter(
    (b) => b.status === 'completed' || b.status === 'processed'
  )

  if (loading) {
    return (
      <div className="container-max p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading price books...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container-max p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-display font-medium mb-2">Export Center</h1>
        <p className="text-muted-foreground">
          Export price books to CSV, XLSX, or JSON formats
        </p>
      </div>

      {/* Format Options */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-success">
              <FileSpreadsheet className="h-5 w-5" />
              Excel (XLSX)
            </CardTitle>
            <CardDescription>
              Full-featured spreadsheet with formatting
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Multiple sheets</li>
              <li>• Formatted columns</li>
              <li>• Formulas supported</li>
              <li>• Best for analysis</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-brand">
              <FileText className="h-5 w-5" />
              CSV
            </CardTitle>
            <CardDescription>
              Plain text format compatible with all tools
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Universal compatibility</li>
              <li>• Lightweight files</li>
              <li>• Easy to parse</li>
              <li>• Best for imports</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-warning">
              <FileJson className="h-5 w-5" />
              JSON
            </CardTitle>
            <CardDescription>
              Structured data for API integration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Nested structures</li>
              <li>• Type preservation</li>
              <li>• API-ready format</li>
              <li>• Best for developers</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Available Price Books */}
      <Card>
        <CardHeader>
          <CardTitle>Available Price Books</CardTitle>
          <CardDescription>
            {completedBooks.length} price book{completedBooks.length !== 1 ? 's' : ''} ready to export
          </CardDescription>
        </CardHeader>
        <CardContent>
          {completedBooks.length > 0 ? (
            <div className="space-y-3">
              {completedBooks.map((book) => (
                <div
                  key={book.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-muted transition-colors"
                >
                  <div className="flex items-start gap-4 flex-1">
                    <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center">
                      <FileText className="h-6 w-6 text-muted-foreground" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold">{book.manufacturer}</h3>
                        {book.edition && (
                          <Badge variant="brand">{book.edition}</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{book.product_count.toLocaleString()} items</span>
                        {book.effective_date && (
                          <>
                            <span>•</span>
                            <span>Effective: {book.effective_date}</span>
                          </>
                        )}
                        <span>•</span>
                        <span>Uploaded {new Date(book.upload_date).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Export Buttons */}
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(book.id, 'excel')}
                      disabled={exportingBooks.has(`${book.id}-excel`)}
                      className="min-w-[90px]"
                    >
                      {exportingBooks.has(`${book.id}-excel`) ? (
                        <>
                          <Clock className="h-4 w-4 animate-spin" />
                          <span>Exporting...</span>
                        </>
                      ) : (
                        <>
                          <FileSpreadsheet className="h-4 w-4 text-success" />
                          <span>XLSX</span>
                        </>
                      )}
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(book.id, 'csv')}
                      disabled={exportingBooks.has(`${book.id}-csv`)}
                      className="min-w-[90px]"
                    >
                      {exportingBooks.has(`${book.id}-csv`) ? (
                        <>
                          <Clock className="h-4 w-4 animate-spin" />
                          <span>Exporting...</span>
                        </>
                      ) : (
                        <>
                          <FileText className="h-4 w-4 text-brand" />
                          <span>CSV</span>
                        </>
                      )}
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExport(book.id, 'json')}
                      disabled={exportingBooks.has(`${book.id}-json`)}
                      className="min-w-[90px]"
                    >
                      {exportingBooks.has(`${book.id}-json`) ? (
                        <>
                          <Clock className="h-4 w-4 animate-spin" />
                          <span>Exporting...</span>
                        </>
                      ) : (
                        <>
                          <FileJson className="h-4 w-4 text-warning" />
                          <span>JSON</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Download className="h-16 w-16 mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Price Books Available</h3>
              <p className="text-sm">Upload and process a price book to enable exports</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export History */}
      {exportHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Exports</CardTitle>
            <CardDescription>
              Your last {exportHistory.length} export{exportHistory.length !== 1 ? 's' : ''}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {exportHistory.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card"
                >
                  <div className="flex items-center gap-3">
                    <div className={getFormatColor(item.format)}>
                      {getFormatIcon(item.format)}
                    </div>
                    <div>
                      <div className="font-medium">{item.manufacturer}</div>
                      <div className="text-sm text-muted-foreground">
                        {item.format.toUpperCase()} • {item.fileSize} • {item.timestamp.toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <Badge
                    variant={
                      item.status === 'completed'
                        ? 'success'
                        : item.status === 'processing'
                        ? 'warning'
                        : 'error'
                    }
                  >
                    {item.status === 'completed' ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Completed
                      </>
                    ) : item.status === 'processing' ? (
                      <>
                        <Clock className="h-3 w-3 mr-1" />
                        Processing
                      </>
                    ) : (
                      'Failed'
                    )}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
