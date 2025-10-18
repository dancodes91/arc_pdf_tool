'use client'

import { useEffect } from 'react'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { DataTable, DataTableColumnHeader } from '@/components/ui/data-table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Eye, Download, Trash2, FileText, Upload } from 'lucide-react'
import Link from 'next/link'
import { ColumnDef } from '@tanstack/react-table'

type PriceBook = {
  id: string
  manufacturer: string
  edition: string | null
  effective_date: string | null
  product_count: number
  status: string
  upload_date: string
}

export default function BooksPage() {
  const { priceBooks, loading, fetchPriceBooks, deletePriceBook, exportPriceBook } = usePriceBookStore()

  useEffect(() => {
    fetchPriceBooks()
  }, [fetchPriceBooks])

  const columns: ColumnDef<PriceBook>[] = [
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
        <Link href="/upload">
          <Button>
            <Upload className="h-4 w-4" />
            Upload New
          </Button>
        </Link>
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
              onExport={() => {
                // Implement CSV export of table
                console.log('Export all price books')
              }}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
