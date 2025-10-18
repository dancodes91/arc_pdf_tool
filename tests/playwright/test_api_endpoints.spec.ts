import { test, expect } from '@playwright/test';

const API_BASE_URL = 'http://localhost:5000/api';

test.describe('API Endpoints Tests', () => {
  let uploadedBookId: number;

  test.describe('Health Checks', () => {
    test('GET /api/health should return healthy status', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/health`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.status).toBe('healthy');
      expect(data.version).toBe('1.0.0');
      expect(data.timestamp).toBeTruthy();
    });
  });

  test.describe('Price Books Management', () => {
    test('GET /api/price-books should return list of price books', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/price-books`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();

      if (data.length > 0) {
        const book = data[0];
        expect(book).toHaveProperty('id');
        expect(book).toHaveProperty('manufacturer');
        expect(book).toHaveProperty('status');
        expect(book).toHaveProperty('product_count');
        uploadedBookId = book.id;
      }
    });

    test('GET /api/price-books/:id should return specific price book', async ({ request }) => {
      // First get all books to get an ID
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length === 0) {
        test.skip();
        return;
      }

      const bookId = books[0].id;
      const response = await request.get(`${API_BASE_URL}/price-books/${bookId}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.id).toBe(bookId);
      expect(data).toHaveProperty('manufacturer');
      expect(data).toHaveProperty('edition');
      expect(data).toHaveProperty('product_count');
    });

    test('GET /api/price-books/:id with invalid ID should return 404', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/price-books/99999`);
      expect(response.status()).toBe(404);
    });
  });

  test.describe('Products', () => {
    test('GET /api/products/:id should return paginated products', async ({ request }) => {
      // Get a book ID first
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length === 0) {
        test.skip();
        return;
      }

      const bookId = books[0].id;
      const response = await request.get(`${API_BASE_URL}/products/${bookId}?page=1&per_page=10`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('products');
      expect(data).toHaveProperty('page');
      expect(data).toHaveProperty('per_page');
      expect(Array.isArray(data.products)).toBeTruthy();

      if (data.products.length > 0) {
        const product = data.products[0];
        expect(product).toHaveProperty('id');
        expect(product).toHaveProperty('sku');
        expect(product).toHaveProperty('model');
      }
    });
  });

  test.describe('Comparison', () => {
    test('POST /api/compare should compare two price books', async ({ request }) => {
      // Get at least 2 books
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length < 2) {
        console.log('Skipping compare test - need at least 2 books');
        test.skip();
        return;
      }

      const response = await request.post(`${API_BASE_URL}/compare`, {
        data: {
          old_price_book_id: books[0].id,
          new_price_book_id: books[1].id
        }
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('old_price_book_id');
      expect(data).toHaveProperty('new_price_book_id');
      expect(data).toHaveProperty('changes');
      expect(data).toHaveProperty('summary');
      expect(data.summary).toHaveProperty('total_changes');
      expect(data.summary).toHaveProperty('new_products');
      expect(data.summary).toHaveProperty('retired_products');
      expect(data.summary).toHaveProperty('price_changes');
    });

    test('POST /api/compare with missing IDs should return 400', async ({ request }) => {
      const response = await request.post(`${API_BASE_URL}/compare`, {
        data: {
          old_price_book_id: 1
          // Missing new_price_book_id
        }
      });

      expect(response.status()).toBe(400);
    });

    test('POST /api/compare with same ID should return 400', async ({ request }) => {
      const response = await request.post(`${API_BASE_URL}/compare`, {
        data: {
          old_price_book_id: 1,
          new_price_book_id: 1
        }
      });

      expect(response.status()).toBe(400);
    });
  });

  test.describe('Export', () => {
    test('GET /api/export/:id?format=csv should export as CSV', async ({ request }) => {
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length === 0) {
        test.skip();
        return;
      }

      const bookId = books[0].id;
      const response = await request.get(`${API_BASE_URL}/export/${bookId}?format=csv`);
      expect(response.ok()).toBeTruthy();
      expect(response.headers()['content-type']).toContain('text/csv');
    });

    test('GET /api/export/:id?format=excel should export as Excel', async ({ request }) => {
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length === 0) {
        test.skip();
        return;
      }

      const bookId = books[0].id;
      const response = await request.get(`${API_BASE_URL}/export/${bookId}?format=excel`);
      expect(response.ok()).toBeTruthy();
      expect(response.headers()['content-type']).toContain('spreadsheet');
    });

    test('GET /api/export/:id with invalid format should return 400', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/export/1?format=invalid`);
      expect(response.status()).toBe(400);
    });
  });

  test.describe('Publish', () => {
    test('POST /api/publish with dry_run should simulate publish', async ({ request }) => {
      const listResponse = await request.get(`${API_BASE_URL}/price-books`);
      const books = await listResponse.json();

      if (books.length === 0) {
        test.skip();
        return;
      }

      const response = await request.post(`${API_BASE_URL}/publish`, {
        data: {
          price_book_id: books[0].id,
          dry_run: true
        }
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('price_book_id');
      expect(data).toHaveProperty('dry_run', true);
      expect(data).toHaveProperty('rows_created');
      expect(data).toHaveProperty('rows_updated');
      expect(data).toHaveProperty('rows_processed');
      expect(data).toHaveProperty('duration_seconds');
      expect(data.status).toBe('completed');
    });

    test('GET /api/publish/history should return publish history', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/publish/history?limit=10`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();

      if (data.length > 0) {
        const sync = data[0];
        expect(sync).toHaveProperty('id');
        expect(sync).toHaveProperty('price_book_id');
        expect(sync).toHaveProperty('status');
        expect(sync).toHaveProperty('started_at');
        expect(sync).toHaveProperty('manufacturer');
      }
    });

    test('POST /api/publish without price_book_id should return 400', async ({ request }) => {
      const response = await request.post(`${API_BASE_URL}/publish`, {
        data: {
          dry_run: true
        }
      });

      expect(response.status()).toBe(400);
    });
  });

  test.describe('Delete Operations', () => {
    test('DELETE /api/price-books/:id with invalid ID should return 404', async ({ request }) => {
      const response = await request.delete(`${API_BASE_URL}/price-books/99999`);
      expect(response.status()).toBe(404);
    });
  });
});
