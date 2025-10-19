'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable, DataTableColumnHeader } from '@/components/ui/data-table'
import {
  ArrowLeft,
  FileText,
  Download,
  ExternalLink,
  Package,
  Settings,
  Layers,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'
import { ColumnDef } from '@tanstack/react-table'

type Product = {
  id: number
  sku: string
  model: string
  description: string
  base_price: number | null
  effective_date: string | null
  is_active: boolean
  family: string | null
}

export default function PriceBookDetailPage() {
  const params = useParams()
  const router = useRouter()
  const bookId = typeof params.id === 'string' ? parseInt(params.id) : null

  const { currentPriceBook, products, loading, fetchProducts, exportPriceBook } = usePriceBookStore()
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (bookId) {
      fetchProducts(bookId)
    }
  }, [bookId, fetchProducts])

  // Define columns for Items table
  const itemColumns: ColumnDef<Product>[] = [
    {
      accessorKey: 'sku',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="SKU" />
      ),
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.getValue('sku')}</span>
      ),
    },
    {
      accessorKey: 'model',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Model" />
      ),
      cell: ({ row }) => (
        <span className="font-medium">{row.getValue('model')}</span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground max-w-md truncate block">
          {row.getValue('description') || '—'}
        </span>
      ),
    },
    {
      accessorKey: 'family',
      header: 'Family',
      cell: ({ row }) => {
        const family = row.getValue('family') as string | null
        return family ? (
          <Badge variant="neutral">{family}</Badge>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        )
      },
    },
    {
      accessorKey: 'base_price',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Base Price" className="text-right" />
      ),
      cell: ({ row }) => {
        const price = row.getValue('base_price') as number | null
        return (
          <div className="text-right font-mono">
            {price !== null ? `$${price.toFixed(2)}` : '—'}
          </div>
        )
      },
    },
    {
      accessorKey: 'is_active',
      header: 'Status',
      cell: ({ row }) => {
        const isActive = row.getValue('is_active')
        return isActive ? (
          <Badge variant="success">Active</Badge>
        ) : (
          <Badge variant="neutral">Inactive</Badge>
        )
      },
    },
  ]

  if (loading && !currentPriceBook) {
    return (
      <div className="container-max p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading price book...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!currentPriceBook) {
    return (
      <div className="container-max p-6">
        <div className="text-center py-16">
          <AlertCircle className="h-16 w-16 text-error mx-auto mb-4" />
          <h2 className="text-h2 font-semibold mb-2">Price Book Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The price book you're looking for doesn't exist or has been deleted.
          </p>
          <Link href="/books">
            <Button>
              <ArrowLeft className="h-4 w-4" />
              Back to Price Books
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const lowConfidenceCount = 0 // Placeholder - would come from API
  const optionsCount = currentPriceBook.option_count || 0
  const finishesCount = 0 // Placeholder - would come from API
  const rulesCount = 0 // Placeholder - would come from API

  return (
    <div className="container-max p-6 space-y-6">
      {/* Back Navigation */}
      <div>
        <Link href="/books">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
            Back to Price Books
          </Button>
        </Link>
      </div>

      {/* Hero Band */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              {/* Manufacturer Logo/Icon */}
              <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center">
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>

              <div className="space-y-2">
                {/* Manufacturer & Edition */}
                <div className="flex items-center gap-3">
                  <h1 className="text-display font-semibold">{currentPriceBook.manufacturer}</h1>
                  {currentPriceBook.edition && (
                    <Badge variant="brand" className="text-sm">
                      {currentPriceBook.edition}
                    </Badge>
                  )}
                </div>

                {/* Metadata */}
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  {currentPriceBook.effective_date && (
                    <div className="flex items-center gap-2">
                      <span>Effective Date:</span>
                      <Badge variant="neutral">{currentPriceBook.effective_date}</Badge>
                    </div>
                  )}
                  <span>•</span>
                  <span>Uploaded {new Date(currentPriceBook.upload_date).toLocaleDateString()}</span>
                  {currentPriceBook.file_path && (
                    <>
                      <span>•</span>
                      <a
                        href={`/api/files/${currentPriceBook.file_path}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline"
                      >
                        Source PDF
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </>
                  )}
                </div>

                {/* Status */}
                <div>
                  {currentPriceBook.status === 'completed' || currentPriceBook.status === 'processed' ? (
                    <Badge variant="success">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Completed
                    </Badge>
                  ) : currentPriceBook.status === 'processing' ? (
                    <Badge variant="warning">Processing</Badge>
                  ) : (
                    <Badge variant="error">Failed</Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => exportPriceBook(currentPriceBook.id, 'excel')}
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Package className="h-4 w-4" />
              Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{currentPriceBook.product_count.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Options
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{optionsCount.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Finishes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{finishesCount.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Rules
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{rulesCount.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Low Confidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-warning">{lowConfidenceCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="items">Items ({currentPriceBook.product_count})</TabsTrigger>
          <TabsTrigger value="options">Options ({optionsCount})</TabsTrigger>
          <TabsTrigger value="finishes">Finishes ({finishesCount})</TabsTrigger>
          <TabsTrigger value="rules">Rules ({rulesCount})</TabsTrigger>
          <TabsTrigger value="provenance">Provenance</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Price Book Summary</CardTitle>
              <CardDescription>
                Overview of {currentPriceBook.manufacturer} {currentPriceBook.edition || ''} price book
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Details</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-sm">Manufacturer:</dt>
                      <dd className="text-sm font-medium">{currentPriceBook.manufacturer}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Edition:</dt>
                      <dd className="text-sm font-medium">{currentPriceBook.edition || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Effective Date:</dt>
                      <dd className="text-sm font-medium">{currentPriceBook.effective_date || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Upload Date:</dt>
                      <dd className="text-sm font-medium">
                        {new Date(currentPriceBook.upload_date).toLocaleDateString()}
                      </dd>
                    </div>
                  </dl>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Statistics</h3>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-sm">Total Items:</dt>
                      <dd className="text-sm font-medium">{currentPriceBook.product_count.toLocaleString()}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Options:</dt>
                      <dd className="text-sm font-medium">{optionsCount.toLocaleString()}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Finishes:</dt>
                      <dd className="text-sm font-medium">{finishesCount.toLocaleString()}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm">Rules:</dt>
                      <dd className="text-sm font-medium">{rulesCount.toLocaleString()}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Items Tab */}
        <TabsContent value="items" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Items</CardTitle>
              <CardDescription>
                All products in this price book ({currentPriceBook.product_count} items)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {products.length > 0 ? (
                <DataTable
                  columns={itemColumns}
                  data={products}
                  searchKey="model"
                  searchPlaceholder="Search by model..."
                  onExport={() => {
                    console.log('Export items to CSV')
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <Package className="h-16 w-16 mb-4" />
                  <p>No items found</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Options Tab */}
        <TabsContent value="options" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Options</CardTitle>
              <CardDescription>
                Configurable options for products ({optionsCount} options)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <Settings className="h-16 w-16 mb-4" />
                <p className="text-lg font-medium mb-2">Options Coming Soon</p>
                <p className="text-sm">This section will display product options and configurations</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Finishes Tab */}
        <TabsContent value="finishes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Finishes</CardTitle>
              <CardDescription>
                Available finishes and materials ({finishesCount} finishes)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <Layers className="h-16 w-16 mb-4" />
                <p className="text-lg font-medium mb-2">Finishes Coming Soon</p>
                <p className="text-sm">This section will display available finishes and materials</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rules Tab */}
        <TabsContent value="rules" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Rules</CardTitle>
              <CardDescription>
                Pricing rules and business logic ({rulesCount} rules)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <CheckCircle2 className="h-16 w-16 mb-4" />
                <p className="text-lg font-medium mb-2">Rules Coming Soon</p>
                <p className="text-sm">This section will display pricing rules and business logic</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Provenance Tab */}
        <TabsContent value="provenance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Provenance</CardTitle>
              <CardDescription>
                Source data and parsing history for this price book
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <FileText className="h-16 w-16 mb-4" />
                <p className="text-lg font-medium mb-2">Provenance Coming Soon</p>
                <p className="text-sm">This section will display source PDF and parsing logs</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
