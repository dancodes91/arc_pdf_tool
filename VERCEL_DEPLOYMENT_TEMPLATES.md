# Vercel + Render Deployment: Code Templates & Examples

This document contains ready-to-use code templates and configuration examples for deploying to Vercel with Render backend.

---

## Table of Contents

1. [Configuration Files](#configuration-files)
2. [Backend CORS Configuration](#backend-cors-configuration)
3. [Frontend API Integration](#frontend-api-integration)
4. [Vercel API Routes](#vercel-api-routes)
5. [GitHub Actions Workflows](#github-actions-workflows)
6. [Environment Variable Templates](#environment-variable-templates)
7. [Error Handling & Retry Logic](#error-handling--retry-logic)
8. [Monitoring & Logging](#monitoring--logging)

---

## Configuration Files

### vercel.json - Complete Example

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "name": "my-app",
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "devCommand": "npm run dev",
  "framework": "nextjs",
  "nodeVersion": "18.x",
  "cleanUrls": true,
  "trailingSlash": false,
  "regions": ["iad1"],
  "functions": {
    "pages/api/**/*": {
      "maxDuration": 60,
      "memory": 3008,
      "includeFiles": "**/*"
    },
    "pages/api/health.js": {
      "maxDuration": 5,
      "memory": 128
    }
  },
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "${NEXT_PUBLIC_API_URL}/:path*"
    }
  ],
  "redirects": [
    {
      "source": "/old-page",
      "destination": "/new-page",
      "permanent": true
    },
    {
      "source": "/blog/:path*",
      "destination": "https://blog.example.com/:path*"
    }
  ],
  "headers": [
    {
      "source": "/:path*",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "SAMEORIGIN"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    },
    {
      "source": "/static/:path*",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url",
    "API_SECRET": "@api_secret"
  },
  "crons": [
    {
      "path": "/api/cron/health-check",
      "schedule": "*/5 * * * *"
    }
  ]
}
```

### next.config.js - Complete Example

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.example.com',
        port: '',
        pathname: '/images/**'
      }
    ],
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384]
  },

  // Rewrites for API proxy
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`
        }
      ],
      afterFiles: [
        {
          source: '/docs/:path*',
          destination: 'https://docs.example.com/:path*'
        }
      ],
      fallback: [
        {
          source: '/:path*',
          destination: `/api/fallback?path=:path*`
        }
      ]
    };
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/old-page',
        destination: '/new-page',
        permanent: true
      }
    ];
  },

  // Headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains'
          }
        ]
      }
    ];
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_STRIPE_KEY: process.env.NEXT_PUBLIC_STRIPE_KEY
  },

  // Internationalization
  i18n: {
    locales: ['en', 'fr', 'es'],
    defaultLocale: 'en'
  },

  // Optimization
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compress: true,
  swcMinify: true,

  // Experimental features
  experimental: {
    optimizePackageImports: [
      'lodash-es',
      '@material-ui/core'
    ]
  }
};

module.exports = nextConfig;
```

### .vercelignore

```
# Version control
.git
.gitignore

# Dependencies
node_modules
.yarn/cache
.pnp

# Build files
dist
build
.next
out

# Testing
coverage
.nyc_output

# Environment
.env
.env.local
.env.*.local

# Documentation
*.md
docs
README.md

# IDE
.vscode
.idea
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*

# Temporary
tmp
temp
.cache

# CI/CD
.github/workflows/test.yml
.github/workflows/lint.yml
```

---

## Backend CORS Configuration

### Express.js with CORS Package

**For Render Backend (Node.js)**

```javascript
// server.js or app.js
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const app = express();

// Define allowed origins based on environment
const allowedOrigins = [
  'https://your-app.vercel.app',
  'https://staging.your-app.vercel.app',
  'https://www.your-domain.com',
  'https://your-domain.com'
];

// Add localhost for development
if (process.env.NODE_ENV === 'development') {
  allowedOrigins.push('http://localhost:3000');
  allowedOrigins.push('http://localhost:3001');
}

// CORS configuration
const corsOptions = {
  origin: function(origin, callback) {
    // Allow requests without origin (like mobile apps, Postman, etc.)
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error(`Origin ${origin} not allowed by CORS`));
    }
  },
  credentials: true,
  optionsSuccessStatus: 200,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-API-Key',
    'Accept'
  ],
  maxAge: 86400 // 24 hours
};

// Apply CORS middleware
app.use(cors(corsOptions));

// Body parser middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date() });
});

// Example API endpoints
app.get('/api/users', async (req, res) => {
  try {
    // Your logic here
    res.json({ users: [] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/users', async (req, res) => {
  try {
    // Your logic here
    res.status(201).json({ created: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ error: err.message });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### FastAPI (Python) CORS Configuration

**For Render Backend (Python)**

```python
# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Define allowed origins
allowed_origins = [
    "https://your-app.vercel.app",
    "https://staging.your-app.vercel.app",
    "https://www.your-domain.com",
    "https://your-domain.com"
]

# Add localhost for development
if os.getenv("ENVIRONMENT") == "development":
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:3001"
    ])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-API-Key",
        "Accept"
    ],
    max_age=86400  # 24 hours
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/users")
async def get_users():
    return {"users": []}

@app.post("/api/users")
async def create_user(user: dict):
    return {"created": True}

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return {"error": str(exc)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

---

## Frontend API Integration

### React Hook for API Calls

```typescript
// hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react';

interface UseApiOptions {
  headers?: Record<string, string>;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: any;
  skip?: boolean;
}

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useApi<T>(
  endpoint: string,
  options: UseApiOptions = {}
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!options.skip);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const url = `${apiUrl}${endpoint}`;

      const response = await fetch(url, {
        method: options.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, [endpoint, options]);

  useEffect(() => {
    if (!options.skip) {
      fetchData();
    }
  }, [endpoint, fetchData, options.skip]);

  return { data, loading, error, refetch: fetchData };
}
```

### Usage Example

```typescript
// pages/users.tsx
import { useApi } from '@/hooks/useApi';

interface User {
  id: string;
  name: string;
  email: string;
}

export default function UsersPage() {
  const { data: users, loading, error, refetch } = useApi<User[]>('/api/users');

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>Users</h1>
      <button onClick={refetch}>Refresh</button>
      <ul>
        {users?.map(user => (
          <li key={user.id}>{user.name} - {user.email}</li>
        ))}
      </ul>
    </div>
  );
}
```

### SWR Hook (Alternative)

```typescript
// hooks/useUser.ts
import useSWR from 'swr';

const fetcher = (url: string) =>
  fetch(url, { credentials: 'include' }).then(r => r.json());

export function useUser(userId: string) {
  const { data, error, isLoading } = useSWR(
    `/api/users/${userId}`,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000 // 1 minute
    }
  );

  return {
    user: data,
    loading: isLoading,
    error
  };
}
```

### React Query Hook (Modern Approach)

```typescript
// hooks/useUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

async function fetchUsers() {
  const res = await fetch(`${apiUrl}/api/users`, {
    credentials: 'include'
  });
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}

async function createUser(userData: any) {
  const res = await fetch(`${apiUrl}/api/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
    credentials: 'include'
  });
  if (!res.ok) throw new Error('Failed to create');
  return res.json();
}

export function useUsers() {
  return useQuery(['users'], fetchUsers);
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation(createUser, {
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
    }
  });
}
```

---

## Vercel API Routes

### Proxy API Route (Pages Router)

```typescript
// pages/api/proxy.ts
import type { NextApiRequest, NextApiResponse } from 'next';

type Data = any;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>
) {
  const { endpoint, ...query } = req.query;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    return res.status(500).json({ error: 'API URL not configured' });
  }

  if (!endpoint) {
    return res.status(400).json({ error: 'Endpoint required' });
  }

  const endpointUrl = `${apiUrl}/${Array.isArray(endpoint) ? endpoint.join('/') : endpoint}`;

  try {
    const fetchOptions: RequestInit = {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        ...req.headers,
        // Remove host header to avoid conflicts
        host: undefined
      }
    };

    // Add body for POST/PUT/PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(req.method || '')) {
      fetchOptions.body = JSON.stringify(req.body);
    }

    // Add authentication header if available
    const token = req.headers.authorization;
    if (token) {
      fetchOptions.headers.authorization = token;
    }

    const response = await fetch(endpointUrl, fetchOptions);
    const data = await response.json();

    res.status(response.status).json(data);
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
```

### Proxy API Route (App Router)

```typescript
// app/api/proxy/[...path]/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const endpoint = params.path.join('/');

  if (!apiUrl) {
    return NextResponse.json(
      { error: 'API URL not configured' },
      { status: 500 }
    );
  }

  try {
    const url = new URL(request.url);
    const targetUrl = `${apiUrl}/${endpoint}${url.search}`;

    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        authorization: request.headers.get('authorization') || ''
      }
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const endpoint = params.path.join('/');
  const body = await request.json();

  if (!apiUrl) {
    return NextResponse.json(
      { error: 'API URL not configured' },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(`${apiUrl}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        authorization: request.headers.get('authorization') || ''
      },
      body: JSON.stringify(body)
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
```

### Health Check Cron Job

```typescript
// pages/api/cron/health-check.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export const config = {
  maxDuration: 10
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Verify request is from Vercel
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const response = await fetch(`${apiUrl}/api/health`, {
      timeout: 5000
    });

    const data = await response.json();

    res.status(200).json({
      success: response.ok,
      timestamp: new Date(),
      backend: data
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
```

---

## GitHub Actions Workflows

### Basic Deploy Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Vercel

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        node-version: [18.x]

    steps:
      - uses: actions/checkout@v3

      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm test
      - run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel
        uses: vercel/action@v4
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          production: ${{ github.ref == 'refs/heads/main' }}
```

### Advanced Multi-Environment Workflow

```yaml
# .github/workflows/deploy-multi-env.yml
name: Deploy to Multiple Environments

on:
  push:
    branches: [main, develop, staging]
  pull_request:
    branches: [main]

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}

jobs:
  quality-checks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type Check
        run: npm run type-check

      - name: Tests
        run: npm test -- --coverage

      - name: Build
        run: npm run build

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        if: always()

  deploy-preview:
    needs: quality-checks
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy Preview to Vercel
        uses: vercel/action@v4
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  deploy-staging:
    needs: quality-checks
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy Staging to Vercel
        uses: vercel/action@v4
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.STAGING_PROJECT_ID }}

  deploy-production:
    needs: quality-checks
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy Production to Vercel
        uses: vercel/action@v4
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          production: true

      - name: Notify Slack
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Production deployment successful'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Environment Variable Templates

### .env.example

```env
# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME=My Application
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_STRIPE_KEY=pk_test_xxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=GA-xxx
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx

# Backend Configuration (Server-side only)
API_SECRET=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# JWT & Authentication
JWT_SECRET=your-jwt-secret
JWT_EXPIRY=7d
SESSION_SECRET=your-session-secret

# Third-party Services
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
SENDGRID_API_KEY=SG.xxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Email Configuration
EMAIL_FROM=noreply@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password

# Feature Flags
NEXT_PUBLIC_FEATURE_BETA=false
NEXT_PUBLIC_FEATURE_NEW_UI=true

# Environment
NODE_ENV=development
LOG_LEVEL=debug
```

### Vercel Environment Variables Setup Script

```bash
#!/bin/bash
# scripts/setup-vercel-env.sh

# Usage: ./scripts/setup-vercel-env.sh production

ENVIRONMENT=${1:-development}

echo "Setting up Vercel environment variables for: $ENVIRONMENT"

if [ "$ENVIRONMENT" = "production" ]; then
  echo "→ Setting production environment variables..."

  vercel env add NEXT_PUBLIC_API_URL --prod <<< "https://api.example.com"
  vercel env add API_SECRET --prod <<< "$(openssl rand -base64 32)"
  vercel env add DATABASE_URL --prod
  vercel env add JWT_SECRET --prod <<< "$(openssl rand -base64 32)"
  vercel env add STRIPE_SECRET_KEY --prod
  vercel env add SENDGRID_API_KEY --prod

elif [ "$ENVIRONMENT" = "staging" ]; then
  echo "→ Setting staging environment variables..."

  vercel env add NEXT_PUBLIC_API_URL <<< "https://staging-api.example.com"
  vercel env add API_SECRET <<< "$(openssl rand -base64 32)"

fi

echo "✓ Environment variables setup complete!"
```

---

## Error Handling & Retry Logic

### Retry Utility with Exponential Backoff

```typescript
// utils/fetchWithRetry.ts
interface RetryOptions {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  onRetry?: (attempt: number, error: Error) => void;
}

export async function fetchWithRetry(
  url: string,
  options: RequestInit & RetryOptions = {}
): Promise<Response> {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    backoffMultiplier = 2,
    onRetry,
    ...fetchOptions
  } = options;

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);

      // Don't retry on client errors (4xx)
      if (response.status >= 400 && response.status < 500) {
        return response;
      }

      // Retry on server errors (5xx) and network timeouts
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt === maxRetries) {
        throw lastError;
      }

      // Calculate exponential backoff
      const delay = Math.min(
        baseDelay * Math.pow(backoffMultiplier, attempt),
        maxDelay
      );

      if (onRetry) {
        onRetry(attempt + 1, lastError);
      }

      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error('Unknown error');
}
```

### Usage Example

```typescript
// components/DataFetcher.tsx
import { fetchWithRetry } from '@/utils/fetchWithRetry';

export default function DataFetcher() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetchWithRetry(
          `${process.env.NEXT_PUBLIC_API_URL}/api/data`,
          {
            maxRetries: 3,
            baseDelay: 500,
            onRetry: (attempt, error) => {
              console.log(`Retry attempt ${attempt}: ${error.message}`);
            }
          }
        );
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };

    fetchData();
  }, []);

  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>Loading...</div>;
  return <div>{JSON.stringify(data)}</div>;
}
```

### Error Boundary Component

```typescript
// components/ErrorBoundary.tsx
import React, { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to error tracking service
    console.error('Error caught:', error, errorInfo);

    if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
      // Send to Sentry
      fetch('/api/errors', {
        method: 'POST',
        body: JSON.stringify({
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack
        })
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h1>Something went wrong</h1>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## Monitoring & Logging

### Client-side Error Tracking

```typescript
// lib/errorTracking.ts
export function initializeErrorTracking() {
  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    trackError({
      type: 'error',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack
    });
  });

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    trackError({
      type: 'unhandledRejection',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack
    });
  });
}

interface ErrorLog {
  type: string;
  message: string;
  [key: string]: any;
}

export function trackError(error: ErrorLog) {
  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.error('Tracked error:', error);
  }

  // Send to backend
  if (process.env.NEXT_PUBLIC_API_URL) {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/errors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...error,
        timestamp: new Date(),
        userAgent: navigator.userAgent,
        url: window.location.href
      })
    }).catch(err => {
      // Fail silently to avoid infinite error loops
      console.warn('Failed to send error log:', err);
    });
  }
}
```

### Performance Monitoring

```typescript
// lib/performance.ts
export function monitorPerformance() {
  // Use Web Vitals
  import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
    getCLS(metric => logMetric('CLS', metric));
    getFID(metric => logMetric('FID', metric));
    getFCP(metric => logMetric('FCP', metric));
    getLCP(metric => logMetric('LCP', metric));
    getTTFB(metric => logMetric('TTFB', metric));
  });
}

function logMetric(name: string, metric: any) {
  const data = {
    name,
    value: metric.value,
    rating: metric.rating,
    timestamp: new Date()
  };

  // Send to analytics
  if (process.env.NEXT_PUBLIC_API_URL) {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/metrics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      keepalive: true
    }).catch(err => {
      console.warn('Failed to send metric:', err);
    });
  }

  console.log(`${name}: ${metric.value}`);
}
```

---

## End of Templates Document

These templates provide a solid foundation for deploying applications to Vercel with Render backend. Customize them based on your specific requirements and security policies.
