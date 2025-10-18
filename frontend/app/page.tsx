'use client'

import { useEffect } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, Upload, BarChart3, GitCompare, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export default function Dashboard() {
  const {
    priceBooks,
    loading,
    error,
    fetchPriceBooks
  } = usePriceBookStore()

  useEffect(() => {
    fetchPriceBooks()
  }, [fetchPriceBooks])

  const completedBooks = priceBooks.filter(book => book.status === 'completed' || book.status === 'processed')
  const processingBooks = priceBooks.filter(book => book.status === 'processing')
  const totalProducts = priceBooks.reduce((sum, book) => sum + book.product_count, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container-max p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display font-medium mb-2">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your price book parsing and management system
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/upload">
            <Button>
              <Upload className="h-4 w-4" />
              Upload PDF
            </Button>
          </Link>
          <Link href="/diff">
            <Button variant="outline">
              <GitCompare className="h-4 w-4" />
              Compare
            </Button>
          </Link>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="error">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Statistics Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Price Books
            </CardTitle>
            <FileText className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-h1 font-semibold">{priceBooks.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {completedBooks.length} completed · {processingBooks.length} processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Products
            </CardTitle>
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-h1 font-semibold">{totalProducts.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Across all price books
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Completed
            </CardTitle>
            <div className="h-3 w-3 rounded-full bg-success"></div>
          </CardHeader>
          <CardContent>
            <div className="text-h1 font-semibold">{completedBooks.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Successfully parsed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Processing
            </CardTitle>
            <div className="h-3 w-3 rounded-full bg-warning animate-pulse"></div>
          </CardHeader>
          <CardContent>
            <div className="text-h1 font-semibold">{processingBooks.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Currently processing
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Price Books */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Price Books</CardTitle>
              <CardDescription className="mt-1.5">
                Latest uploaded and processed price books
              </CardDescription>
            </div>
            <Link href="/books">
              <Button variant="outline" size="sm">
                View All
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {priceBooks.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No price books yet</h3>
              <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                Upload your first PDF price book to get started with parsing and managing your catalog
              </p>
              <Link href="/upload">
                <Button>
                  <Upload className="h-4 w-4" />
                  Upload PDF
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {priceBooks.slice(0, 5).map((book) => (
                <div
                  key={book.id}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <FileText className="h-10 w-10 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium truncate">{book.manufacturer}</h4>
                        {book.edition && (
                          <Badge variant="neutral">{book.edition}</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                        {book.effective_date && (
                          <span>Effective: {book.effective_date}</span>
                        )}
                        <span>•</span>
                        <span>{book.product_count} items</span>
                        <span>•</span>
                        <span>{new Date(book.upload_date).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {book.status === 'completed' || book.status === 'processed' ? (
                      <Badge variant="success">Completed</Badge>
                    ) : book.status === 'processing' ? (
                      <Badge variant="warning">Processing</Badge>
                    ) : (
                      <Badge variant="error">Failed</Badge>
                    )}
                    <Link href={`/books/${book.id}`}>
                      <Button variant="ghost" size="sm">
                        View Details
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upload New Price Book</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Parse a new PDF price book from supported manufacturers
            </p>
            <Link href="/upload">
              <Button variant="outline" className="w-full">
                <Upload className="h-4 w-4" />
                Start Upload
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Compare Price Books</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Review differences between old and new price books
            </p>
            <Link href="/diff">
              <Button variant="outline" className="w-full">
                <GitCompare className="h-4 w-4" />
                View Diffs
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Publish to Baserow</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Sync parsed price books to your Baserow catalog
            </p>
            <Link href="/publish">
              <Button variant="outline" className="w-full">
                Publish Data
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
