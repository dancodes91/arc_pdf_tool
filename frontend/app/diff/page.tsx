'use client'

import { useEffect, useState } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Alert } from '@/components/ui/alert'
import {
  GitCompare,
  Plus,
  Minus,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Download,
  ArrowRight,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'

type FilterChip = {
  id: string
  label: string
  icon: React.ReactNode
  variant: 'success' | 'error' | 'warning' | 'brand' | 'neutral'
  count: number
}

export default function DiffPage() {
  const {
    priceBooks,
    comparisonResult,
    loading,
    fetchPriceBooks,
    comparePriceBooks
  } = usePriceBookStore()

  const [oldBookId, setOldBookId] = useState<number | null>(null)
  const [newBookId, setNewBookId] = useState<number | null>(null)
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [selectedChanges, setSelectedChanges] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchPriceBooks()
  }, [fetchPriceBooks])

  const handleCompare = async () => {
    if (oldBookId && newBookId) {
      await comparePriceBooks(oldBookId, newBookId)
    }
  }

  const handleToggleChange = (changeId: number) => {
    const newSelected = new Set(selectedChanges)
    if (newSelected.has(changeId)) {
      newSelected.delete(changeId)
    } else {
      newSelected.add(changeId)
    }
    setSelectedChanges(newSelected)
  }

  const handleSelectAll = () => {
    if (comparisonResult?.changes) {
      const allIds = comparisonResult.changes.map((c) => c.id)
      setSelectedChanges(new Set(allIds))
    }
  }

  const handleDeselectAll = () => {
    setSelectedChanges(new Set())
  }

  const handleApprove = () => {
    console.log('Approve selected changes:', Array.from(selectedChanges))
    // TODO: Implement approval logic
  }

  const handleExportDiff = () => {
    console.log('Export diff to CSV')
    // TODO: Implement CSV export
  }

  // Calculate filter chip counts
  const filterChips: FilterChip[] = [
    {
      id: 'all',
      label: 'All Changes',
      icon: <GitCompare className="h-4 w-4" />,
      variant: 'neutral',
      count: comparisonResult?.summary.total_changes || 0,
    },
    {
      id: 'added',
      label: 'Added',
      icon: <Plus className="h-4 w-4" />,
      variant: 'success',
      count: comparisonResult?.summary.new_products || 0,
    },
    {
      id: 'removed',
      label: 'Removed',
      icon: <Minus className="h-4 w-4" />,
      variant: 'error',
      count: comparisonResult?.summary.retired_products || 0,
    },
    {
      id: 'changed',
      label: 'Changed',
      icon: <RefreshCw className="h-4 w-4" />,
      variant: 'warning',
      count: comparisonResult?.summary.price_changes || 0,
    },
    {
      id: 'renamed',
      label: 'Renamed',
      icon: <ArrowRight className="h-4 w-4" />,
      variant: 'brand',
      count: 0, // Placeholder - would need to track renames separately
    },
    {
      id: 'low-confidence',
      label: 'Low Confidence',
      icon: <AlertCircle className="h-4 w-4" />,
      variant: 'warning',
      count: 0, // Placeholder
    },
  ]

  // Filter changes based on active filter
  const filteredChanges = comparisonResult?.changes.filter((change) => {
    if (activeFilter === 'all') return true
    if (activeFilter === 'added') return change.change_type === 'new'
    if (activeFilter === 'removed') return change.change_type === 'retired'
    if (activeFilter === 'changed') return change.change_type === 'price_change'
    // Add more filter logic as needed
    return true
  }) || []

  return (
    <div className="container-max p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-display font-medium mb-2">Diff Review</h1>
        <p className="text-muted-foreground">
          Compare two price books and review differences
        </p>
      </div>

      {/* Comparison Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Select Price Books to Compare
          </CardTitle>
          <CardDescription>
            Choose an old and new price book to identify changes
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Old Price Book</label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={oldBookId || ''}
                onChange={(e) => setOldBookId(Number(e.target.value))}
              >
                <option value="">Select old version...</option>
                {priceBooks
                  .filter((b) => b.status === 'completed' || b.status === 'processed')
                  .map((book) => (
                    <option key={book.id} value={book.id}>
                      {book.manufacturer} - {book.edition || 'No edition'} ({book.effective_date || 'No date'})
                    </option>
                  ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">New Price Book</label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={newBookId || ''}
                onChange={(e) => setNewBookId(Number(e.target.value))}
              >
                <option value="">Select new version...</option>
                {priceBooks
                  .filter((b) => b.status === 'completed' || b.status === 'processed')
                  .filter((b) => b.id !== oldBookId)
                  .map((book) => (
                    <option key={book.id} value={book.id}>
                      {book.manufacturer} - {book.edition || 'No edition'} ({book.effective_date || 'No date'})
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex items-end">
              <Button
                onClick={handleCompare}
                disabled={!oldBookId || !newBookId || loading}
                className="w-full"
              >
                <GitCompare className="h-4 w-4" />
                Compare
              </Button>
            </div>
          </div>

          {comparisonResult && (
            <Alert variant="success">
              <CheckCircle2 className="h-4 w-4" />
              <div className="ml-2">
                <strong>Comparison Complete</strong>
                <p className="text-sm mt-1">
                  {comparisonResult.old_edition} vs {comparisonResult.new_edition}: Found{' '}
                  {comparisonResult.summary.total_changes} changes
                </p>
              </div>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {comparisonResult && (
        <>
          {/* Filter Chips */}
          <div className="flex flex-wrap gap-2">
            {filterChips.map((chip) => (
              <button
                key={chip.id}
                onClick={() => setActiveFilter(chip.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  activeFilter === chip.id
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-card hover:bg-muted border-border'
                }`}
              >
                {chip.icon}
                <span className="font-medium">{chip.label}</span>
                <Badge variant={chip.variant} className="ml-1">
                  {chip.count}
                </Badge>
              </button>
            ))}
          </div>

          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Changes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {comparisonResult.summary.total_changes}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Plus className="h-4 w-4 text-success" />
                  New Products
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-success">
                  {comparisonResult.summary.new_products}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Minus className="h-4 w-4 text-error" />
                  Retired Products
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-error">
                  {comparisonResult.summary.retired_products}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-warning" />
                  Price Changes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold text-warning">
                  {comparisonResult.summary.price_changes}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Changes List */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Changes</CardTitle>
                  <CardDescription>
                    {filteredChanges.length} changes • {selectedChanges.size} selected
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleSelectAll}>
                    Select All
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDeselectAll}>
                    Deselect All
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleExportDiff}>
                    <Download className="h-4 w-4" />
                    Export
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {filteredChanges.length > 0 ? (
                <div className="space-y-2">
                  {filteredChanges.map((change) => {
                    const isSelected = selectedChanges.has(change.id)
                    const changeType = change.change_type
                    const isNew = changeType === 'new'
                    const isRetired = changeType === 'retired'
                    const isPriceChange = changeType === 'price_change'

                    return (
                      <div
                        key={change.id}
                        className={`flex items-center gap-4 p-4 rounded-lg border transition-colors ${
                          isSelected
                            ? 'bg-brand-light border-primary'
                            : 'bg-card hover:bg-muted border-border'
                        }`}
                      >
                        {/* Checkbox */}
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleChange(change.id)}
                          className="h-4 w-4"
                        />

                        {/* Change Type Badge */}
                        <Badge
                          variant={
                            isNew ? 'success' : isRetired ? 'error' : isPriceChange ? 'warning' : 'neutral'
                          }
                        >
                          {isNew ? (
                            <>
                              <Plus className="h-3 w-3 mr-1" />
                              Added
                            </>
                          ) : isRetired ? (
                            <>
                              <Minus className="h-3 w-3 mr-1" />
                              Removed
                            </>
                          ) : isPriceChange ? (
                            <>
                              <RefreshCw className="h-3 w-3 mr-1" />
                              Changed
                            </>
                          ) : (
                            'Other'
                          )}
                        </Badge>

                        {/* Product ID */}
                        <span className="font-mono text-sm text-muted-foreground min-w-[100px]">
                          {change.product_id}
                        </span>

                        {/* Before/After */}
                        <div className="flex-1 grid grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">Before</div>
                            <div className={`text-sm font-medium ${isRetired ? 'line-through text-error' : ''}`}>
                              {change.old_value || '—'}
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">After</div>
                            <div className={`text-sm font-medium ${isNew ? 'text-success' : ''}`}>
                              {change.new_value || '—'}
                            </div>
                          </div>
                        </div>

                        {/* Delta Badge */}
                        {change.change_percentage !== null && (
                          <Badge variant={change.change_percentage > 0 ? 'warning' : 'success'}>
                            {change.change_percentage > 0 ? (
                              <TrendingUp className="h-3 w-3 mr-1" />
                            ) : (
                              <TrendingDown className="h-3 w-3 mr-1" />
                            )}
                            {Math.abs(change.change_percentage).toFixed(1)}%
                          </Badge>
                        )}

                        {/* Description */}
                        <div className="text-sm text-muted-foreground max-w-xs truncate">
                          {change.description}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <GitCompare className="h-16 w-16 mb-4" />
                  <p>No changes found for this filter</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Approval Footer */}
          {selectedChanges.size > 0 && (
            <Card className="sticky bottom-6 shadow-xl border-primary">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                    <div>
                      <div className="font-semibold">
                        {selectedChanges.size} change{selectedChanges.size !== 1 ? 's' : ''} selected
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Ready to approve and apply to production
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={handleDeselectAll}>
                      Cancel
                    </Button>
                    <Button onClick={handleApprove}>
                      <CheckCircle2 className="h-4 w-4" />
                      Approve & Apply
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Empty State */}
      {!comparisonResult && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <GitCompare className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Comparison Yet</h3>
            <p className="text-muted-foreground text-center max-w-sm">
              Select two price books above and click Compare to identify changes
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
