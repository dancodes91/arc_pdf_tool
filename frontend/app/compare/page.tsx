'use client'

import { useEffect, useState } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Compare, FileText, TrendingUp, TrendingDown, Plus, Minus } from 'lucide-react'
import Link from 'next/link'

export default function ComparePage() {
  const { 
    priceBooks, 
    comparisonResult,
    loading, 
    error, 
    fetchPriceBooks,
    comparePriceBooks
  } = usePriceBookStore()

  const [oldBookId, setOldBookId] = useState('')
  const [newBookId, setNewBookId] = useState('')
  const [comparing, setComparing] = useState(false)

  useEffect(() => {
    fetchPriceBooks()
  }, [fetchPriceBooks])

  const handleCompare = async () => {
    if (!oldBookId || !newBookId) {
      alert('Please select both price books to compare')
      return
    }

    if (oldBookId === newBookId) {
      alert('Cannot compare a price book with itself')
      return
    }

    setComparing(true)
    try {
      await comparePriceBooks(parseInt(oldBookId), parseInt(newBookId))
    } finally {
      setComparing(false)
    }
  }

  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case 'new_product':
        return <Plus className="h-4 w-4 text-green-500" />
      case 'retired_product':
        return <Minus className="h-4 w-4 text-red-500" />
      case 'price_change':
        return <TrendingUp className="h-4 w-4 text-blue-500" />
      default:
        return <FileText className="h-4 w-4 text-gray-500" />
    }
  }

  const getChangeBadge = (changeType: string) => {
    const variants = {
      'new_product': 'default',
      'retired_product': 'destructive',
      'price_change': 'secondary',
      'description_change': 'outline',
      'status_change': 'outline',
      'fuzzy_match': 'secondary'
    } as const

    return (
      <Badge variant={variants[changeType as keyof typeof variants] || 'outline'}>
        {changeType.replace('_', ' ').toUpperCase()}
      </Badge>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Compare Price Books</h1>
            <p className="text-muted-foreground">
              Compare different editions and track changes
            </p>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-destructive rounded-full"></div>
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparison Form */}
      <Card>
        <CardHeader>
          <CardTitle>Select Price Books to Compare</CardTitle>
          <CardDescription>
            Choose the old and new price book editions to compare
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Old Price Book (Baseline)</label>
              <select
                value={oldBookId}
                onChange={(e) => setOldBookId(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="">Select old price book...</option>
                {priceBooks.map((book) => (
                  <option key={book.id} value={book.id}>
                    {book.manufacturer} - {book.edition || 'Unknown Edition'}
                    {book.effective_date && ` (${book.effective_date})`}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">New Price Book (Updated)</label>
              <select
                value={newBookId}
                onChange={(e) => setNewBookId(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="">Select new price book...</option>
                {priceBooks.map((book) => (
                  <option key={book.id} value={book.id}>
                    {book.manufacturer} - {book.edition || 'Unknown Edition'}
                    {book.effective_date && ` (${book.effective_date})`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end mt-4">
            <Button 
              onClick={handleCompare}
              disabled={!oldBookId || !newBookId || comparing}
            >
              {comparing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Comparing...
                </>
              ) : (
                <>
                  <Compare className="mr-2 h-4 w-4" />
                  Compare Price Books
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Comparison Results */}
      {comparisonResult && (
        <div className="space-y-6">
          {/* Summary Statistics */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Changes</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {comparisonResult.summary.total_changes}
                </div>
                <p className="text-xs text-muted-foreground">
                  Across all categories
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">New Products</CardTitle>
                <Plus className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {comparisonResult.summary.new_products}
                </div>
                <p className="text-xs text-muted-foreground">
                  Products added
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Retired Products</CardTitle>
                <Minus className="h-4 w-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {comparisonResult.summary.retired_products}
                </div>
                <p className="text-xs text-muted-foreground">
                  Products removed
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Price Changes</CardTitle>
                <TrendingUp className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {comparisonResult.summary.price_changes}
                </div>
                <p className="text-xs text-muted-foreground">
                  Price updates
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Changes Table */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Changes</CardTitle>
              <CardDescription>
                Complete list of changes between {comparisonResult.old_edition} and {comparisonResult.new_edition}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {comparisonResult.changes.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No changes found</h3>
                  <p className="text-muted-foreground">
                    The price books are identical
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Product ID</TableHead>
                      <TableHead>Old Value</TableHead>
                      <TableHead>New Value</TableHead>
                      <TableHead>Change %</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {comparisonResult.changes.map((change) => (
                      <TableRow key={change.id}>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            {getChangeIcon(change.change_type)}
                            {getChangeBadge(change.change_type)}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {change.product_id || 'N/A'}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {change.old_value || 'N/A'}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {change.new_value || 'N/A'}
                        </TableCell>
                        <TableCell>
                          {change.change_percentage ? (
                            <Badge variant={change.change_percentage > 0 ? "default" : "secondary"}>
                              {change.change_percentage > 0 ? '+' : ''}{change.change_percentage.toFixed(1)}%
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">N/A</span>
                          )}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {change.description}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* No Results State */}
      {!comparisonResult && !loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <Compare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Ready to Compare</h3>
              <p className="text-muted-foreground">
                Select two price books above to see their differences
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
