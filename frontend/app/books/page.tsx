'use client'

import { useEffect, useState, useRef } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { DataTable, DataTableColumnHeader } from '@/components/ui/data-table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye, Download, Trash2, FileText, Upload, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { ColumnDef } from '@tanstack/react-table'

type PriceBook = {
  id: number
  manufacturer: string
  edition: string | null
  effective_date: string | null
  product_count: number
  status: string
  upload_date: string
}

export default function BooksPage() {
  const { priceBooks, loading, fetchPriceBooks, deletePriceBook, exportPriceBook } = usePriceBookStore()
  const [selectedRows, setSelectedRows] = useState<PriceBook[]>([])
  const [isDeleting, setIsDeleting] = useState(false)
  const lastFetchRef = useRef<number>(0)
  const FETCH_COOLDOWN = 1000 // 1 second cooldown between fetches

  const debouncedFetch = () => {
    const now = Date.now()
    if (now - lastFetchRef.current > FETCH_COOLDOWN) {
      lastFetchRef.current = now
      fetchPriceBooks()
    }
  }

  // Fetch price books on mount and when window regains focus
  useEffect(() => {
    fetchPriceBooks()
    lastFetchRef.current = Date.now()

    // Refresh when user navigates back to this page
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        debouncedFetch()
      }
    }

    const handleFocus = () => {
      debouncedFetch()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleFocus)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('focus', handleFocus)
    }
  }, [fetchPriceBooks])

  const handleBulkDelete = async () => {
    if (selectedRows.length === 0) return
    
    const count = selectedRows.length
    const confirmMessage = `Are you sure you want to delete ${count} price book${count > 1 ? 's' : ''}?`
    
    if (!confirm(confirmMessage)) return
    
    // Update lastFetchRef BEFORE any operations to prevent event listeners from triggering
    lastFetchRef.current = Date.now()
    
    // Save selected rows before clearing
    const rowsToDelete = [...selectedRows]
    setIsDeleting(true)
    setSelectedRows([]) // Clear selection immediately to prevent UI flicker
    try {
      // Delete all selected items (skip refresh for each individual deletion)
      await Promise.all(rowsToDelete.map(book => deletePriceBook(book.id, true)))
      
      // Refresh the list only once after all deletions are complete
      await fetchPriceBooks()
    } catch (error) {
      console.error('Error deleting price books:', error)
      alert('Some price books could not be deleted. Please try again.')
      // Refresh even on error to ensure UI is in sync
      await fetchPriceBooks()
    } finally {
      setIsDeleting(false)
    }
  }

  const columns: ColumnDef<PriceBook>[] = [
    {
      id: 'select',
      header: ({ table }) => (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            onChange={(e) => {
              table.toggleAllPageRowsSelected(e.target.checked)
            }}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer"
            aria-label="Select all"
          />
        </div>
      ),
      cell: ({ row }) => (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={(e) => {
              row.toggleSelected(e.target.checked)
            }}
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer"
            aria-label="Select row"
          />
        </div>
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'manufacturer',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Manufacturer" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue('manufacturer')}</span>
        </div>
      ),
    },
    {
      accessorKey: 'edition',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Edition" />
      ),
      cell: ({ row }) => {
        const edition = row.getValue('edition') as string | null
        return edition ? (
          <Badge variant="neutral">{edition}</Badge>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        )
      },
    },
    {
      accessorKey: 'effective_date',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Effective Date" />
      ),
      cell: ({ row }) => {
        const date = row.getValue('effective_date') as string | null
        return date ? (
          <Badge variant="brand">{date}</Badge>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        )
      },
    },
    {
      accessorKey: 'product_count',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Products" className="text-right" />
      ),
      cell: ({ row }) => {
        const count = row.getValue('product_count') as number
        return (
          <div className="text-right font-mono">
            {count.toLocaleString()}
          </div>
        )
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.getValue('status') as string
        return status === 'completed' || status === 'processed' ? (
          <Badge variant="success">Completed</Badge>
        ) : status === 'processing' ? (
          <Badge variant="warning">Processing</Badge>
        ) : (
          <Badge variant="error">Failed</Badge>
        )
      },
    },
    {
      accessorKey: 'upload_date',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Upload Date" />
      ),
      cell: ({ row }) => {
        const date = new Date(row.getValue('upload_date'))
        return (
          <span className="text-sm text-muted-foreground">
            {date.toLocaleDateString()}
          </span>
        )
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const book = row.original

        return (
          <div className="flex items-center gap-1">
            <Link href={`/books/${book.id}`}>
              <Button variant="ghost" size="icon-sm" title="View details">
                <Eye className="h-4 w-4" />
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => exportPriceBook(book.id, 'excel')}
              title="Export to Excel"
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={async () => {
                if (confirm(`Delete ${book.manufacturer} ${book.edition || ''}?`)) {
                  lastFetchRef.current = Date.now()
                  await deletePriceBook(book.id)
                }
              }}
              title="Delete"
              className="hover:text-error"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        )
      },
    },
  ]

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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display font-medium mb-2">Price Books</h1>
          <p className="text-muted-foreground">
            Browse and manage your parsed price books
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchPriceBooks()}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Link href="/upload">
            <Button>
              <Upload className="h-4 w-4" />
              Upload New
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Books
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{priceBooks.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {priceBooks.filter(b => b.status === 'completed' || b.status === 'processed').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {priceBooks.filter(b => b.status === 'processing').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Products
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              {priceBooks.reduce((sum, b) => sum + b.product_count, 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Table */}
      {priceBooks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No price books yet</h3>
            <p className="text-muted-foreground mb-6 text-center max-w-sm">
              Upload your first PDF price book to get started
            </p>
            <Link href="/upload">
              <Button>
                <Upload className="h-4 w-4" />
                Upload Price Book
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>All Price Books</CardTitle>
            <CardDescription>
              {priceBooks.length} price book{priceBooks.length !== 1 ? 's' : ''} in your library
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={columns}
              data={priceBooks}
              searchKey="manufacturer"
              searchPlaceholder="Search by manufacturer..."
              enableRowSelection={true}
              onSelectionChange={setSelectedRows}
              onBulkDelete={handleBulkDelete}
              selectedCount={selectedRows.length}
              isDeleting={isDeleting}
              onExport={() => {
                // Export table data as CSV
                const headers = ['Manufacturer', 'Edition', 'Effective Date', 'Products', 'Status', 'Upload Date']
                const rows = priceBooks.map(book => [
                  book.manufacturer || '',
                  book.edition || '',
                  book.effective_date || '',
                  book.product_count?.toString() || '0',
                  book.status || '',
                  book.upload_date ? new Date(book.upload_date).toLocaleDateString() : ''
                ])
                
                // Create CSV content
                const csvContent = [
                  headers.join(','),
                  ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
                ].join('\n')
                
                // Create and trigger download
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
                const link = document.createElement('a')
                const url = URL.createObjectURL(blob)
                link.setAttribute('href', url)
                link.setAttribute('download', `price_books_${new Date().toISOString().split('T')[0]}.csv`)
                link.style.visibility = 'hidden'
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
              }}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}