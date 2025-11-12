# Comprehensive Guide: Deploying Web Applications to Vercel with Render Backend

**Last Updated:** November 2024-2025
**Focus:** Production-ready deployment for Vercel frontend with separate Render backend
**Audience:** Full-stack developers, DevOps engineers, engineering teams

---

## Table of Contents

1. [Best Practices for Vercel Deployment (2024-2025)](#1-best-practices-for-vercel-deployment-2024-2025)
2. [Environment Variables Configuration](#2-environment-variables-configuration)
3. [CORS Configuration](#3-cors-configuration-handling)
4. [API Routes and Proxy Configuration](#4-api-routes-and-proxy-configuration)
5. [Environment-Specific Configurations](#5-environment-specific-configurations)
6. [Custom Domain Setup and DNS](#6-custom-domain-setup-and-dns-configuration)
7. [Build Settings by Framework](#7-build-settings-and-deployment-by-framework)
8. [Troubleshooting and Common Issues](#8-troubleshooting-and-common-issues)
9. [CI/CD Integration with GitHub](#9-cicd-integration-with-github)
10. [Performance Optimization](#10-performance-optimization-tips)
11. [Production Checklist](#11-production-deployment-checklist)

---

## 1. Best Practices for Vercel Deployment (2024-2025)

### 1.1 Core Deployment Principles

**Git Integration & Automation**
- Connect your GitHub/GitLab repository directly to Vercel for automatic deployments
- Vercel automatically creates preview deployments for every branch and pull request
- Only the default branch (typically `main` or `master`) deploys to production
- Preview deployments allow team members to test changes before merging to production

**Code Quality & Testing**
- Run linting and testing before deployment using GitHub Actions or CI/CD
- Use preview deployments extensively to catch issues before production
- Implement automated testing within your CI/CD pipeline
- Monitor deployment logs for warnings and errors

**Security-First Approach**
- Configure the Vercel Web Application Firewall (WAF) to block malicious traffic
- Enable deployment protection to prevent unauthorized deployments
- Set up proper authentication and authorization before going live
- Review SSL certificate configuration and security headers
- Rate limit API endpoints to prevent abuse

**Production Readiness**
- Define an incident response plan with escalation paths and communication channels
- Document rollback procedures for quick recovery from issues
- Establish monitoring and alerting for critical metrics
- Prepare a deployment schedule and communicate changes to stakeholders

### 1.2 New Features in 2024-2025

**Rolling Releases**
- Gradually rollout new deployments to a subset of users
- Built-in monitoring of feature adoption
- No custom routing configuration required
- Reduces risk of widespread issues from breaking changes

**Image Optimization Pricing**
- Review and opt-in to new pricing tiers if you have high image optimization costs
- Leverage automatic image optimization for responsive design

**Vercel Speed Insights**
- Enable to collect real field performance data (Core Web Vitals)
- Correlate performance changes with code deployments
- Identify which functions or resources impact performance

---

## 2. Environment Variables Configuration

### 2.1 Understanding Environment Variable Scopes

Environment variables in Vercel are scoped to specific environments and branches:

| Scope | Usage | Applies To |
|-------|-------|-----------|
| **Production** | Main branch deployments | `main`/`master` branch |
| **Preview** | Non-main branch deployments | All PR and feature branch previews |
| **Development** | Local development | `.env.local` file (not committed) |
| **Custom** | Team or project-level | Can be imported to other environments |

### 2.2 Setting Up Environment Variables

**Via Vercel Dashboard**
1. Navigate to Project Settings → Environment Variables
2. Add new key-value pairs
3. Select which environments the variable applies to (Production, Preview, Development)
4. Optionally scope to specific Git branches
5. Save and redeploy the project for changes to take effect

**Via Vercel CLI**
```bash
# Pull environment variables to local .env file
vercel env pull

# Deploy with specific environment variables
vercel deploy --env DATABASE_URL=xyz --env API_KEY=abc

# Deploy to production with environment variables
vercel deploy --prod --env DATABASE_URL=xyz
```

**Via vercel.json Configuration**
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "env": {
    "DATABASE_URL": "@database_url",
    "API_KEY": "@api_key"
  }
}
```

### 2.3 Configuring Backend API Connection

**For Next.js/React Applications**

Create environment variables for your Render backend:

```bash
# In Vercel Project Settings → Environment Variables

# Production environment
NEXT_PUBLIC_API_URL=https://your-app.onrender.com
API_SECRET=your-secret-key-here
DATABASE_URL=your-database-url

# Preview environment
NEXT_PUBLIC_API_URL=https://staging-api.onrender.com
API_SECRET=preview-secret-key
DATABASE_URL=staging-database-url
```

**Important: NEXT_PUBLIC_ Prefix**

- Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser and included in JavaScript bundles
- **Use this prefix only for non-sensitive variables** that are safe to expose publicly
- Backend URLs, authentication tokens, and API keys should NOT have this prefix
- In Next.js, variables without the prefix are only available on the server-side (API routes, getServerSideProps, etc.)

**Example Environment Variable Structure**
```javascript
// This is exposed to the browser
export const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// This is server-only (API routes)
const dbUrl = process.env.DATABASE_URL;
const apiSecret = process.env.API_SECRET;
```

### 2.4 Accessing Environment Variables in Code

**Next.js API Routes (Server-Side)**
```javascript
// pages/api/users.js
export default async function handler(req, res) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const apiSecret = process.env.API_SECRET;

  try {
    const response = await fetch(`${apiUrl}/users`, {
      headers: {
        'Authorization': `Bearer ${apiSecret}`
      }
    });
    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
```

**React Components (Client-Side)**
```javascript
import { useEffect, useState } from 'react';

export default function UsersList() {
  const [users, setUsers] = useState([]);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    fetch(`${apiUrl}/users`)
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(err => console.error(err));
  }, [apiUrl]);

  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

### 2.5 Environment Variable Size Limits

- **General limit**: 64 KB total per deployment
- **Edge Functions**: 5 KB per individual variable
- Large configuration objects should be stored in a separate configuration file or database

### 2.6 Best Practices

- Never commit `.env.local` or `.env` files to version control
- Use `.env.example` file to document required variables without sensitive values
- Rotate secrets regularly, especially API keys
- Use branch-specific overrides only for values that differ from production
- Document all required environment variables in your README

---

## 3. CORS Configuration Handling

### 3.1 Understanding CORS Issues with Vercel Frontend + Render Backend

When your frontend on Vercel makes requests to your backend on Render, browsers enforce Cross-Origin Resource Sharing (CORS) policies. The browser will block requests unless the backend explicitly allows them.

**Common Error**
```
Access to XMLHttpRequest at 'https://your-api.onrender.com/api/data'
from origin 'https://your-app.vercel.app' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### 3.2 Essential CORS Headers

Your backend must return these headers in its responses:

| Header | Purpose | Example |
|--------|---------|---------|
| `Access-Control-Allow-Origin` | Specify allowed origins | `https://your-app.vercel.app` |
| `Access-Control-Allow-Methods` | Specify allowed HTTP verbs | `GET, POST, PUT, DELETE, OPTIONS` |
| `Access-Control-Allow-Headers` | Allow custom headers | `Content-Type, Authorization` |
| `Access-Control-Allow-Credentials` | Allow cookies/auth | `true` |
| `Access-Control-Max-Age` | Cache preflight response | `86400` (24 hours) |

### 3.3 Backend CORS Configuration (Express/Node.js on Render)

**Using cors Package**
```javascript
const express = require('express');
const cors = require('cors');
const app = express();

// Option 1: Specific origins (Recommended for Production)
const corsOptions = {
  origin: [
    'https://your-app.vercel.app',
    'https://staging.your-app.vercel.app',
    'http://localhost:3000' // for local development
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  maxAge: 86400 // 24 hours
};

app.use(cors(corsOptions));

// Option 2: Dynamic origin validation
const dynamicCorsOptions = {
  origin: function(origin, callback) {
    const allowedOrigins = [
      'https://your-app.vercel.app',
      'https://staging.your-app.vercel.app',
      'http://localhost:3000'
    ];

    if (allowedOrigins.includes(origin) || !origin) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
};

app.use(cors(dynamicCorsOptions));

// Your routes
app.get('/api/data', (req, res) => {
  res.json({ message: 'Success!' });
});
```

**Manual Header Configuration**
```javascript
app.use((req, res, next) => {
  const origin = req.headers.origin;
  const allowedOrigins = [
    'https://your-app.vercel.app',
    'https://staging.your-app.vercel.app'
  ];

  if (allowedOrigins.includes(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
    res.header('Access-Control-Allow-Credentials', 'true');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  }

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});
```

### 3.4 Frontend CORS Handling (Vercel)

**Option 1: Direct API Calls with Headers**
```javascript
// Add authentication headers if needed
const headers = {
  'Content-Type': 'application/json'
};

if (typeof window !== 'undefined') {
  const token = localStorage.getItem('authToken');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
}

fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/data`, {
  method: 'GET',
  headers: headers,
  credentials: 'include' // Include cookies if using session-based auth
})
.then(res => res.json())
.catch(err => console.error('CORS Error:', err));
```

**Option 2: Using Vercel API Routes as Proxy** (See section 4.1)

### 3.5 Handling Preflight Requests

Browsers automatically send an `OPTIONS` preflight request before making certain requests:
- Requests with custom headers
- POST/PUT/DELETE requests
- Requests with custom Content-Type

Your backend must respond to OPTIONS requests with proper CORS headers:

```javascript
app.options('/api/*', cors(corsOptions)); // Enable preflight for all API routes
app.options('*', cors(corsOptions)); // Enable preflight for all routes
```

### 3.6 Common CORS Debugging Tips

1. **Check browser console** for the exact CORS error message
2. **Use Network tab** to inspect the preflight OPTIONS request
3. **Verify the origin** matches exactly (including protocol and port)
4. **Don't use `*` for origin** in production - always specify exact domains
5. **Test with curl** to verify CORS headers from backend:
   ```bash
   curl -H "Origin: https://your-app.vercel.app" -v https://your-api.onrender.com/api/data
   ```

### 3.7 Alternative: Vercel Proxy Configuration

Instead of configuring CORS on your backend, you can use Vercel's `rewrites` feature (see section 4.2).

---

## 4. API Routes and Proxy Configuration

### 4.1 Using Next.js API Routes as Proxy

Instead of allowing CORS from the backend, proxy requests through Vercel:

**Create an API Route**
```javascript
// pages/api/proxy.js or app/api/proxy/route.ts (App Router)
import { NextResponse } from 'next/server';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/${endpoint}`,
      {
        headers: {
          'Authorization': `Bearer ${process.env.API_SECRET}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

export async function POST(request) {
  const { endpoint, body } = await request.json();

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/${endpoint}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.API_SECRET}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      }
    );

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}
```

**Use from Frontend**
```javascript
// No CORS issues - request goes to same domain
const response = await fetch('/api/proxy?endpoint=users');
const data = await response.json();
```

### 4.2 Using vercel.json Rewrites

Configure rewrites in `vercel.json` to proxy requests to your backend:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-api.onrender.com/:path*"
    },
    {
      "source": "/api/v2/:path*",
      "destination": "https://your-api-v2.onrender.com/:path*"
    }
  ]
}
```

**Important Considerations**
- Rewrites are internal - the URL stays the same in the browser
- This approach avoids CORS entirely
- Backend credentials should be passed via environment variables
- The rewrite happens on Vercel's servers before reaching the client

### 4.3 Using Next.js Rewrites (Recommended)

For Next.js applications, use the built-in rewrites feature:

**next.config.js**
```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`
      }
    ];
  }
};
```

### 4.4 Handling Headers in Proxied Requests

When proxying through Vercel, add necessary headers:

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
        headers: [
          {
            key: 'Authorization',
            value: process.env.API_SECRET
          },
          {
            key: 'X-API-Version',
            value: '1.0'
          }
        ]
      }
    ];
  }
};
```

### 4.5 API Route Configuration in vercel.json

Configure specific behavior for API functions:

```json
{
  "functions": {
    "pages/api/**/*": {
      "maxDuration": 60,
      "memory": 3008,
      "timeoutSeconds": 60
    },
    "api/health-check.js": {
      "maxDuration": 10,
      "memory": 512
    }
  }
}
```

---

## 5. Environment-Specific Configurations

### 5.1 Development Environment

**Local Setup**
```bash
# Pull development variables from Vercel
vercel env pull

# This creates a .env.local file (add to .gitignore)
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:5000
API_SECRET=dev-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/dev_db
EOF

# Run locally
npm run dev
```

**.env.local Example**
```env
# Frontend variables
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME=My App Dev

# Server-side variables
API_SECRET=dev-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/dev_db
STRIPE_SECRET_KEY=sk_test_xxx
```

### 5.2 Staging Environment Setup

**Option 1: Dedicated Staging Branch**

Create a `staging` branch that deploys to a different Vercel environment:

```bash
# Create staging branch
git checkout -b staging
git push -u origin staging
```

**Vercel Configuration**
1. Go to Project Settings → Environments
2. Create a custom environment for the staging branch
3. Set branch rule: `staging`
4. Add custom domain (e.g., `staging.your-app.vercel.app`)
5. Override environment variables for staging:

| Variable | Production | Staging |
|----------|-----------|---------|
| `NEXT_PUBLIC_API_URL` | `https://api.onrender.com` | `https://staging-api.onrender.com` |
| `STRIPE_PUBLIC_KEY` | `pk_live_xxx` | `pk_test_xxx` |
| `ANALYTICS_ENABLED` | `true` | `true` |

**Option 2: Branch-Specific Environment Variables**

For simpler setups, use branch-specific variable overrides:

```bash
# Set variables for the staging branch
vercel env add NEXT_PUBLIC_API_URL --git-branch staging
# Then when prompted, enter: https://staging-api.onrender.com
```

### 5.3 Production Environment

**Best Practices**
- Only the default branch should deploy to production
- Require approval before production deployments
- Enable deployment protection in Project Settings
- Use production-specific secrets with high security standards
- Monitor production deployments closely

**Production Environment Variables**
```env
# Production API endpoints
NEXT_PUBLIC_API_URL=https://api.onrender.com

# Production secrets
STRIPE_SECRET_KEY=sk_live_xxx
DATABASE_URL=postgresql://prod_user:prod_pass@prod-db.onrender.com:5432/prod_db
JWT_SECRET=production-jwt-secret-key
SESSION_SECRET=production-session-secret-key

# Production feature flags
NEXT_PUBLIC_ANALYTICS_ENABLED=true
NEXT_PUBLIC_SENTRY_ENABLED=true
```

### 5.4 Managing Environment Variable Overrides

Variables at lower levels override those at higher levels:

```
Team Level
    ↓
Project Level
    ↓
Environment Level (Production/Preview/Development)
    ↓
Branch-Specific Level (highest priority)
```

**Example Hierarchy**
```
Team: API_URL=https://default-api.com
Project: API_URL=https://project-api.com  (overrides team)
Production: API_URL=https://prod-api.com (overrides project)
main-branch: API_URL=https://main-api.com (overrides production)
```

---

## 6. Custom Domain Setup and DNS Configuration

### 6.1 Adding a Custom Domain to Vercel

**Step 1: Navigate to Domain Settings**
1. Go to Project Settings → Domains
2. Click "Add Domain"
3. Enter your custom domain (e.g., `example.com`)

**Step 2: Choose DNS Configuration Method**

#### Method 1: Nameserver Method (Recommended)

1. In Vercel, select "Nameservers"
2. Click "Enable Vercel DNS"
3. Copy the provided nameservers:
   - `ns1.vercel-dns.com`
   - `ns2.vercel-dns.com`
   - `ns3.vercel-dns.com`
   - `ns4.vercel-dns.com`

4. Go to your domain registrar (GoDaddy, Namecheap, etc.)
5. Update nameservers to Vercel's nameservers
6. Wait up to 48 hours for DNS propagation (usually much faster)

**Important:** If you had existing DNS records with another provider, you need to add them to Vercel's DNS management:
- Go to Project Settings → Domains → your-domain.com → Edit DNS Records
- Recreate any essential records (mail, verification, etc.)

#### Method 2: DNS Records Method

If you want to keep your current DNS provider:

1. In Vercel, select "DNS Records"
2. Add the following records in your registrar's dashboard:

| Type | Name | Value |
|------|------|-------|
| A | @ | 76.76.21.21 |
| CNAME | www | cname.vercel-dns.com |

For subdomains (e.g., `blog.example.com`):
| Type | Name | Value |
|------|------|-------|
| CNAME | blog | cname.vercel-dns.com |

### 6.2 SSL/TLS Certificate Setup

Vercel automatically provisions free SSL certificates via Let's Encrypt:

**Automatic Configuration**
- Once your domain is verified, Vercel automatically generates an SSL certificate
- Wildcard certificates are issued automatically (*.yourdomain.com)
- Certificates are renewed automatically before expiration
- HTTPS is enabled by default

**Troubleshooting Certificate Generation**

If your certificate isn't generating:

1. **Check CAA Records**: Ensure your domain's CAA record allows Let's Encrypt:
   ```
   0 issue "letsencrypt.org"
   0 issuewild "letsencrypt.org"
   ```

2. **Verify DNS Configuration**:
   - Confirm A and CNAME records are correctly set
   - DNS must be fully configured before certificate generation
   - Give DNS changes time to propagate

3. **Cloudflare Proxy Issue**:
   - If using Cloudflare, disable proxying during certificate validation
   - Let's Encrypt needs direct HTTP-01 access
   - You can re-enable proxying after certificate is issued

4. **Custom SSL Certificates** (Enterprise only):
   - Upload your own certificate in Project Settings → Domains → SSL Certificates
   - Requires PEM format for both certificate and private key

### 6.3 DNS Record Management

**Via Vercel Dashboard**
1. Go to Project Settings → Domains → Your Domain → Manage DNS Records
2. View and edit records directly in Vercel
3. Common record types: A, AAAA, ALIAS, CAA, CNAME, MX, SRV, TXT

**Important TTL Settings**
- Default TTL: 60 seconds (allows quick updates)
- For production: Consider 3600 seconds (1 hour) for stability
- Custom TTLs available in Vercel DNS management

**Verification Records**
Some services require verification. Add their TXT records in Vercel DNS:
```
Example: Google Search Console verification
Type: TXT
Name: @
Value: google-site-verification=abc123xyz456
```

### 6.4 Configuring Subdomains

**API Subdomain Example**
```
1. Add domain: api.example.com
2. In Vercel, select the API project
3. Add domain api.example.com
4. Set CNAME: cname.vercel-dns.com
```

**Mail Records for Subdomains**
If your main domain has MX records for email, they work across all subdomains automatically. No need to recreate them.

### 6.5 Multiple Environments with Different Domains

**Configuration Example**
- Production: `example.com` → Production project
- Staging: `staging.example.com` → Staging project
- API: `api.example.com` → API gateway project

Each domain points to different Vercel projects with their own environment variables and deployments.

---

## 7. Build Settings and Deployment by Framework

### 7.1 Framework Auto-Detection

Vercel automatically detects your framework and applies correct settings:

| Framework | Detection Method | Default Build Command | Output Directory |
|-----------|-----------------|----------------------|------------------|
| Next.js | `next.config.js` | `next build` | `.next` |
| React (CRA) | `react-scripts` in package.json | `react-scripts build` | `build` |
| Vue 3 | `vue.config.js` | `vite build` | `dist` |
| Nuxt | `nuxt.config.js` | `nuxt build` | `.nuxt` |
| Vite | `vite.config.js` | `vite build` | `dist` |
| Astro | `astro.config.mjs` | `astro build` | `dist` |

### 7.2 Next.js Specific Configuration

**next.config.js - API Routes and Rewrites**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.example.com',
        port: '',
        pathname: '/images/**'
      }
    ]
  },

  // Configure rewrites for API proxy
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`
      }
    ];
  },

  // Redirect configuration
  async redirects() {
    return [
      {
        source: '/old-page',
        destination: '/new-page',
        permanent: true
      }
    ];
  },

  // Custom headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          }
        ]
      }
    ];
  }
};

module.exports = nextConfig;
```

**Middleware for CORS and Authentication**
```javascript
// middleware.ts or middleware.js
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Add security headers
  const response = NextResponse.next();
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');

  // Handle authentication
  const token = request.cookies.get('authToken')?.value;
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return response;
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*']
};
```

### 7.3 React (Create React App) Configuration

**vercel.json Configuration**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "build",
  "framework": "create-react-app",
  "env": {
    "REACT_APP_API_URL": "@api_url"
  }
}
```

**Environment Variables for React**
- React requires `REACT_APP_` prefix for client-side access
- Only variables with this prefix are available in the browser
- Restart dev server after adding new variables

**.env.local**
```env
REACT_APP_API_URL=http://localhost:5000
REACT_APP_APP_NAME=My App
REACT_APP_STRIPE_KEY=pk_test_xxx
```

### 7.4 Vue 3 / Nuxt Configuration

**vercel.json for Vue 3**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "nuxt"
}
```

**nuxt.config.ts**
```typescript
export default defineNuxtConfig({
  // API base URL
  ssr: true,
  runtimeConfig: {
    public: {
      apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:3001'
    },
    apiSecret: process.env.API_SECRET // Server-only
  },

  // Middleware for API proxy
  nitro: {
    prerender: {
      crawlLinks: true
    }
  }
});
```

**Environment Variables for Nuxt**
- Use `NUXT_PUBLIC_` prefix for client-side variables
- `NUXT_` prefix for server-side only

### 7.5 Custom Build Configuration

**Override Build Command**
```json
{
  "buildCommand": "npm run custom-build",
  "outputDirectory": "dist",
  "installCommand": "npm ci --prefer-offline"
}
```

**Conditional Build Steps**
```json
{
  "ignoreCommand": "git diff --quiet HEAD^ HEAD -- ./src/ ./package.json"
}
```
This skips build if only docs or config changed, not actual source code.

### 7.6 Install and Build Commands

**npm-specific**
```json
{
  "installCommand": "npm ci",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev"
}
```

**yarn-specific**
```json
{
  "installCommand": "yarn install --frozen-lockfile",
  "buildCommand": "yarn build",
  "devCommand": "yarn dev"
}
```

**pnpm-specific**
```json
{
  "installCommand": "pnpm install --frozen-lockfile",
  "buildCommand": "pnpm build",
  "devCommand": "pnpm dev"
}
```

---

## 8. Troubleshooting and Common Issues

### 8.1 Build Failures

**Issue: "Module not found" or dependency errors**
```
Error: Cannot find module 'react'
```

**Solutions:**
1. Verify package.json has the correct dependencies
2. Check dependency versions match your code
3. Run locally with exact build command: `npm run build`
4. Check for missing peer dependencies
5. Clear Vercel cache and redeploy:
   - Go to Settings → Git
   - Click "Redeploy" button (not "New Deployment")

**Issue: Build times exceeding limits**

**Solutions:**
1. Identify slow dependencies: `npm audit` and `npm ls`
2. Use dynamic imports for large packages:
   ```javascript
   const HeavyComponent = dynamic(() => import('./Heavy'), {
     loading: () => <Loading />
   });
   ```
3. Reduce or remove heavy dev dependencies from production builds
4. Enable caching in vercel.json:
   ```json
   {
     "crons": [{
       "path": "/api/rebuild-cache",
       "schedule": "0 0 * * 0"
     }]
   }
   ```

### 8.2 Environment Variable Issues

**Issue: Variables not accessible in deployed app**

**Solutions:**
1. Verify variables are set in correct environment (Production vs Preview)
2. For Next.js, ensure `NEXT_PUBLIC_` prefix for client-side variables
3. Redeploy after adding variables (they don't apply retroactively)
4. Check variable scoping - branch-specific variables override global ones
5. Use Vercel CLI to verify: `vercel env list`

**Issue: "undefined" environment variable in browser**

**Solutions:**
```javascript
// Wrong - not exposed to browser
const api = process.env.API_URL; // undefined

// Correct - use NEXT_PUBLIC_ prefix
const api = process.env.NEXT_PUBLIC_API_URL; // works
```

### 8.3 CORS Errors

**Issue: "No 'Access-Control-Allow-Origin' header"**

**Solutions:**
1. Add CORS headers to your Render backend (see section 3.3)
2. Use Vercel rewrites to proxy requests (see section 4.2)
3. Use Next.js API routes as intermediary (see section 4.1)
4. Check that allowed origins exactly match (protocol, domain, port)

**Testing CORS locally:**
```bash
# Test from frontend
curl -H "Origin: https://your-app.vercel.app" \
     -v https://your-api.onrender.com/api/test

# Check response headers for Access-Control-*
```

### 8.4 API Route Errors

**Issue: API route returns 404**

**Solutions:**
1. Verify file structure: `pages/api/route-name.js` or `app/api/route-name/route.ts`
2. Check for syntax errors in the route handler
3. Ensure export is correct (default export for Pages Router)
4. Check case sensitivity in route paths

**Issue: API route timeout (504)**

**Solutions:**
1. Increase function timeout in vercel.json:
   ```json
   {
     "functions": {
       "pages/api/**/*": {
         "maxDuration": 60
       }
     }
   }
   ```

2. Optimize function execution:
   - Reduce database query time
   - Implement pagination for large datasets
   - Use caching where possible
   - Consider background jobs for heavy processing

3. Enable Fluid Compute for longer timeouts (up to 15 minutes)

### 8.5 Performance Issues

**Issue: Slow initial load times**

**Solutions:**
1. Enable Speed Insights: Project Settings → Analytics → Enable Speed Insights
2. Optimize images with Next.js Image component
3. Enable compression: vercel.json settings
4. Reduce JavaScript bundle size
5. Implement code splitting

**Issue: High Function Duration**

**Solutions:**
1. Profile your API routes: add console.time() and console.timeEnd()
2. Move heavy operations to background jobs
3. Implement caching with Redis or similar
4. Optimize database queries

### 8.6 Authentication & Access Issues

**Issue: "Project configuration belongs to a different team"**

**Solutions:**
1. Remove `.vercel` folder from your repository
2. Re-link the project: `vercel link`
3. Redeploy: `vercel deploy --prod`

**Issue: Two-factor enforcement preventing deployment**

**Solutions:**
1. Ensure all team members have 2FA enabled
2. Use Vercel tokens instead of password authentication
3. Generate a token: vercel.com/account/tokens
4. Use token for CI/CD: `vercel deploy --token $VERCEL_TOKEN`

### 8.7 Preview Deployment Issues

**Issue: Preview deployment doesn't match production**

**Solutions:**
1. Verify preview environment variables match production
2. Check .vercelignore doesn't exclude important files
3. Clear build cache: Go to Settings → Git → Redeploy
4. Ensure the same build command runs for all environments

### 8.8 Debugging with Vercel Logs

**Access Build Logs**
1. Go to Deployments tab
2. Click on specific deployment
3. View build logs in detail

**Common Log Patterns**
- `> npm run build` - Build command starting
- `> Failed to compile` - Compilation error (check next lines)
- `> Output directory "dist" is not a valid directory` - Wrong output dir
- `> Function Scheduled Task` - Cron job execution

**Using Vercel CLI for Debugging**
```bash
# Test build locally
vercel build

# Run locally with production settings
vercel env pull
npm run build
npm start

# Deploy with verbose logs
vercel deploy --prod --debug
```

---

## 9. CI/CD Integration with GitHub

### 9.1 Vercel's Automatic GitHub Integration

**Setup Process**
1. Connect GitHub account to Vercel
2. Select repository to import
3. Vercel creates a GitHub app installation
4. Automatic deployments trigger on git events

**Automatic Behavior**
- Push to main branch → Production deployment
- Push to other branches → Preview deployment
- Pull request created → Preview deployment with unique URL
- Pull request closed → Preview URL removed
- Force push → New deployment (don't force push to main!)

**Benefits**
- Zero configuration needed
- Automatic preview URLs
- Instant rollbacks via GitHub
- No extra CI runner costs

### 9.2 GitHub Actions Integration (Advanced)

Use GitHub Actions when you need:
- Custom testing before deployment
- Linting and code quality checks
- Complex build workflows
- Multi-stage deployments

**Workflow File Setup**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      # Install dependencies
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - run: npm ci

      # Run tests
      - name: Run tests
        run: npm run test

      # Run linting
      - name: Run linting
        run: npm run lint

      # Build locally to catch errors early
      - name: Build
        run: npm run build

      # Deploy preview to Vercel
      - name: Deploy preview to Vercel
        uses: vercel/action@v4
        if: github.event_name == 'pull_request'
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

      # Deploy to production
      - name: Deploy to Vercel Production
        uses: vercel/action@v4
        if: github.ref == 'refs/heads/main'
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          production: true
```

### 9.3 Setting Up GitHub Action Secrets

**Add Secrets to Repository**
1. Go to GitHub → Repository Settings → Secrets and variables → Actions
2. Add these secrets:
   - `VERCEL_TOKEN` - Generate from vercel.com/account/tokens
   - `VERCEL_ORG_ID` - Found in Vercel account settings
   - `VERCEL_PROJECT_ID` - Found in project settings

**Getting Project ID from Vercel**
```bash
# Run in project directory
vercel link

# Or find in .vercel/project.json
cat .vercel/project.json
```

### 9.4 Advanced Workflow Examples

**Multi-Environment Deployment**

```yaml
name: Deploy to Multiple Environments

on:
  push:
    branches: [main, develop, staging]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm ci && npm run build

      # Deploy based on branch
      - name: Deploy to Production
        if: github.ref == 'refs/heads/main'
        run: vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}

      - name: Deploy to Staging
        if: github.ref == 'refs/heads/staging'
        env:
          VERCEL_PROJECT_ID: ${{ secrets.STAGING_PROJECT_ID }}
        run: vercel deploy --token ${{ secrets.VERCEL_TOKEN }}

      - name: Deploy to Development
        if: github.ref == 'refs/heads/develop'
        env:
          VERCEL_PROJECT_ID: ${{ secrets.DEV_PROJECT_ID }}
        run: vercel deploy --token ${{ secrets.VERCEL_TOKEN }}
```

**With Code Quality Checks**

```yaml
name: Test and Deploy

on: [push, pull_request]

jobs:
  quality-checks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Test
        run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json

      - name: Build
        run: npm run build

  deploy:
    needs: quality-checks
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

### 9.5 Deployment Notifications

**Slack Notifications**

```yaml
name: Deploy with Notifications

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm ci && npm run build

      - name: Deploy
        run: vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }}

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 10. Performance Optimization Tips

### 10.1 Core Web Vitals Optimization

**Largest Contentful Paint (LCP)** - Loading Performance

```javascript
// next/image for automatic optimization
import Image from 'next/image';

export default function Hero() {
  return (
    <Image
      src="/hero.jpg"
      alt="Hero"
      width={1200}
      height={600}
      priority={true} // Load immediately, don't lazy load
    />
  );
}
```

**Interaction to Next Paint (INP)** - Responsiveness

```javascript
// Defer non-critical JavaScript
const HeavyComponent = dynamic(() => import('./Heavy'), {
  ssr: false,
  loading: () => <Skeleton />
});

// Break long tasks into smaller chunks
const handleClick = async () => {
  // Process in chunks
  for (let i = 0; i < items.length; i += 100) {
    await new Promise(resolve => setTimeout(resolve, 0));
    processChunk(items.slice(i, i + 100));
  }
};
```

**Cumulative Layout Shift (CLS)** - Visual Stability

```css
/* Reserve space for images */
img {
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
}

/* Avoid inserting content above existing content */
.ad-container {
  min-height: 250px; /* Reserve space for ads */
}
```

### 10.2 Image Optimization

**Next.js Image Component**

```javascript
import Image from 'next/image';

// Automatic optimization
export default function OptimizedImage() {
  return (
    <Image
      src="/product.jpg"
      alt="Product"
      width={800}
      height={600}
      quality={75}
      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 800px"
      placeholder="blur"
      blurDataURL="data:image/jpeg;base64,..." // Low-res placeholder
      loading="lazy" // Default - loads on viewport entry
    />
  );
}
```

**Configuration in next.config.js**

```javascript
const nextConfig = {
  images: {
    domains: ['api.example.com', 'cdn.example.com'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 60, // 1 minute
    dangerouslyAllowSVG: false
  }
};
```

### 10.3 JavaScript Optimization

**Code Splitting**

```javascript
// Split code by route
import dynamic from 'next/dynamic';

const Dashboard = dynamic(() => import('./Dashboard'), { ssr: false });
const Reports = dynamic(() => import('./Reports'), { ssr: false });

export default function App({ path }) {
  return path === '/dashboard' ? <Dashboard /> : <Reports />;
}
```

**Tree Shaking**

```javascript
// Bad - imports entire library
import * as lodash from 'lodash';

// Good - imports only needed functions
import { debounce } from 'lodash-es';
```

**Bundle Analysis**

```bash
# Install bundle analyzer
npm install @next/bundle-analyzer

# Analyze bundle
ANALYZE=true npm run build
```

### 10.4 Caching Strategies

**HTTP Caching Headers in vercel.json**

```json
{
  "headers": [
    {
      "source": "/static/:path*",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    },
    {
      "source": "/:path*",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=3600, s-maxage=60"
        }
      ]
    }
  ]
}
```

**API Response Caching**

```javascript
// Cache API responses for 60 seconds
export const revalidate = 60;

export async function GET() {
  const data = await fetch('https://api.example.com/data', {
    next: { revalidate: 60 }
  });
  return Response.json(data);
}
```

**Incremental Static Regeneration (ISR)**

```javascript
export const revalidate = 60; // Revalidate every 60 seconds

export async function generateStaticParams() {
  const products = await fetch('https://api.example.com/products');
  return products.map(p => ({ slug: p.slug }));
}

export default async function ProductPage({ params }) {
  const product = await fetch(`https://api.example.com/products/${params.slug}`);
  return <ProductDetail product={product} />;
}
```

### 10.5 Edge Functions for Geolocation

**Middleware for Content Personalization**

```javascript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Get user's country from Vercel headers
  const country = request.geo?.country;
  const response = NextResponse.next();

  // Set header based on location
  response.headers.set('X-User-Country', country || 'US');

  // Redirect to region-specific page
  if (country === 'DE') {
    return NextResponse.redirect(new URL('/de', request.url));
  }

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)']
};
```

**Edge Function for API Response Caching**

```javascript
// pages/api/cache.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export const config = {
  runtime: 'edge'
};

export async function GET(request: NextRequest) {
  // This runs on Vercel Edge Network
  const url = new URL(request.url);
  const cacheKey = url.pathname + url.search;

  // Check cache
  const cached = await CACHE.get(cacheKey);
  if (cached) {
    return new Response(cached, {
      headers: { 'X-Cache': 'hit' }
    });
  }

  // Fetch and cache
  const response = await fetch('https://api.example.com/data');
  const data = await response.json();

  await CACHE.set(cacheKey, JSON.stringify(data), { ex: 3600 });

  return NextResponse.json(data, {
    headers: { 'X-Cache': 'miss' }
  });
}
```

### 10.6 Database Connection Optimization

**HTTP Connection Pooling**

```javascript
// api/db.ts - Reuse HTTP connections
import http from 'http';
import https from 'https';

// Create agents outside handler
const httpAgent = new http.Agent({ keepAlive: true, keepAliveMsecs: 10000 });
const httpsAgent = new https.Agent({ keepAlive: true, keepAliveMsecs: 10000 });

export default async function handler(req, res) {
  // Reuse connection across requests
  const response = await fetch('https://db.example.com/query', {
    agent: httpsAgent
  });
  res.json(await response.json());
}
```

**PostgreSQL Connection Pooling**

```javascript
// lib/db.ts
import { Pool } from 'pg';

// Single pool instance for entire serverless function
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 1, // Limit connections for serverless
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

export async function query(text, params) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log('Executed query', { text, duration, rows: result.rowCount });
    return result;
  } catch (error) {
    console.error('Database error', error);
    throw error;
  }
}
```

### 10.7 Monitor Performance

**Enable Vercel Analytics**

```bash
npm install @vercel/analytics react

# In your app root
import { Analytics } from "@vercel/analytics/react";

export default function App() {
  return (
    <>
      <YourApp />
      <Analytics />
    </>
  );
}
```

**Check Deployments in Dashboard**
- Go to Analytics tab for Core Web Vitals
- View real user metrics
- Compare deployments to see performance impact

---

## 11. Production Deployment Checklist

### 11.1 Pre-Deployment Verification

#### Code Quality
- [ ] All tests passing (`npm test`)
- [ ] Linting clean (`npm run lint`)
- [ ] Type checking passes (`npm run type-check`)
- [ ] No console.log or debug statements left
- [ ] All dependencies up to date and secured
- [ ] Reviewed for security vulnerabilities (`npm audit`)

#### Functionality Testing
- [ ] All features working in staging environment
- [ ] User authentication/authorization working
- [ ] Error handling and edge cases covered
- [ ] Forms validating correctly
- [ ] API integration tested with production-like data
- [ ] Payment processing (if applicable) tested

#### Performance Verification
- [ ] Core Web Vitals scores acceptable
- [ ] Lighthouse score > 90
- [ ] Bundle size optimized
- [ ] Images compressed and optimized
- [ ] API response times acceptable
- [ ] Load testing completed (if applicable)

### 11.2 Configuration Verification

#### Environment Setup
- [ ] All environment variables set in production environment
- [ ] Database migrations completed
- [ ] Cache invalidation strategy defined
- [ ] Backup and recovery procedures documented
- [ ] Monitoring and alerting configured

#### Domain & SSL
- [ ] Custom domain configured
- [ ] SSL certificate issued and valid
- [ ] DNS records properly configured
- [ ] Email receiving working (if using domain for email)
- [ ] Wildcard certificates configured for subdomains

#### API Integration
- [ ] Backend API reachable from production
- [ ] CORS headers properly configured
- [ ] API authentication working
- [ ] Rate limiting configured
- [ ] API versioning strategy in place

### 11.3 Security Checklist

#### Application Security
- [ ] HTTPS enforced (redirect http to https)
- [ ] Security headers configured:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: SAMEORIGIN
  - Strict-Transport-Security
  - Content-Security-Policy
- [ ] CSRF protection enabled
- [ ] XSS protection measures in place
- [ ] SQL injection prevention verified
- [ ] Sensitive data not logged or exposed in client

#### Access Control
- [ ] Two-factor authentication for admin accounts
- [ ] Role-based access control implemented
- [ ] Deployment protection enabled
- [ ] Team member access reviewed
- [ ] API keys and secrets properly stored

#### Monitoring & Logging
- [ ] Error tracking configured (Sentry, LogRocket, etc.)
- [ ] Performance monitoring enabled
- [ ] Server logs being collected
- [ ] Real-time alerting for critical errors
- [ ] Audit logging for important actions

### 11.4 Operational Readiness

#### Documentation
- [ ] Deployment procedures documented
- [ ] Rollback procedures documented
- [ ] Incident response plan created
- [ ] Team trained on deployment process
- [ ] Emergency contacts listed

#### Monitoring Setup
- [ ] Application performance monitoring (APM) enabled
- [ ] Uptime monitoring configured
- [ ] Custom metrics/dashboards created
- [ ] Alerting rules configured
- [ ] Incident tracking system set up

#### Backup & Recovery
- [ ] Database backups automated
- [ ] Backup retention policy defined
- [ ] Restore procedures tested
- [ ] Disaster recovery plan documented
- [ ] RTO/RPO targets defined

### 11.5 Launch Day Checklist

**6 Hours Before Launch**
- [ ] Final staging environment test
- [ ] Team on standby
- [ ] Communication channels open
- [ ] Monitoring dashboards ready

**2 Hours Before Launch**
- [ ] Production access verified
- [ ] DNS ready to switch
- [ ] Last-minute code review
- [ ] Deployment commands prepared

**30 Minutes Before Launch**
- [ ] Stop non-critical deployments
- [ ] Brief team on status
- [ ] Confirm monitoring is active
- [ ] Verify communication channels

**Launch**
- [ ] Deploy to production
- [ ] Monitor error rates and performance
- [ ] Verify core functionality
- [ ] Check user-facing features
- [ ] Monitor logs for issues

**Post-Launch (First Hour)**
- [ ] Active monitoring of metrics
- [ ] Quick response to any issues
- [ ] Gradual traffic increase if using rolling releases
- [ ] Communication to stakeholders

**Post-Launch (First Day)**
- [ ] Monitor all key metrics
- [ ] Respond to user feedback
- [ ] Document any issues
- [ ] Celebrate successful launch!

### 11.6 Post-Deployment Monitoring

**Critical Metrics to Watch**
- Error rate (should be < 0.1%)
- API response time (p95 < 1s)
- Core Web Vitals scores
- Deployment stability
- User session duration
- Conversion rates (if applicable)

**Alerts to Set Up**
- Error rate > 1%
- API response time > 2s
- Function timeout rate > 5%
- Database connection errors
- SSL certificate expiration warning (30 days before)

**Daily Review**
- Check deployment logs for warnings
- Review error tracking for patterns
- Monitor performance metrics
- Check for security alerts

---

## Quick Reference: Common Commands

### Vercel CLI Commands

```bash
# Login to Vercel
vercel login

# Deploy to preview environment
vercel

# Deploy to production
vercel --prod

# Pull environment variables
vercel env pull

# View project info
vercel info

# Set environment variable
vercel env add VARIABLE_NAME

# Check project status
vercel status

# View deployments
vercel list

# Rollback to previous deployment
vercel rollback
```

### Configuration Files Reference

**vercel.json Structure**
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "devCommand": "npm run dev",
  "framework": "next",
  "regions": ["iad1", "sfo1"],
  "env": {
    "EXAMPLE_VAR": "@example_var"
  },
  "functions": {
    "api/**/*": {
      "maxDuration": 60,
      "memory": 3008
    }
  },
  "redirects": [
    {
      "source": "/old/:path*",
      "destination": "/new/:path*"
    }
  ],
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://backend.example.com/:path*"
    }
  ],
  "headers": [
    {
      "source": "/:path*",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        }
      ]
    }
  ]
}
```

---

## Resources & Additional Reading

- **Official Documentation**: https://vercel.com/docs
- **Production Checklist**: https://vercel.com/docs/production-checklist
- **Environment Variables**: https://vercel.com/docs/environment-variables
- **Deployment Guide**: https://vercel.com/guides
- **API Reference**: https://vercel.com/docs/rest-api
- **Community Forum**: https://community.vercel.com
- **GitHub Discussions**: https://github.com/vercel/vercel/discussions

---

## Conclusion

Deploying a web application to Vercel with a separate Render backend requires careful attention to:

1. **Environment configuration** - Ensure all variables are properly set and scoped
2. **CORS handling** - Configure headers correctly to avoid cross-origin issues
3. **API integration** - Use rewrites or API routes to connect frontend and backend
4. **Security** - Enable WAF, configure headers, and protect sensitive data
5. **Monitoring** - Set up analytics, error tracking, and performance monitoring
6. **Testing** - Use preview deployments extensively before production
7. **Documentation** - Maintain clear procedures for deployment and incident response

Follow this guide and your production deployment will be stable, secure, and performant!

---

**Document Version**: 1.0
**Last Updated**: November 2024
**Maintained By**: Development Team
