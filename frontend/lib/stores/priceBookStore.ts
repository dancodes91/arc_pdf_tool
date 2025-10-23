import { create } from 'zustand'
import axios from 'axios'

const DEFAULT_API_URL = 'http://localhost:5000/api'
const envApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '')
const API_BASE_URL = envApiUrl
  ? (envApiUrl.endsWith('/api') ? envApiUrl : `${envApiUrl}/api`)
  : DEFAULT_API_URL

interface PriceBook {
  id: number
  manufacturer: string
  edition: string
  effective_date: string
  upload_date: string
  status: 'processing' | 'processed' | 'completed' | 'failed'
  product_count: number
  option_count: number
  file_path: string
}

interface Product {
  id: number
  sku: string
  model: string
  description: string
  base_price: number | null
  effective_date: string | null
  is_active: boolean
  family: string | null
}

interface ComparisonChange {
  id: number
  change_type: string
  product_id: string
  old_value: string
  new_value: string
  change_percentage: number | null
  description: string
}

interface ComparisonResult {
  old_edition: string
  new_edition: string
  summary: {
    total_changes: number
    new_products: number
    retired_products: number
    price_changes: number
  }
  changes: ComparisonChange[]
}

interface PublishResult {
  id: string
  price_book_id: number
  status: string
  dry_run: boolean
  rows_created: number
  rows_updated: number
  rows_processed: number
  duration_seconds: number
  started_at: string
  completed_at: string | null
  warnings: any[]
  manufacturer?: string
  edition?: string
}

interface PriceBookState {
  priceBooks: PriceBook[]
  currentPriceBook: PriceBook | null
  products: Product[]
  comparisonResult: ComparisonResult | null
  publishHistory: PublishResult[]
  loading: boolean
  error: string | null

  // Actions
  fetchPriceBooks: () => Promise<void>
  fetchProducts: (priceBookId: number) => Promise<void>
  setCurrentPriceBook: (book: PriceBook) => void
  uploadPriceBook: (file: File, manufacturer: string) => Promise<number>
  exportPriceBook: (priceBookId: number, format: 'excel' | 'csv' | 'json') => Promise<void>
  deletePriceBook: (priceBookId: number) => Promise<void>
  comparePriceBooks: (oldId: number, newId: number) => Promise<void>
  publishToBaserow: (priceBookId: number, dryRun: boolean) => Promise<PublishResult>
  fetchPublishHistory: () => Promise<void>
  setError: (error: string | null) => void
  clearError: () => void
}

export const usePriceBookStore = create<PriceBookState>((set, get) => ({
  priceBooks: [],
  currentPriceBook: null,
  products: [],
  comparisonResult: null,
  publishHistory: [],
  loading: false,
  error: null,

  fetchPriceBooks: async () => {
    set({ loading: true, error: null })
    try {
      const response = await axios.get(`${API_BASE_URL}/price-books`)
      set({ priceBooks: response.data, loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to fetch price books'
      set({ error: errorMessage, loading: false })
      console.error('Error fetching price books:', error)
    }
  },

  fetchProducts: async (priceBookId: number) => {
    set({ loading: true, error: null })
    try {
      // Fetch price book details
      const bookResponse = await axios.get(`${API_BASE_URL}/price-books/${priceBookId}`)
      set({ currentPriceBook: bookResponse.data })

      // Fetch products with pagination support
      const productsResponse = await axios.get(`${API_BASE_URL}/products/${priceBookId}`, {
        params: {
          page: 1,
          per_page: 1000 // Fetch all products for now
        }
      })
      set({ products: productsResponse.data.products, loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to fetch products'
      set({ error: errorMessage, loading: false })
      console.error('Error fetching products:', error)
    }
  },

  setCurrentPriceBook: (book: PriceBook) => {
    set({ currentPriceBook: book })
  },

  uploadPriceBook: async (file: File, manufacturer: string) => {
    set({ loading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('manufacturer', manufacturer)

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Refresh price books list
      await get().fetchPriceBooks()

      set({ loading: false })
      return response.data.price_book_id
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to upload price book'
      set({ error: errorMessage, loading: false })
      console.error('Error uploading price book:', error)
      throw new Error(errorMessage)
    }
  },

  exportPriceBook: async (priceBookId: number, format: 'excel' | 'csv' | 'json') => {
    set({ loading: true, error: null })
    try {
      const response = await axios.get(`${API_BASE_URL}/export/${priceBookId}`, {
        params: { format },
        responseType: 'blob',
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url

      // Extract filename from content-disposition header or use default
      const contentDisposition = response.headers['content-disposition']
      const ext = format === 'excel' ? 'xlsx' : format
      let filename = `price_book_${priceBookId}.${ext}`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }

      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      set({ loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to export price book'
      set({ error: errorMessage, loading: false })
      console.error('Error exporting price book:', error)
    }
  },

  deletePriceBook: async (priceBookId: number) => {
    set({ loading: true, error: null })
    try {
      await axios.delete(`${API_BASE_URL}/price-books/${priceBookId}`)

      // Refresh price books list after deletion
      await get().fetchPriceBooks()

      set({ loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to delete price book'
      set({ error: errorMessage, loading: false })
      console.error('Error deleting price book:', error)
      throw new Error(errorMessage)
    }
  },

  comparePriceBooks: async (oldId: number, newId: number) => {
    set({ loading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/compare`, {
        old_price_book_id: oldId,
        new_price_book_id: newId,
      })

      set({ comparisonResult: response.data, loading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to compare price books'
      set({ error: errorMessage, loading: false })
      console.error('Error comparing price books:', error)
    }
  },

  publishToBaserow: async (priceBookId: number, dryRun: boolean) => {
    set({ loading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/publish`, {
        price_book_id: priceBookId,
        dry_run: dryRun,
      })

      // Refresh publish history
      await get().fetchPublishHistory()

      set({ loading: false })
      return response.data
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to publish to Baserow'
      set({ error: errorMessage, loading: false })
      console.error('Error publishing to Baserow:', error)
      throw new Error(errorMessage)
    }
  },

  fetchPublishHistory: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/publish/history`, {
        params: {
          limit: 20
        }
      })

      set({ publishHistory: response.data })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to fetch publish history'
      console.error('Error fetching publish history:', error)
      // Don't set loading/error state for background fetch
    }
  },

  setError: (error: string | null) => {
    set({ error })
  },

  clearError: () => {
    set({ error: null })
  },
}))


