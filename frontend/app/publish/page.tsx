'use client'

import { useEffect, useState } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert } from '@/components/ui/alert'
import {
  Send,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  Eye,
  Play,
  RefreshCw,
  FileText,
} from 'lucide-react'

type PublishRun = {
  id: string
  priceBookId: number
  manufacturer: string
  timestamp: Date
  status: 'success' | 'failed' | 'running' | 'dry-run'
  duration: string
  created: number
  updated: number
  unchanged: number
  warnings: number
  logs?: string
}

export default function PublishPage() {
  const {
    priceBooks,
    publishHistory,
    loading,
    fetchPriceBooks,
    publishToBaserow,
    fetchPublishHistory
  } = usePriceBookStore()
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null)
  const [isDryRun, setIsDryRun] = useState(true)
  const [isPublishing, setIsPublishing] = useState(false)
  const [dryRunResult, setDryRunResult] = useState<PublishRun | null>(null)

  useEffect(() => {
    fetchPriceBooks()
    fetchPublishHistory()
  }, [fetchPriceBooks, fetchPublishHistory])

  const handlePublish = async () => {
    if (!selectedBookId) return

    setIsPublishing(true)

    try {
      const result = await publishToBaserow(selectedBookId, isDryRun)

      // Convert backend result to match UI format
      const book = priceBooks.find(b => b.id === selectedBookId)
      const unchanged = result.rows_processed - result.rows_created - result.rows_updated

      const publishRun: PublishRun = {
        id: result.id,
        priceBookId: result.price_book_id,
        manufacturer: result.manufacturer || book?.manufacturer || 'Unknown',
        timestamp: new Date(result.started_at),
        status: isDryRun ? 'dry-run' : (result.status === 'completed' ? 'success' : 'failed'),
        duration: `${result.duration_seconds?.toFixed(1) || '0'}s`,
        created: result.rows_created,
        updated: result.rows_updated,
        unchanged: unchanged,
        warnings: result.warnings?.length || 0,
        logs: 'View logs...'
      }

      if (isDryRun) {
        setDryRunResult(publishRun)
      } else {
        setDryRunResult(null)
        // History is automatically fetched by the store
      }
    } catch (error) {
      console.error('Publish failed:', error)
    } finally {
      setIsPublishing(false)
    }
  }

  const completedBooks = priceBooks.filter(
    (b) => b.status === 'completed' || b.status === 'processed'
  )

  const selectedBook = selectedBookId
    ? priceBooks.find(b => b.id === selectedBookId)
    : null

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
        <h1 className="text-display font-medium mb-2">Publish to Baserow</h1>
        <p className="text-muted-foreground">
          Publish price books to your Baserow database with field mapping and validation
        </p>
      </div>

      {/* Publish Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Select Price Book
          </CardTitle>
          <CardDescription>
            Choose a price book to publish to Baserow
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Price Book</label>
            <select
              className="w-full h-10 px-3 rounded-md border border-input bg-background"
              value={selectedBookId || ''}
              onChange={(e) => setSelectedBookId(Number(e.target.value))}
            >
              <option value="">Select a price book...</option>
              {completedBooks.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.manufacturer} - {book.edition || 'No edition'} ({book.product_count} items)
                </option>
              ))}
            </select>
          </div>

          {selectedBook && (
            <div className="p-4 rounded-lg bg-muted space-y-3">
              <h3 className="font-medium">Field Mapping Summary</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">SKU:</span>
                  <span className="font-mono">→ baserow_sku</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Model:</span>
                  <span className="font-mono">→ baserow_model</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Description:</span>
                  <span className="font-mono">→ baserow_description</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Price:</span>
                  <span className="font-mono">→ baserow_base_price</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Family:</span>
                  <span className="font-mono">→ baserow_family</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="font-mono">→ baserow_is_active</span>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="dry-run"
              checked={isDryRun}
              onChange={(e) => setIsDryRun(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="dry-run" className="text-sm cursor-pointer">
              Dry run (preview changes without publishing)
            </label>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <Button
              onClick={handlePublish}
              disabled={!selectedBookId || isPublishing}
              className="flex-1"
            >
              {isPublishing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  {isDryRun ? 'Running Dry Run...' : 'Publishing...'}
                </>
              ) : (
                <>
                  {isDryRun ? <Play className="h-4 w-4" /> : <Send className="h-4 w-4" />}
                  {isDryRun ? 'Run Dry Run' : 'Publish to Baserow'}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Dry Run Results */}
      {dryRunResult && (
        <Card className="border-brand">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-brand" />
              Dry Run Results
            </CardTitle>
            <CardDescription>
              Preview of changes that would be made to Baserow
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary Stats */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-success" />
                    Created
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-success">
                    {dryRunResult.created}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 text-warning" />
                    Updated
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-warning">
                    {dryRunResult.updated}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Unchanged
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">
                    {dryRunResult.unchanged}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-error" />
                    Warnings
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold text-error">
                    {dryRunResult.warnings}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Warnings */}
            {dryRunResult.warnings > 0 && (
              <Alert variant="warning">
                <AlertCircle className="h-4 w-4" />
                <div className="ml-2">
                  <strong>{dryRunResult.warnings} warnings detected</strong>
                  <p className="text-sm mt-1">
                    Some fields may have validation issues. Review logs before publishing.
                  </p>
                </div>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <FileText className="h-4 w-4" />
                View Logs
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setIsDryRun(false)
                  handlePublish()
                }}
              >
                <Send className="h-4 w-4" />
                Proceed with Publish
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Publish History */}
      {publishHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Publish History</CardTitle>
            <CardDescription>
              Recent publish runs to Baserow ({publishHistory.length} runs)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {publishHistory.map((run: any) => {
                // Calculate values for display
                const book = priceBooks.find(b => b.id === run.price_book_id)
                const unchanged = (run.rows_processed || 0) - (run.rows_created || 0) - (run.rows_updated || 0)
                const displayStatus = run.dry_run ? 'dry-run' : run.status

                return (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-muted transition-colors"
                >
                  <div className="flex items-start gap-4 flex-1">
                    <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center">
                      <Database className="h-6 w-6 text-muted-foreground" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold">{run.manufacturer || book?.manufacturer || 'Unknown'}</h3>
                        <Badge
                          variant={
                            displayStatus === 'completed' || displayStatus === 'success'
                              ? 'success'
                              : displayStatus === 'failed'
                              ? 'error'
                              : displayStatus === 'running'
                              ? 'warning'
                              : 'brand'
                          }
                        >
                          {displayStatus === 'completed' || displayStatus === 'success' ? (
                            <>
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                              Success
                            </>
                          ) : displayStatus === 'failed' ? (
                            <>
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Failed
                            </>
                          ) : displayStatus === 'running' ? (
                            <>
                              <Clock className="h-3 w-3 mr-1" />
                              Running
                            </>
                          ) : (
                            <>
                              <Eye className="h-3 w-3 mr-1" />
                              Dry Run
                            </>
                          )}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{new Date(run.started_at).toLocaleString()}</span>
                        <span>•</span>
                        <span>Duration: {run.duration_seconds?.toFixed(1)}s</span>
                        <span>•</span>
                        <span className="text-success">{run.rows_created} created</span>
                        <span className="text-warning">{run.rows_updated} updated</span>
                        {run.warnings && run.warnings.length > 0 && (
                          <>
                            <span>•</span>
                            <span className="text-error">{run.warnings.length} warnings</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <Button variant="outline" size="sm">
                    <FileText className="h-4 w-4" />
                    View Logs
                  </Button>
                </div>
              )})}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {completedBooks.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Send className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Price Books Available</h3>
            <p className="text-muted-foreground text-center max-w-sm">
              Upload and process a price book before publishing to Baserow
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
