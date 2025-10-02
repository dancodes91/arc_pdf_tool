'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { usePriceBookStore } from '@/lib/stores/priceBookStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { FileText, Download, ArrowLeft, Eye, Filter, AlertTriangle } from 'lucide-react'
import Link from 'next/link'

export default function PreviewPage() {
  const params = useParams()
  const priceBookId = parseInt(params.id as string)
  
  const { 
    currentPriceBook,
    products, 
    loading, 
    error, 
    fetchProducts,
    setCurrentPriceBook,
    exportPriceBook
  } = usePriceBookStore()

  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [priceFilter, setPriceFilter] = useState('')
  const [summary, setSummary] = useState<any>(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (priceBookId) {
      fetchProducts(priceBookId)
      // Fetch price book summary with confidence data
      const loadSummary = async () => {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'
          const res = await fetch(`${apiUrl}/api/price-books/${priceBookId}`)
          const data = await res.json()
          setSummary(data)
          setCurrentPriceBook({
            id: priceBookId,
            manufacturer: data.manufacturer || 'Unknown',
            edition: data.edition || '2025',
            effective_date: data.effective_date || '2025-01-01',
            upload_date: data.upload_date || new Date().toISOString(),
            status: data.status || 'completed',
            product_count: data.product_count || 0,
            option_count: data.option_count || 0,
            file_path: data.file_path || ''
          })
        } catch (error) {
          console.error('Error loading summary:', error)
        }
      }
      loadSummary()
    }
  }, [priceBookId, fetchProducts, setCurrentPriceBook])

  async function handleExport(format: 'csv' | 'xlsx' | 'json') {
    setExporting(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'
      const response = await fetch(`${apiUrl}/api/export/${priceBookId}?format=${format === 'xlsx' ? 'excel' : format}`)

      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `price_book_${priceBookId}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.model.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.description.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesStatus = !statusFilter ||
                         (statusFilter === 'active' && product.is_active) ||
                         (statusFilter === 'inactive' && !product.is_active)

    const matchesPrice = !priceFilter || !product.base_price || (() => {
      const price = product.base_price
      switch (priceFilter) {
        case '0-50': return price >= 0 && price <= 50
        case '50-100': return price > 50 && price <= 100
        case '100-200': return price > 100 && price <= 200
        case '200+': return price > 200
        default: return true
      }
    })()

    return matchesSearch && matchesStatus && matchesPrice
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading products...</p>
        </div>
      </div>
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
            <h1 className="text-3xl font-bold tracking-tight">
              {currentPriceBook?.manufacturer} Price Book
            </h1>
            <p className="text-muted-foreground">
              Edition: {currentPriceBook?.edition} | 
              Effective: {currentPriceBook?.effective_date} | 
              Uploaded: {currentPriceBook?.upload_date ? new Date(currentPriceBook.upload_date).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => handleExport('xlsx')} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            Excel
          </Button>
          <Button variant="outline" onClick={() => handleExport('csv')} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport('json')} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            JSON
          </Button>
        </div>
      </div>

      {/* Confidence Meter */}
      {summary?.parsing_metadata && (
        <Card className={summary.parsing_metadata.overall_confidence < 0.7 ? 'border-yellow-500' : ''}>
          <CardHeader>
            <CardTitle className="flex items-center text-base">
              {summary.parsing_metadata.overall_confidence < 0.7 && (
                <AlertTriangle className="mr-2 h-4 w-4 text-yellow-500" />
              )}
              Parsing Confidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Overall Quality</span>
                <span className="text-sm font-bold">
                  {Math.round((summary.parsing_metadata.overall_confidence || 0) * 100)}%
                </span>
              </div>
              <Progress value={Math.round((summary.parsing_metadata.overall_confidence || 0) * 100)} />
              {summary.parsing_metadata.overall_confidence < 0.7 && (
                <p className="text-sm text-yellow-600 mt-2">
                  ⚠️ Low confidence detected. Manual review recommended for accuracy.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Products</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{products.length}</div>
            <p className="text-xs text-muted-foreground">
              {filteredProducts.length} showing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Products</CardTitle>
            <div className="h-4 w-4 rounded-full bg-green-500"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {products.filter(p => p.is_active).length}
            </div>
            <p className="text-xs text-muted-foreground">
              Currently available
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Price</CardTitle>
            <div className="h-4 w-4 rounded-full bg-blue-500"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${products.filter(p => p.base_price).reduce((sum, p) => sum + (p.base_price || 0), 0) / products.filter(p => p.base_price).length || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Based on {products.filter(p => p.base_price).length} products
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Badge variant="secondary">
              {currentPriceBook?.status || 'Unknown'}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentPriceBook?.status === 'completed' ? 'Ready' : 'Processing'}
            </div>
            <p className="text-xs text-muted-foreground">
              {currentPriceBook?.status === 'completed' ? 'All data parsed' : 'Still processing'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="mr-2 h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search Products</label>
              <input
                type="text"
                placeholder="Search by SKU, model, or description..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Price Range</label>
              <select
                value={priceFilter}
                onChange={(e) => setPriceFilter(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="">All Prices</option>
                <option value="0-50">$0 - $50</option>
                <option value="50-100">$50 - $100</option>
                <option value="100-200">$100 - $200</option>
                <option value="200+">$200+</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Products Table */}
      <Card>
        <CardHeader>
          <CardTitle>Products</CardTitle>
          <CardDescription>
            {filteredProducts.length} of {products.length} products
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredProducts.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No products found</h3>
              <p className="text-muted-foreground">
                Try adjusting your search or filter criteria
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SKU</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Base Price</TableHead>
                  <TableHead>Effective Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Family</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell className="font-mono text-sm">
                      {product.sku}
                    </TableCell>
                    <TableCell>{product.model || 'N/A'}</TableCell>
                    <TableCell className="max-w-xs truncate">
                      {product.description || 'N/A'}
                    </TableCell>
                    <TableCell>
                      {product.base_price ? (
                        <Badge variant="secondary">
                          ${product.base_price.toFixed(2)}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">N/A</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {product.effective_date || 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={product.is_active ? "default" : "secondary"}>
                        {product.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {product.family ? (
                        <Badge variant="outline">{product.family}</Badge>
                      ) : (
                        <span className="text-muted-foreground">N/A</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
