# ARC PDF Tool - Complete Deployment Guide
## Railway MySQL + Render Backend + Vercel Frontend

**Prepared for:** CEO
**Date:** October 21, 2025
**Estimated Time:** 60-90 minutes
**Monthly Cost:** $6-15 (Hobby tier) | $30-50 (Production tier)

---

## Executive Summary

This guide provides step-by-step instructions for deploying the ARC PDF Tool using modern cloud platforms:

- **Railway** - MySQL database hosting ($5/month base + usage)
- **Render** - Flask Python backend API ($7/month for always-on)
- **Vercel** - Next.js React frontend (Free tier)

**Why This Stack?**
- ✅ **Cost-Effective**: Starting at ~$12/month for production-ready deployment
- ✅ **Simple Setup**: No DevOps expertise required
- ✅ **Auto-Scaling**: Handles traffic spikes automatically
- ✅ **Zero Downtime**: Automatic deployments with health checks
- ✅ **Modern**: Uses latest cloud-native technologies

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Part 1: Railway MySQL Database](#3-part-1-railway-mysql-database)
4. [Part 2: Render Backend Deployment](#4-part-2-render-backend-deployment)
5. [Part 3: Vercel Frontend Deployment](#5-part-3-vercel-frontend-deployment)
6. [Part 4: Integration & Testing](#6-part-4-integration--testing)
7. [Monitoring & Maintenance](#7-monitoring--maintenance)
8. [Cost Breakdown](#8-cost-breakdown)
9. [Troubleshooting Guide](#9-troubleshooting-guide)
10. [Next Steps](#10-next-steps)

---

## 1. Architecture Overview

### System Architecture

```
┌──────────────────────────────────────────┐
│          Users / Clients                  │
│        (Web Browsers)                     │
└─────────────────┬────────────────────────┘
                  │ HTTPS
                  ↓
┌──────────────────────────────────────────┐
│     Vercel Frontend (Next.js/React)      │
│  - User Interface                        │
│  - Static Assets                         │
│  - Client-Side Logic                     │
│  - Global CDN                            │
└─────────────────┬────────────────────────┘
                  │ REST API
                  ↓
┌──────────────────────────────────────────┐
│      Render Backend (Flask/Python)       │
│  - API Endpoints                         │
│  - PDF Parsing (Tesseract, Camelot)     │
│  - Business Logic                        │
│  - File Upload Management                │
└─────────────────┬────────────────────────┘
                  │ MySQL Connection
                  ↓
┌──────────────────────────────────────────┐
│        Railway MySQL Database            │
│  - Price Books Storage                   │
│  - Products Data                         │
│  - Automatic Backups                     │
│  - Connection Pooling                    │
└──────────────────────────────────────────┘
```

### Data Flow

1. **User uploads PDF** → Frontend (Vercel)
2. **Frontend sends file** → Backend API (Render)
3. **Backend parses PDF** → Extracts data using Tesseract/Camelot
4. **Backend stores data** → MySQL Database (Railway)
5. **Backend returns results** → Frontend displays to user

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14, React 18, TailwindCSS | Modern responsive UI |
| **Backend** | Flask 3.1, Python 3.11 | RESTful API server |
| **Database** | MySQL 8.0 | Relational data storage |
| **PDF Processing** | PyPDF, Camelot, Tesseract OCR | Parse manufacturer PDFs |
| **Deployment** | Railway, Render, Vercel | Cloud hosting platforms |

**📸 SCREENSHOT PLACEHOLDER: Architecture diagram with all three platforms**

---

## 2. Prerequisites

### Required Accounts (Free Sign-up)

Before starting, create accounts on these platforms:

#### 1. GitHub Account
- **URL**: https://github.com/signup
- **Purpose**: Code repository and deployment source
- **Cost**: Free
- **Time**: 5 minutes

**Action Items:**
- ✅ Sign up for GitHub account
- ✅ Verify email address
- ✅ Push your ARC PDF Tool code to GitHub repository

**📸 SCREENSHOT PLACEHOLDER: GitHub repository page**

#### 2. Railway Account
- **URL**: https://railway.app/
- **Purpose**: MySQL database hosting
- **Trial**: $5 credit (30 days)
- **Cost**: $5/month base + compute usage
- **Time**: 3 minutes

**Action Items:**
- ✅ Sign up with GitHub account (recommended)
- ✅ Receive $5 trial credit
- ✅ Add payment method (required after trial)

**📸 SCREENSHOT PLACEHOLDER: Railway signup page**

#### 3. Render Account
- **URL**: https://render.com/
- **Purpose**: Flask backend hosting
- **Trial**: Free tier available (with limitations)
- **Cost**: $7/month for Starter plan (recommended)
- **Time**: 3 minutes

**Action Items:**
- ✅ Sign up with GitHub account
- ✅ Connect GitHub repository
- ✅ Optional: Add payment method for paid plans

**📸 SCREENSHOT PLACEHOLDER: Render dashboard**

#### 4. Vercel Account
- **URL**: https://vercel.com/signup
- **Purpose**: Next.js frontend hosting
- **Trial**: Hobby plan is free forever
- **Cost**: $0/month (Hobby) or $20/month (Pro)
- **Time**: 2 minutes

**Action Items:**
- ✅ Sign up with GitHub account
- ✅ Connect GitHub repository
- ✅ No payment method needed for Hobby plan

**📸 SCREENSHOT PLACEHOLDER: Vercel signup page**

### Local Development Requirements

Ensure your local machine has:

- ✅ **Git** installed (for repository management)
- ✅ **Code editor** (VS Code recommended)
- ✅ **Command line** access (Terminal/PowerShell/Git Bash)
- ✅ **GitHub repository** with your project code

### Project Files Checklist

Verify these files exist in your repository:

```
arc_pdf_tool/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── render.yaml              # Render configuration
├── render-build.sh          # Build script
├── database/
│   └── models.py            # Database models
├── frontend/
│   ├── package.json         # Frontend dependencies
│   ├── next.config.js       # Next.js configuration
│   └── src/                 # React components
└── docs/
    └── DEPLOYMENT.md        # This guide
```

**📸 SCREENSHOT PLACEHOLDER: File structure in VS Code**

---

## 3. Part 1: Railway MySQL Database

### Why Railway for MySQL?

**Advantages:**
- ✅ **Fast Setup**: Deploy MySQL in 15 seconds
- ✅ **Affordable**: ~$1-5/month for small databases
- ✅ **Automatic Backups**: Daily snapshots included
- ✅ **Public Access**: Easy external connections
- ✅ **Usage-Based Pricing**: Pay only for what you use
- ✅ **No Configuration**: Production-ready out of the box

**Comparison with Alternatives:**

| Feature | Railway | PlanetScale | AWS RDS |
|---------|---------|-------------|---------|
| **Setup Time** | 15 seconds | 2 minutes | 15 minutes |
| **Starting Price** | $5/month base | $39/month | $15/month |
| **Free Tier** | $5 credit (trial) | None | 12 months |
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Scalability** | Good | Excellent | Excellent |

### Step 1: Create Railway Project

1. Go to **https://railway.app/**
2. Click **"Login"** and sign in with GitHub
3. On dashboard, click **"New Project"**
4. Select **"Provision MySQL"**

**📸 SCREENSHOT PLACEHOLDER: Railway new project page with MySQL option**

### Step 2: Configure MySQL Database

Railway will automatically create a MySQL instance. You'll see:

**Database Information:**
- **Name**: `railway` (default)
- **Region**: `us-west1` (or closest to you)
- **Status**: `Active`
- **MySQL Version**: `8.0`

**No configuration needed** - Railway sets up:
- ✅ Root password (auto-generated)
- ✅ Public hostname
- ✅ Port assignment
- ✅ Automatic backups
- ✅ SSL encryption

**📸 SCREENSHOT PLACEHOLDER: Railway MySQL service deployed**

### Step 3: Get Database Credentials

1. Click on your **MySQL service** in Railway dashboard
2. Go to **"Variables"** tab
3. You'll see these automatically generated variables:

```
MYSQL_URL = mysql://root:PASSWORD@HOST:PORT/railway
MYSQLHOST = containers-us-west-xxx.railway.app
MYSQLPORT = 6379
MYSQLUSER = root
MYSQLPASSWORD = [auto-generated-password]
MYSQLDATABASE = railway
```

**IMPORTANT:** Copy these credentials - you'll need them for Render deployment.

**📸 SCREENSHOT PLACEHOLDER: Railway Variables tab showing credentials**

### Step 4: Create Database Tables

#### Option A: Using Railway's MySQL Client

1. In Railway dashboard, click your MySQL service
2. Click **"Data"** tab
3. Click **"Query"** button
4. Run this SQL:

```sql
-- Create price_books table
CREATE TABLE price_books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer VARCHAR(100) NOT NULL,
    edition VARCHAR(100),
    effective_date DATE,
    file_path VARCHAR(500),
    file_size INT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_products INT DEFAULT 0,
    parsing_confidence DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_manufacturer (manufacturer),
    INDEX idx_effective_date (effective_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create products table
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    price_book_id INT NOT NULL,
    sku VARCHAR(255) NOT NULL,
    description TEXT,
    list_price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    category VARCHAR(100),
    finish_code VARCHAR(50),
    page_number INT,
    confidence_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    INDEX idx_price_book (price_book_id),
    INDEX idx_sku (sku),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create diff_results table (for price comparisons)
CREATE TABLE diff_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    old_price_book_id INT NOT NULL,
    new_price_book_id INT NOT NULL,
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_changes INT DEFAULT 0,
    new_products INT DEFAULT 0,
    removed_products INT DEFAULT 0,
    price_increases INT DEFAULT 0,
    price_decreases INT DEFAULT 0,
    diff_data JSON,
    FOREIGN KEY (old_price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    FOREIGN KEY (new_price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    INDEX idx_old_book (old_price_book_id),
    INDEX idx_new_book (new_price_book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Verify tables were created
SHOW TABLES;

-- Check table structure
DESCRIBE price_books;
DESCRIBE products;
DESCRIBE diff_results;
```

5. Click **"Run Query"**
6. Verify output shows: `3 rows affected` for SHOW TABLES

**📸 SCREENSHOT PLACEHOLDER: Railway Query interface with SQL**

#### Option B: Using MySQL Workbench (Advanced)

If you prefer a GUI tool:

1. Download **MySQL Workbench**: https://dev.mysql.com/downloads/workbench/
2. Create new connection with Railway credentials
3. Import the SQL script above
4. Execute queries

**📸 SCREENSHOT PLACEHOLDER: MySQL Workbench connection**

### Step 5: Enable Public Networking

Railway MySQL is accessible externally by default, but verify:

1. In MySQL service, go to **"Settings"** tab
2. Check **"Public Networking"** section
3. Ensure it shows **"Enabled"**
4. Note the **Public Domain**: `containers-us-west-xxx.railway.app`

**Important:** This allows Render backend to connect to your database.

**📸 SCREENSHOT PLACEHOLDER: Railway public networking settings**

### Step 6: Monitor Database Usage

Railway shows real-time metrics:

1. Click **"Metrics"** tab in MySQL service
2. View:
   - CPU usage
   - Memory usage
   - Network I/O
   - Estimated monthly cost

**Expected initial usage:**
- CPU: <5%
- Memory: ~50-100 MB
- Monthly cost: ~$1-2

**📸 SCREENSHOT PLACEHOLDER: Railway metrics dashboard**

### Railway MySQL Setup Complete ✅

**Summary of what you have:**
- ✅ MySQL 8.0 database running
- ✅ Three tables created (price_books, products, diff_results)
- ✅ Public access enabled
- ✅ Connection credentials saved
- ✅ Automatic daily backups

**Next:** Deploy Flask backend on Render

---

## 4. Part 2: Render Backend Deployment

### Why Render for Backend?

**Advantages:**
- ✅ **Python Native**: Excellent Flask support
- ✅ **Auto-Deploy**: GitHub integration
- ✅ **Always On**: Starter plan ($7/month) never sleeps
- ✅ **SSL Included**: HTTPS automatically configured
- ✅ **Easy Scaling**: Upgrade plan with one click
- ✅ **Health Checks**: Automatic monitoring and restarts

**Free vs Paid:**

| Feature | Free Tier | Starter ($7/mo) |
|---------|-----------|-----------------|
| **Uptime** | Sleeps after 15min idle | Always on |
| **Build Time** | Standard | Faster |
| **RAM** | 512 MB | 512 MB |
| **CPU** | Shared | Shared |
| **SSL** | ✅ Yes | ✅ Yes |
| **Custom Domain** | ✅ Yes | ✅ Yes |

**Recommendation:** Use **Starter plan** for production to avoid cold starts.

### Step 7: Prepare Backend Code

Before deploying, verify your repository has these files:

#### File 1: `requirements.txt`

Your project should already have this. Verify it includes:

```txt
# Core Framework
Flask==3.1.2
flask-cors==6.0.1
gunicorn==23.0.0

# Database
mysqlclient==2.2.0
SQLAlchemy==2.0.43
alembic==1.16.5

# PDF Processing
PyPDF==3.17.4
pdf2image==1.17.0
pdfplumber==0.11.7
camelot-py==1.0.9
pytesseract==0.3.13

# Data Processing
pandas==2.3.2
openpyxl==3.1.5
numpy==2.3.3

# Utilities
python-dotenv==1.1.1
requests==2.32.5
```

**📸 SCREENSHOT PLACEHOLDER: requirements.txt in editor**

#### File 2: `render-build.sh`

Create this file if it doesn't exist:

```bash
#!/bin/bash
# Render build script for ARC PDF Tool

set -o errexit  # Exit on error

echo "📦 Installing system dependencies..."

# Update package list
apt-get update

# Install Tesseract OCR (for PDF text extraction)
apt-get install -y tesseract-ocr

# Install Poppler utils (for PDF processing)
apt-get install -y poppler-utils

# Install MySQL client development libraries
apt-get install -y default-libmysqlclient-dev build-essential

# Install Ghostscript (for PDF manipulation)
apt-get install -y ghostscript

echo "🐍 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️  Running database migrations..."
# Uncomment if using Alembic migrations
# alembic upgrade head

echo "✅ Build complete!"
```

**Make it executable:**
```bash
chmod +x render-build.sh
```

**📸 SCREENSHOT PLACEHOLDER: render-build.sh file**

#### File 3: `render.yaml` (Optional)

This file configures Render via Infrastructure as Code. Your project should have it:

```yaml
services:
  - type: web
    name: arc-pdf-api
    env: python
    buildCommand: chmod +x render-build.sh && ./render-build.sh
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: FLASK_ENV
        value: production
      - key: SECRET_KEY
        generateValue: true
      - key: MYSQL_HOST
        sync: false
      - key: MYSQL_PORT
        sync: false
      - key: MYSQL_USER
        sync: false
      - key: MYSQL_PASSWORD
        sync: false
      - key: MYSQL_DATABASE
        sync: false
      - key: TESSERACT_CMD
        value: /usr/bin/tesseract
      - key: CORS_ORIGINS
        sync: false
```

**📸 SCREENSHOT PLACEHOLDER: render.yaml file**

#### File 4: Verify `app.py` has MySQL Support

Ensure your `app.py` uses MySQL connection:

```python
import os
import MySQLdb

# Database configuration
db_config = {
    'host': os.environ.get('MYSQL_HOST'),
    'user': os.environ.get('MYSQL_USER'),
    'password': os.environ.get('MYSQL_PASSWORD'),
    'database': os.environ.get('MYSQL_DATABASE'),
    'port': int(os.environ.get('MYSQL_PORT', 3306))
}

# Or if using SQLAlchemy:
# DATABASE_URL = f"mysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
```

**📸 SCREENSHOT PLACEHOLDER: app.py database configuration**

### Step 8: Push Code to GitHub

Ensure all changes are committed and pushed:

```bash
# Add all files
git add .

# Commit with message
git commit -m "Configure for Render deployment with Railway MySQL"

# Push to GitHub
git push origin main
```

**Verify:**
- Go to your GitHub repository
- Check that `render-build.sh`, `render.yaml`, and `requirements.txt` are visible
- Ensure latest commit is pushed

**📸 SCREENSHOT PLACEHOLDER: GitHub repository showing files**

### Step 9: Create Render Web Service

1. Go to **https://render.com/dashboard**
2. Click **"New +"** button (top right)
3. Select **"Web Service"**
4. Click **"Connect a repository"**

**📸 SCREENSHOT PLACEHOLDER: Render New Web Service button**

### Step 10: Connect GitHub Repository

1. Click **"Configure account"** to authorize Render
2. In GitHub popup, select **"All repositories"** or choose specific repo
3. Click **"Install"**
4. Back in Render, find your repository: `arc_pdf_tool`
5. Click **"Connect"**

**📸 SCREENSHOT PLACEHOLDER: Render GitHub connection**

### Step 11: Configure Web Service Settings

Fill in the deployment configuration:

#### Basic Settings

- **Name**: `arc-pdf-api` (must be unique across Render)
- **Region**: `Ohio (US East)` (or closest to users)
- **Branch**: `main` (or `alex-feature` if that's your main branch)
- **Runtime**: `Python 3`

**📸 SCREENSHOT PLACEHOLDER: Render basic settings**

#### Build Settings

- **Build Command**:
  ```bash
  chmod +x render-build.sh && ./render-build.sh
  ```

- **Start Command**:
  ```bash
  gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```

**Explanation:**
- `--workers 2`: Run 2 worker processes (handles concurrent requests)
- `--timeout 120`: Allow 2 minutes for PDF processing
- `--bind 0.0.0.0:$PORT`: Bind to Render's assigned port

**📸 SCREENSHOT PLACEHOLDER: Render build settings**

#### Instance Type

- **Free**: For testing only (sleeps after 15 min idle)
- **Starter**: **Recommended** - $7/month, always on, faster
- **Standard**: $25/month, more resources

**Select:** **Starter** ($7/month)

**📸 SCREENSHOT PLACEHOLDER: Render instance type selection**

### Step 12: Add Environment Variables

Click **"Advanced"** to expand environment variables section.

Add these variables from your Railway MySQL:

| Key | Value | Example |
|-----|-------|---------|
| `PYTHON_VERSION` | `3.11.0` | Fixed value |
| `FLASK_ENV` | `production` | Fixed value |
| `SECRET_KEY` | [Click "Generate"] | Auto-generated |
| `MYSQL_HOST` | [From Railway] | `containers-us-west-xxx.railway.app` |
| `MYSQL_PORT` | [From Railway] | `6379` or `3306` |
| `MYSQL_USER` | [From Railway] | `root` |
| `MYSQL_PASSWORD` | [From Railway] | Long generated password |
| `MYSQL_DATABASE` | [From Railway] | `railway` |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Fixed value |
| `CORS_ORIGINS` | `http://localhost:3000` | Will update later |

**How to get Railway values:**
1. Open Railway dashboard
2. Click on MySQL service
3. Go to "Variables" tab
4. Copy each value

**📸 SCREENSHOT PLACEHOLDER: Render environment variables filled in**

### Step 13: Deploy Backend

1. Review all settings
2. Click **"Create Web Service"**
3. Render starts building your application

**Build Process (5-10 minutes):**
1. ⏳ Checking out code from GitHub
2. ⏳ Installing system dependencies (Tesseract, Poppler, MySQL)
3. ⏳ Installing Python packages (~100 packages)
4. ⏳ Starting Gunicorn server
5. ✅ Service is live!

**Watch the logs in real-time** to see progress.

**📸 SCREENSHOT PLACEHOLDER: Render build logs showing success**

### Step 14: Get Backend URL

Once deployed successfully, Render provides a URL:

```
https://arc-pdf-api.onrender.com
```

**Copy this URL** - you'll need it for:
- Vercel frontend configuration
- Testing API endpoints

**📸 SCREENSHOT PLACEHOLDER: Render service URL**

### Step 15: Verify Backend Health

Test that the backend is running:

#### Test 1: Health Check Endpoint

Open browser and go to:
```
https://arc-pdf-api.onrender.com/healthz
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "arc_pdf_tool",
  "timestamp": "2025-10-21T12:00:00Z",
  "checks": {
    "database": true,
    "filesystem": true
  }
}
```

**📸 SCREENSHOT PLACEHOLDER: Browser showing health check response**

#### Test 2: API Endpoints

Test the API is accessible:
```
https://arc-pdf-api.onrender.com/api/price-books
```

**Expected Response:**
```json
[]
```
(Empty array because no data yet)

**📸 SCREENSHOT PLACEHOLDER: API endpoint test**

#### Test 3: Database Connection

Check Render logs for database connection:

1. In Render dashboard, click your service
2. Click **"Logs"** tab
3. Look for:
   ```
   Database connection: SUCCESS
   MySQL Version: 8.0.x
   ```

**📸 SCREENSHOT PLACEHOLDER: Render logs showing database connection**

### Render Backend Setup Complete ✅

**Summary:**
- ✅ Flask backend deployed on Render
- ✅ Connected to Railway MySQL database
- ✅ Health check returning 200 OK
- ✅ API endpoints responding
- ✅ Gunicorn serving on port 10000
- ✅ SSL certificate active (HTTPS)

**Next:** Deploy frontend on Vercel

---

## 5. Part 3: Vercel Frontend Deployment

### Why Vercel for Frontend?

**Advantages:**
- ✅ **Built for Next.js**: Created by Next.js team
- ✅ **Global CDN**: Lightning-fast worldwide
- ✅ **Zero Config**: Auto-detects Next.js
- ✅ **Free HTTPS**: SSL certificates included
- ✅ **Preview Deployments**: Every PR gets preview URL
- ✅ **Instant Rollbacks**: One-click revert
- ✅ **Free Tier**: Generous limits for small projects

**Free vs Pro:**

| Feature | Hobby (Free) | Pro ($20/mo) |
|---------|--------------|--------------|
| **Bandwidth** | 100 GB/month | 1 TB/month |
| **Builds** | 6000 min/month | 24000 min/month |
| **Custom Domains** | Unlimited | Unlimited |
| **Team Members** | 1 | Unlimited |
| **Analytics** | Basic | Advanced |

**Recommendation:** Start with **Hobby (Free)** - it's plenty for most projects.

### Step 16: Prepare Frontend Environment

Your frontend code should be in `frontend/` directory with:

```
frontend/
├── package.json          # Dependencies
├── next.config.js        # Next.js config
├── tsconfig.json         # TypeScript config
├── tailwind.config.js    # Tailwind CSS
├── public/               # Static assets
├── src/
│   ├── app/             # Next.js 14 App Router
│   ├── components/      # React components
│   └── lib/             # Utilities
└── .env.local           # Local environment variables
```

#### Update `.env.local` (Local Development)

```bash
# Backend API URL (local)
NEXT_PUBLIC_API_URL=http://localhost:5000

# For production, we'll set this in Vercel dashboard
```

**Important:** The `NEXT_PUBLIC_` prefix makes the variable available to client-side code.

**📸 SCREENSHOT PLACEHOLDER: Frontend directory structure**

### Step 17: Verify API Configuration

Check that your frontend API calls use the environment variable:

```typescript
// src/lib/api.ts or similar
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export const fetchPriceBooks = async () => {
  const response = await fetch(`${API_URL}/api/price-books`);
  return response.json();
};
```

**📸 SCREENSHOT PLACEHOLDER: API configuration code**

### Step 18: Push Frontend Code

Ensure frontend is committed:

```bash
# Navigate to frontend directory
cd frontend

# Add changes
git add .

# Commit
git commit -m "Configure for Vercel deployment"

# Push
git push origin main
```

### Step 19: Create Vercel Project

1. Go to **https://vercel.com/dashboard**
2. Click **"Add New..."** → **"Project"**
3. Click **"Import Git Repository"**
4. Find your repository: `arc_pdf_tool`
5. Click **"Import"**

**📸 SCREENSHOT PLACEHOLDER: Vercel import project page**

### Step 20: Configure Project Settings

Vercel auto-detects Next.js, but verify settings:

#### Framework Preset
- **Framework**: `Next.js` (should auto-detect)
- **Version**: `14.x` (or your version)

#### Root Directory
**⚠️ CRITICAL SETTING:**
- **Root Directory**: `frontend`

This tells Vercel your frontend code is in `frontend/` subdirectory.

**📸 SCREENSHOT PLACEHOLDER: Vercel root directory setting highlighted**

#### Build & Development Settings

**Auto-detected (leave as default):**
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`
- **Development Command**: `npm run dev`

**📸 SCREENSHOT PLACEHOLDER: Vercel build settings**

### Step 21: Add Environment Variables

Scroll to **"Environment Variables"** section.

Add this variable:

| Key | Value | Environments |
|-----|-------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://arc-pdf-api.onrender.com` | ✅ Production ✅ Preview ✅ Development |

**Use your Render backend URL from Step 14.**

**Important:**
- Select **all three environments** (Production, Preview, Development)
- The `NEXT_PUBLIC_` prefix is required for client-side access
- No trailing slash in the URL

**📸 SCREENSHOT PLACEHOLDER: Vercel environment variable configuration**

### Step 22: Deploy Frontend

1. Review all settings
2. Click **"Deploy"**
3. Vercel builds your Next.js application

**Build Process (2-3 minutes):**
1. ⏳ Cloning repository
2. ⏳ Running `npm install`
3. ⏳ Running `npm run build`
4. ⏳ Uploading to CDN
5. ✅ Deployment successful!

**Watch the build logs** for any errors.

**📸 SCREENSHOT PLACEHOLDER: Vercel build logs**

### Step 23: Get Frontend URL

After successful deployment, Vercel provides URLs:

**Production URL:**
```
https://arc-pdf-tool.vercel.app
```

**Deployment-specific URL:**
```
https://arc-pdf-tool-abc123xyz.vercel.app
```

**Both URLs work**, but use the production URL for official use.

**Copy the production URL** for the next step.

**📸 SCREENSHOT PLACEHOLDER: Vercel deployment success page with URLs**

### Step 24: Update Backend CORS

The backend needs to allow requests from your Vercel domain.

1. Go back to **Render dashboard**
2. Open your **arc-pdf-api** service
3. Go to **"Environment"** tab
4. Find `CORS_ORIGINS` variable
5. Click **"Edit"**
6. Update value to:
   ```
   http://localhost:3000,https://arc-pdf-tool.vercel.app,https://*.vercel.app
   ```
7. Click **"Save Changes"**

**Render automatically redeploys** (2-3 minutes).

**Explanation:**
- `http://localhost:3000` - Local development
- `https://arc-pdf-tool.vercel.app` - Your production URL
- `https://*.vercel.app` - All Vercel preview deployments

**📸 SCREENSHOT PLACEHOLDER: Render CORS environment variable update**

### Step 25: Verify Frontend

Open your browser and test:

#### Test 1: Homepage Loads

Visit: `https://arc-pdf-tool.vercel.app`

**Expected:** Dashboard page loads without errors

**📸 SCREENSHOT PLACEHOLDER: Frontend homepage**

#### Test 2: No Console Errors

1. Press **F12** to open DevTools
2. Go to **"Console"** tab
3. Look for errors (should be clean)

**Expected:** No CORS errors, no 404 errors

**📸 SCREENSHOT PLACEHOLDER: Browser console showing no errors**

#### Test 3: API Connection

1. In DevTools, go to **"Network"** tab
2. Refresh the page
3. Look for API requests to `arc-pdf-api.onrender.com`
4. Check status codes (should be 200 OK)

**Expected:** API calls succeed

**📸 SCREENSHOT PLACEHOLDER: Network tab showing successful API calls**

### Vercel Frontend Setup Complete ✅

**Summary:**
- ✅ Next.js frontend deployed on Vercel
- ✅ Environment variable configured
- ✅ Connected to Render backend
- ✅ CORS configured properly
- ✅ Global CDN active
- ✅ HTTPS enabled

**Next:** Integration testing and verification

---

## 6. Part 4: Integration & Testing

Now that all three services are deployed, let's verify the complete integration.

### Step 26: End-to-End Testing

#### Test 1: Upload PDF File

**Purpose:** Verify complete workflow from frontend → backend → database

1. Go to your frontend: `https://arc-pdf-tool.vercel.app`
2. Click **"Upload"** in navigation menu
3. Select manufacturer:
   - **Hager** or **SELECT Hinges**
4. Click **"Choose File"**
5. Select a test PDF from your computer
6. Click **"Upload & Parse"**

**Expected behavior:**
- ⏳ Progress indicator shows
- ⏳ Backend processes PDF (30-60 seconds)
- ✅ Redirect to preview page
- ✅ Products displayed in table

**If it works:** Congratulations! Your entire stack is functioning.

**If it fails:** See troubleshooting section below.

**📸 SCREENSHOT PLACEHOLDER: Upload page with file selected**

#### Test 2: Verify Database Storage

Check that data was saved to Railway MySQL:

1. Go to **Railway dashboard**
2. Click on your MySQL service
3. Go to **"Data"** tab
4. Run query:
   ```sql
   SELECT COUNT(*) as total_books FROM price_books;
   SELECT COUNT(*) as total_products FROM products;
   ```

**Expected:**
- `total_books`: 1 (or more if you uploaded multiple)
- `total_products`: Number of products parsed from PDF

**📸 SCREENSHOT PLACEHOLDER: Railway data query results**

#### Test 3: Export Functionality

1. From preview page, click **"Export"** dropdown
2. Select **"Excel"** (or CSV/JSON)
3. Click **"Download"**

**Expected:** File downloads successfully with parsed data

**📸 SCREENSHOT PLACEHOLDER: Export menu**

#### Test 4: Compare Price Books

**Prerequisites:** Upload two different PDF editions first

1. Go to **"Compare"** page
2. Select **Old Edition**: First uploaded price book
3. Select **New Edition**: Second uploaded price book
4. Click **"Generate Comparison"**

**Expected:**
- ⏳ Processing indicator
- ✅ Diff results showing:
  - Price changes (increases/decreases)
  - New products
  - Removed products
  - Statistics

**📸 SCREENSHOT PLACEHOLDER: Compare page with results**

#### Test 5: Mobile Responsiveness

1. Open frontend on mobile device (or use DevTools mobile view)
2. Test navigation
3. Try uploading (if mobile allows)

**Expected:** UI adapts to mobile screen

**📸 SCREENSHOT PLACEHOLDER: Mobile view**

### Step 27: Performance Testing

#### Check Response Times

Use browser DevTools Network tab:

1. Refresh frontend page
2. Check **"Network"** tab
3. Look at timing for API calls

**Good performance:**
- Frontend load: < 3 seconds
- API calls: < 500ms
- PDF upload: 30-60 seconds (depending on size)

**📸 SCREENSHOT PLACEHOLDER: Network timing**

#### Check Backend Logs

Monitor Render logs for issues:

1. Render dashboard → arc-pdf-api
2. Click **"Logs"** tab
3. Look for:
   - ✅ `200 OK` responses
   - ✅ Database queries succeeding
   - ❌ Any `ERROR` or `500` messages

**📸 SCREENSHOT PLACEHOLDER: Render logs showing successful requests**

### Step 28: Security Verification

#### SSL/HTTPS Check

Verify all services use HTTPS:

- ✅ Frontend: `https://arc-pdf-tool.vercel.app` (Vercel auto-SSL)
- ✅ Backend: `https://arc-pdf-api.onrender.com` (Render auto-SSL)
- ✅ Database: Railway uses encrypted connections

**Test:** Click padlock icon in browser address bar

**📸 SCREENSHOT PLACEHOLDER: Browser showing secure connection**

#### Environment Variables Check

Ensure secrets are not exposed:

1. View frontend source (right-click → View Page Source)
2. Search for:
   - ❌ `MYSQL_PASSWORD` (should NOT appear)
   - ❌ `SECRET_KEY` (should NOT appear)
   - ✅ `NEXT_PUBLIC_API_URL` (OK to appear)

**Only `NEXT_PUBLIC_*` variables should be visible in frontend.**

**📸 SCREENSHOT PLACEHOLDER: Frontend source showing only public vars**

### Integration Testing Complete ✅

**All systems verified:**
- ✅ Railway MySQL: Storing and retrieving data
- ✅ Render Backend: Processing PDFs, serving API
- ✅ Vercel Frontend: Displaying UI, calling backend
- ✅ HTTPS: All connections encrypted
- ✅ CORS: Cross-origin requests allowed
- ✅ Performance: Response times acceptable

---

## 7. Monitoring & Maintenance

### Railway MySQL Monitoring

#### View Database Metrics

1. Railway dashboard → MySQL service
2. Click **"Metrics"** tab

**Monitor:**
- **CPU Usage**: Should stay < 20% normally
- **Memory**: Typical: 50-200 MB
- **Disk Usage**: Grows with data
- **Network I/O**: Spikes during uploads

**📸 SCREENSHOT PLACEHOLDER: Railway metrics**

#### Check Database Health

Run diagnostic queries:

```sql
-- Check table sizes
SELECT
  TABLE_NAME,
  TABLE_ROWS,
  ROUND(DATA_LENGTH / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'railway'
ORDER BY DATA_LENGTH DESC;

-- Check for slow queries (if enabled)
SELECT * FROM mysql.slow_log LIMIT 10;
```

**📸 SCREENSHOT PLACEHOLDER: Database health check**

#### Set Up Alerts (Optional)

Railway doesn't have built-in alerts, but you can:

1. Use external monitoring (e.g., UptimeRobot)
2. Monitor usage from Metrics dashboard weekly
3. Set calendar reminders to check

### Render Backend Monitoring

#### View Application Logs

1. Render dashboard → arc-pdf-api
2. Click **"Logs"** tab
3. Use filters:
   - **Info**: Regular operations
   - **Warning**: Potential issues
   - **Error**: Failed requests

**Common log patterns:**

**Good:**
```
INFO: 200 GET /api/price-books
INFO: Database query: 0.045s
INFO: PDF parsing complete: 150 products
```

**Needs attention:**
```
WARNING: Slow query: 2.3s
ERROR: Database connection failed
ERROR: 500 Internal Server Error
```

**📸 SCREENSHOT PLACEHOLDER: Render logs with filters**

#### Monitor Metrics

1. Click **"Metrics"** tab in Render service

**View:**
- **CPU Usage**: Normal: 20-40% during uploads
- **Memory Usage**: Normal: 200-400 MB
- **HTTP Requests**: Track request volume
- **Response Time**: Should stay < 500ms for API calls

**Set alerts for:**
- CPU > 80% sustained
- Memory > 90%
- High error rates

**📸 SCREENSHOT PLACEHOLDER: Render metrics dashboard**

#### Check Deployment History

1. Click **"Events"** tab
2. View all deployments and their status
3. Quickly rollback if needed:
   - Find previous deployment
   - Click **"Redeploy"**

**📸 SCREENSHOT PLACEHOLDER: Render deployment history**

### Vercel Frontend Monitoring

#### View Deployment Logs

1. Vercel dashboard → your project
2. Click **"Deployments"** tab
3. Click on any deployment
4. View **"Build Logs"** and **"Function Logs"**

**📸 SCREENSHOT PLACEHOLDER: Vercel deployment logs**

#### Monitor Performance

1. Click **"Analytics"** tab (if Pro plan)
2. View:
   - Page views
   - Geographic distribution
   - Load times
   - Core Web Vitals

**📸 SCREENSHOT PLACEHOLDER: Vercel analytics**

#### Check Bandwidth Usage

1. Go to **"Usage"** tab
2. Monitor:
   - **Bandwidth**: Free tier = 100 GB/month
   - **Build Minutes**: Free tier = 6000 min/month
   - **Serverless Function Executions**

**📸 SCREENSHOT PLACEHOLDER: Vercel usage dashboard**

### Proactive Monitoring Setup

#### Option 1: UptimeRobot (Free)

Monitor backend availability:

1. Sign up: https://uptimerobot.com
2. Add monitor:
   - **Type**: HTTP(s)
   - **URL**: `https://arc-pdf-api.onrender.com/healthz`
   - **Interval**: 5 minutes
   - **Alert Contacts**: Your email
3. Receive alerts if service goes down

**📸 SCREENSHOT PLACEHOLDER: UptimeRobot setup**

#### Option 2: Sentry Error Tracking (Optional)

Track application errors:

1. Sign up: https://sentry.io
2. Install in backend:
   ```bash
   pip install sentry-sdk[flask]
   ```
3. Initialize in `app.py`:
   ```python
   import sentry_sdk
   sentry_sdk.init(dsn="your-dsn")
   ```
4. Get email alerts for errors

**📸 SCREENSHOT PLACEHOLDER: Sentry dashboard**

### Maintenance Tasks

#### Weekly Tasks

- ✅ Check Railway MySQL usage and cost
- ✅ Review Render logs for errors
- ✅ Check Vercel deployment status
- ✅ Test critical workflows (upload, export)

#### Monthly Tasks

- ✅ Review Railway database size (optimize if needed)
- ✅ Check for security updates in dependencies
- ✅ Review costs across all platforms
- ✅ Backup important data (Railway auto-backups, but manual backup recommended)

#### Quarterly Tasks

- ✅ Performance optimization review
- ✅ Consider upgrading plans if usage increased
- ✅ Update documentation
- ✅ Review and optimize database indexes

### Backup Strategy

#### Railway MySQL Backups

**Automatic backups:**
- Railway performs daily backups (retained 7 days)
- Located in Railway dashboard → MySQL → Backups

**Manual backup:**
```bash
# Using mysqldump (install MySQL client first)
mysqldump -h [RAILWAY_HOST] -P [PORT] -u root -p railway > backup_$(date +%Y%m%d).sql
```

**Restore backup:**
```bash
mysql -h [RAILWAY_HOST] -P [PORT] -u root -p railway < backup_20251021.sql
```

**📸 SCREENSHOT PLACEHOLDER: Railway backups page**

#### Application Code Backups

- ✅ Code already backed up on GitHub
- ✅ Render and Vercel keep deployment history
- ✅ Can rollback to previous deployment anytime

---

## 8. Cost Breakdown

### Monthly Cost Summary

#### Hobby/Development Tier (Cost-Effective)

| Service | Plan | Cost | Notes |
|---------|------|------|-------|
| **Railway MySQL** | Hobby | ~$1-5/mo | Usage-based, depends on data volume |
| **Render Backend** | Starter | $7/mo | Always on, no cold starts |
| **Vercel Frontend** | Hobby | $0/mo | Free forever, generous limits |
| **Total** | | **~$8-12/mo** | **Best for small to medium projects** |

#### Production Tier (Recommended)

| Service | Plan | Cost | Notes |
|---------|------|------|-------|
| **Railway MySQL** | Pro | ~$10-20/mo | Higher limits, better performance |
| **Render Backend** | Standard | $25/mo | 2GB RAM, priority support |
| **Vercel Frontend** | Hobby | $0/mo | Still free (or Pro $20/mo for team) |
| **Total** | | **~$35-45/mo** | **Best for production with growth** |

#### Enterprise Tier (High Traffic)

| Service | Plan | Cost | Notes |
|---------|------|------|-------|
| **Railway MySQL** | Custom | $50+/mo | Dedicated resources |
| **Render Backend** | Pro Plus | $85/mo | 4GB RAM, autoscaling |
| **Vercel Frontend** | Pro | $20/mo | Team features, analytics |
| **Total** | | **~$155+/mo** | **Best for high-traffic apps** |

### Detailed Cost Breakdown

#### Railway MySQL Pricing

**Pricing Model:** $5/month base + usage

**Usage charges:**
- **CPU**: $0.000463/vCPU/minute
- **Memory**: $0.000231/GB/minute
- **Disk**: $0.25/GB/month
- **Network Egress**: $0.10/GB

**Example calculations:**

**Small database (< 1 GB, low traffic):**
```
Base: $5.00
CPU (10% avg): ~$0.67
Memory (100 MB avg): ~$0.33
Disk (500 MB): ~$0.13
Network (1 GB): ~$0.10
Total: ~$6.23/month
```

**Medium database (5 GB, moderate traffic):**
```
Base: $5.00
CPU (25% avg): ~$1.67
Memory (500 MB avg): ~$1.67
Disk (5 GB): ~$1.25
Network (10 GB): ~$1.00
Total: ~$10.59/month
```

**Monitor usage:** Railway dashboard → Metrics → Estimated cost

**📸 SCREENSHOT PLACEHOLDER: Railway cost estimate**

#### Render Backend Pricing

**Fixed pricing per tier:**

| Plan | Cost | RAM | CPU | Uptime |
|------|------|-----|-----|--------|
| **Free** | $0 | 512 MB | Shared | Sleeps after 15 min |
| **Starter** | $7/mo | 512 MB | Shared | Always on |
| **Standard** | $25/mo | 2 GB | 1 vCPU | Always on, faster |
| **Pro** | $85/mo | 4 GB | 2 vCPU | Autoscaling |
| **Pro Plus** | $250/mo | 8 GB | 4 vCPU | Highest performance |

**Recommendation by usage:**

- **Testing**: Free tier (accept cold starts)
- **Small business**: Starter ($7/mo)
- **Growing business**: Standard ($25/mo)
- **High traffic**: Pro ($85/mo)

**No hidden costs** - price is all-inclusive with:
- ✅ SSL certificates
- ✅ Automatic deployments
- ✅ 100 GB bandwidth/month
- ✅ Health checks
- ✅ Logging

**📸 SCREENSHOT PLACEHOLDER: Render pricing page**

#### Vercel Frontend Pricing

**Hobby (Free Forever):**
- ✅ **100 GB** bandwidth/month
- ✅ **6000 build minutes**/month
- ✅ **Unlimited** websites
- ✅ **Unlimited** team members (1 per project)
- ✅ **Free SSL** certificates
- ✅ **Free custom domains**

**Perfect for:** Most small to medium projects

**Pro ($20/month):**
- ✅ **1 TB** bandwidth/month
- ✅ **24000 build minutes**/month
- ✅ **Advanced analytics**
- ✅ **Team collaboration**
- ✅ **Password protection**
- ✅ **Priority support**

**Upgrade if:**
- Bandwidth exceeds 100 GB/month
- Need team collaboration
- Want advanced analytics

**📸 SCREENSHOT PLACEHOLDER: Vercel pricing comparison**

### Cost Optimization Tips

#### 1. Start Small, Scale Up

**Strategy:**
- Begin with Hobby tier (~$8-12/month)
- Monitor usage for 1-2 months
- Upgrade only when hitting limits

#### 2. Optimize Database Usage

**Reduce Railway costs:**
- ✅ Add database indexes for faster queries
- ✅ Clean up old/unused data periodically
- ✅ Use connection pooling (already configured)
- ✅ Compress large text fields

**Example savings:** 20-30% reduction in query time = lower CPU usage

#### 3. Use Free Tiers Wisely

**Services with generous free tiers:**
- ✅ Vercel: Free forever for frontend
- ✅ GitHub: Free for public repos
- ✅ Cloudflare: Free CDN (if needed)

#### 4. Monitor and Alert

**Set usage alerts:**
- Railway: Check weekly, set calendar reminder
- Render: Enable usage notifications
- Vercel: Monitor bandwidth in dashboard

**Catch overages early** before they become expensive.

#### 5. Optimize Build Times

**Reduce Render build minutes:**
- Cache dependencies properly
- Use build script optimizations
- Only rebuild when necessary (Render is smart about this)

### Annual Cost Comparison

**vs Traditional Hosting:**

| Option | Monthly | Annual | Notes |
|--------|---------|--------|-------|
| **Our Stack** | $8-12 | $96-144 | Fully managed, auto-scaling |
| **AWS EC2** | $15-30 | $180-360 | Requires DevOps, setup |
| **DigitalOcean** | $12-24 | $144-288 | Requires maintenance |
| **Heroku** | $25-50 | $300-600 | Similar to our stack |

**Savings:** 50-70% compared to traditional hosting

---

## 9. Troubleshooting Guide

### Common Issues & Solutions

#### Issue 1: Backend Returns 404 for API Calls

**Symptoms:**
- Frontend shows "Network Error"
- Browser console: `404 Not Found`
- All API calls fail

**Cause:**
- Routes not registered
- Incorrect API path
- App not starting properly

**Solution:**

1. **Check Render logs:**
   ```
   Render Dashboard → arc-pdf-api → Logs
   ```
   Look for startup errors

2. **Verify routes in `app.py`:**
   ```python
   # Ensure blueprint is registered
   from api_routes import api
   app.register_blueprint(api, url_prefix='/api')
   ```

3. **Test health endpoint:**
   ```
   https://arc-pdf-api.onrender.com/healthz
   ```
   Should return 200 OK

4. **Redeploy if needed:**
   ```bash
   git commit --allow-empty -m "Trigger redeploy"
   git push origin main
   ```

**📸 SCREENSHOT PLACEHOLDER: Render logs showing route errors**

---

#### Issue 2: CORS Errors in Browser

**Symptoms:**
```
Access to XMLHttpRequest at 'https://arc-pdf-api.onrender.com/api/price-books'
from origin 'https://arc-pdf-tool.vercel.app' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Cause:**
- Backend CORS_ORIGINS not configured
- Vercel URL not included in CORS
- CORS middleware not loaded

**Solution:**

1. **Update CORS_ORIGINS in Render:**
   ```
   Render Dashboard → Environment → CORS_ORIGINS
   ```
   Value:
   ```
   http://localhost:3000,https://arc-pdf-tool.vercel.app,https://*.vercel.app
   ```

2. **Verify `app.py` has CORS:**
   ```python
   from flask_cors import CORS

   CORS(app, origins=[
       r"http://localhost:\d+",
       r"https?://.*\.vercel\.app",
   ])
   ```

3. **Redeploy backend** after changes

4. **Clear browser cache:**
   - Press Ctrl+Shift+Delete
   - Clear cached images and files
   - Or use Incognito mode

**📸 SCREENSHOT PLACEHOLDER: CORS error in browser console**

---

#### Issue 3: Database Connection Failed

**Symptoms:**
- Backend logs: `Can't connect to MySQL server`
- Health check: `{"database": false}`
- 500 errors on API calls

**Cause:**
- Wrong Railway credentials
- Railway MySQL not running
- Network issue

**Solution:**

1. **Verify Railway MySQL is running:**
   ```
   Railway Dashboard → MySQL service → Status: Active
   ```

2. **Check environment variables in Render:**
   - `MYSQL_HOST` matches Railway
   - `MYSQL_PORT` is correct (usually 3306 or custom)
   - `MYSQL_USER` is `root`
   - `MYSQL_PASSWORD` matches Railway
   - `MYSQL_DATABASE` is `railway`

3. **Test connection from Render Shell:**
   ```
   Render Dashboard → Shell
   ```
   Run:
   ```bash
   mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD -e "SHOW DATABASES;"
   ```

4. **Check Railway public networking:**
   ```
   Railway → MySQL → Settings → Public Networking: Enabled
   ```

**📸 SCREENSHOT PLACEHOLDER: Railway MySQL credentials**

---

#### Issue 4: Frontend Environment Variable Not Working

**Symptoms:**
- API calls go to wrong URL or `undefined`
- Console error: `Cannot read property 'NEXT_PUBLIC_API_URL'`

**Cause:**
- Variable not set in Vercel
- Missing `NEXT_PUBLIC_` prefix
- Not deployed after adding variable

**Solution:**

1. **Check Vercel environment variables:**
   ```
   Vercel → Project → Settings → Environment Variables
   ```
   Ensure:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://arc-pdf-api.onrender.com`
   - Checked: ✅ Production ✅ Preview ✅ Development

2. **Redeploy frontend:**
   ```
   Vercel → Deployments → [Latest] → ... → Redeploy
   ```

3. **Verify in code:**
   ```typescript
   console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
   ```

**📸 SCREENSHOT PLACEHOLDER: Vercel environment variables**

---

#### Issue 5: PDF Upload Fails / Times Out

**Symptoms:**
- Upload spinner runs forever
- Backend returns 500 error
- Logs show Tesseract or memory errors

**Cause:**
- PDF too large
- Insufficient memory
- Missing system dependencies
- OCR processing taking too long

**Solution:**

1. **Check file size:**
   - Max recommended: 50 MB
   - If larger, compress PDF first

2. **Verify system dependencies installed:**
   ```
   Render logs should show:
   ✓ Installing tesseract-ocr
   ✓ Installing poppler-utils
   ```

3. **Increase timeout if needed:**
   In `render.yaml`:
   ```yaml
   startCommand: gunicorn app:app --timeout 300
   ```
   (increases to 5 minutes)

4. **Upgrade Render plan:**
   - Starter: 512 MB RAM
   - Standard: 2 GB RAM (better for large PDFs)

5. **Check backend logs:**
   ```
   Look for:
   - Memory errors
   - Tesseract errors
   - Timeout errors
   ```

**📸 SCREENSHOT PLACEHOLDER: Upload timeout error**

---

#### Issue 6: Slow First Request (Cold Start)

**Symptoms:**
- First API call takes 30-60 seconds
- Subsequent requests are fast
- Happens after inactivity

**Cause:**
- Using Render Free tier (sleeps after 15 min)

**Solution:**

**Option 1: Upgrade to Starter Plan ($7/month)**
- Best solution
- Eliminates cold starts completely
- Render → arc-pdf-api → Settings → Upgrade

**Option 2: Keep-Alive Ping (Free tier workaround)**
- Set up external monitor (UptimeRobot)
- Ping `/healthz` every 10 minutes
- Keeps service awake

**Option 3: Accept Trade-off**
- Inform users first load may be slow
- Good enough for low-traffic apps

**📸 SCREENSHOT PLACEHOLDER: Render cold start in logs**

---

#### Issue 7: Railway Costs Higher Than Expected

**Symptoms:**
- Monthly bill higher than estimated
- Unexpected usage spikes

**Cause:**
- High CPU usage
- Large database
- Lots of network egress

**Solution:**

1. **Check Railway metrics:**
   ```
   Railway → MySQL → Metrics
   ```
   Identify:
   - CPU spikes
   - Memory usage
   - Network traffic

2. **Optimize database:**
   ```sql
   -- Add indexes to slow queries
   CREATE INDEX idx_sku ON products(sku);

   -- Clean old data
   DELETE FROM price_books WHERE created_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);
   ```

3. **Review query patterns:**
   ```sql
   -- Find slow queries
   SHOW PROCESSLIST;
   ```

4. **Consider connection pooling:**
   Already configured in SQLAlchemy:
   ```python
   engine = create_engine(
       DATABASE_URL,
       pool_size=5,
       max_overflow=10
   )
   ```

**📸 SCREENSHOT PLACEHOLDER: Railway usage breakdown**

---

#### Issue 8: Build Fails on Render

**Symptoms:**
- Deployment fails
- Red X on deployment
- Error in build logs

**Common Causes & Solutions:**

**Cause A: Missing Dependencies**
```
Error: No module named 'mysqlclient'
```
**Solution:** Add to `requirements.txt`
```txt
mysqlclient==2.2.0
```

**Cause B: Build Script Permission Denied**
```
Error: Permission denied: ./render-build.sh
```
**Solution:** Make executable
```bash
chmod +x render-build.sh
git add render-build.sh
git commit -m "Fix permissions"
git push
```

**Cause C: Python Version Mismatch**
```
Error: Could not find a version that satisfies requirement...
```
**Solution:** Set Python version
```yaml
# render.yaml
envVars:
  - key: PYTHON_VERSION
    value: 3.11.0
```

**Cause D: System Dependencies Missing**
```
Error: Failed building wheel for mysqlclient
```
**Solution:** Ensure `render-build.sh` installs:
```bash
apt-get install -y default-libmysqlclient-dev build-essential
```

**📸 SCREENSHOT PLACEHOLDER: Render build error logs**

---

#### Issue 9: Vercel Build Fails

**Symptoms:**
- Deployment fails
- TypeScript errors
- Module not found

**Common Causes & Solutions:**

**Cause A: Wrong Root Directory**
```
Error: No package.json found
```
**Solution:** Set root directory to `frontend`

**Cause B: TypeScript Errors**
```
Error: Type 'string' is not assignable to type 'number'
```
**Solution:** Fix TypeScript errors or temporarily:
```json
// tsconfig.json
{
  "compilerOptions": {
    "noEmit": true,
    "skipLibCheck": true
  }
}
```

**Cause C: Missing Dependencies**
```
Error: Cannot find module '@tanstack/react-table'
```
**Solution:** Install dependency
```bash
cd frontend
npm install @tanstack/react-table
git add package.json package-lock.json
git commit -m "Add missing dependency"
git push
```

**📸 SCREENSHOT PLACEHOLDER: Vercel build error**

---

### Getting More Help

#### Official Documentation

- **Railway**: https://docs.railway.app/
- **Render**: https://render.com/docs
- **Vercel**: https://vercel.com/docs
- **Flask**: https://flask.palletsprojects.com/
- **Next.js**: https://nextjs.org/docs

#### Community Support

- **Railway Discord**: https://discord.gg/railway
- **Render Community**: https://community.render.com/
- **Vercel Discord**: https://vercel.com/discord
- **Stack Overflow**: Tag with `railway`, `render`, `vercel`

#### Direct Support

- **Railway**: support@railway.app
- **Render**: support@render.com
- **Vercel**: support@vercel.com

---

## 10. Next Steps

### Immediate Actions (After Deployment)

#### 1. Custom Domain (Optional)

**Purchase domain:**
- Namecheap: https://namecheap.com (~$10/year)
- Google Domains: https://domains.google
- Cloudflare: https://cloudflare.com

**Configure:**
1. Add to Vercel:
   ```
   Vercel → Project → Settings → Domains
   Add: arcpdftool.com
   ```

2. Update DNS:
   ```
   Type: CNAME
   Name: @
   Value: cname.vercel-dns.com
   ```

3. Update backend CORS:
   ```
   CORS_ORIGINS: https://arcpdftool.com
   ```

**📸 SCREENSHOT PLACEHOLDER: Custom domain setup**

#### 2. Email Notifications (Optional)

Set up alerts for:
- Upload completions
- Error notifications
- Daily usage summaries

**Tools:**
- SendGrid (free tier)
- Mailgun
- Amazon SES

#### 3. Analytics (Optional)

Track usage:
- **Google Analytics**: User behavior
- **Plausible**: Privacy-focused
- **PostHog**: Product analytics

#### 4. Backup Strategy

**Automated backups:**
- Railway: Already backing up daily
- Manual export weekly:
  ```bash
  mysqldump -h [HOST] -u root -p railway > backup.sql
  ```

### Short Term (Week 1-2)

#### 1. User Testing

- ✅ Have team test all features
- ✅ Upload real PDFs
- ✅ Verify accuracy
- ✅ Test on different browsers
- ✅ Test on mobile devices

#### 2. Documentation

Create user guides:
- How to upload PDFs
- How to compare price books
- How to export data
- Troubleshooting common issues

#### 3. Performance Baseline

Establish metrics:
- Average upload time
- API response times
- Database query performance
- User satisfaction

### Medium Term (Month 1-3)

#### 1. Feature Enhancements

Based on user feedback:
- Additional manufacturer support
- Bulk upload capability
- Advanced filtering
- Email exports
- API access for partners

#### 2. Optimization

Improve performance:
- Add database indexes
- Optimize PDF parsing
- Implement caching
- Compress assets

#### 3. Security Hardening

Enhance security:
- Add rate limiting
- Implement API authentication
- Add input validation
- Security audit

### Long Term (Month 3-12)

#### 1. Scaling Preparation

Monitor and plan:
- Database growth patterns
- Traffic trends
- Upgrade timing
- Cost projections

#### 2. Advanced Features

Consider:
- Machine learning for better parsing
- Predictive pricing
- Integration with ERP systems
- Mobile app

#### 3. Business Intelligence

Analytics:
- Usage patterns
- Most popular manufacturers
- User behavior analysis
- ROI measurement

---

## Conclusion

### Deployment Recap

You have successfully deployed a modern, scalable application using:

**Infrastructure:**
- ✅ **Railway MySQL**: Reliable database hosting
- ✅ **Render Backend**: Production-ready Flask API
- ✅ **Vercel Frontend**: Lightning-fast Next.js UI

**Features:**
- ✅ PDF parsing with OCR
- ✅ Database storage
- ✅ Price comparison
- ✅ Multi-format export
- ✅ Responsive UI

**Benefits:**
- ✅ Auto-scaling infrastructure
- ✅ Zero-downtime deployments
- ✅ Built-in monitoring
- ✅ Cost-effective hosting
- ✅ Easy maintenance

### Application URLs

**Production URLs:**
- **Frontend**: https://arc-pdf-tool.vercel.app
- **Backend API**: https://arc-pdf-api.onrender.com
- **Database**: Railway (private connection)

### Cost Summary

**Hobby/Small Business:**
- **Monthly**: $8-12
- **Annual**: ~$96-144
- **Best for**: Testing, low traffic, startups

**Production/Growing Business:**
- **Monthly**: $35-45
- **Annual**: ~$420-540
- **Best for**: Real business use, medium traffic

### Support Resources

**Documentation:**
- This deployment guide
- Platform-specific docs (Railway, Render, Vercel)
- Application README

**Monitoring:**
- Railway Metrics
- Render Logs
- Vercel Analytics
- UptimeRobot (optional)

**Help:**
- Platform support channels
- Community forums
- Direct support emails

### Success Metrics

Track these to measure deployment success:

**Technical:**
- ✅ Uptime > 99.5%
- ✅ API response time < 500ms
- ✅ Zero deployment failures
- ✅ No database errors

**Business:**
- ✅ User satisfaction
- ✅ Feature usage
- ✅ Parsing accuracy
- ✅ Cost efficiency

### Final Checklist

Before sharing with users:

- [ ] All three services deployed and running
- [ ] Health checks passing
- [ ] SSL/HTTPS working on all URLs
- [ ] Upload and parse working
- [ ] Export functionality tested
- [ ] Compare feature tested
- [ ] Mobile responsiveness verified
- [ ] Browser compatibility checked
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Team has access to dashboards
- [ ] Documentation updated
- [ ] Costs reviewed and acceptable

---

## Appendix

### A. Environment Variables Reference

#### Render Backend

| Variable | Value | Purpose |
|----------|-------|---------|
| `PYTHON_VERSION` | `3.11.0` | Python runtime version |
| `FLASK_ENV` | `production` | Flask environment mode |
| `SECRET_KEY` | [Auto-generated] | Flask session encryption |
| `MYSQL_HOST` | Railway host | Database connection |
| `MYSQL_PORT` | Railway port | Database port |
| `MYSQL_USER` | `root` | Database username |
| `MYSQL_PASSWORD` | Railway password | Database password |
| `MYSQL_DATABASE` | `railway` | Database name |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | OCR binary path |
| `CORS_ORIGINS` | Vercel URLs | Allowed frontend origins |

#### Vercel Frontend

| Variable | Value | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_API_URL` | Render backend URL | Backend API endpoint |

### B. Useful Commands

#### Railway MySQL

```sql
-- Check database size
SELECT table_schema AS "Database",
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS "Size (MB)"
FROM information_schema.TABLES
WHERE table_schema = 'railway'
GROUP BY table_schema;

-- Optimize tables
OPTIMIZE TABLE price_books;
OPTIMIZE TABLE products;

-- Check indexes
SHOW INDEX FROM products;
```

#### Render Logs

```bash
# View logs (from Render dashboard)
# Or use Render CLI:
render logs arc-pdf-api

# Follow logs in real-time:
render logs arc-pdf-api --tail
```

#### Vercel Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from command line
vercel --prod

# Pull environment variables locally
vercel env pull
```

### C. Performance Benchmarks

**Typical Performance:**

| Operation | Time | Notes |
|-----------|------|-------|
| Homepage load | 1-2s | First visit |
| API call | 100-300ms | Price books list |
| PDF upload (10 pages) | 30-45s | Including parse |
| PDF upload (50 pages) | 90-120s | Larger document |
| Export Excel | 2-5s | 1000 products |
| Compare price books | 5-10s | Depends on size |

### D. Database Schema

```sql
-- Full schema for reference

CREATE TABLE price_books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer VARCHAR(100) NOT NULL,
    edition VARCHAR(100),
    effective_date DATE,
    file_path VARCHAR(500),
    file_size INT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_products INT DEFAULT 0,
    parsing_confidence DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_manufacturer (manufacturer),
    INDEX idx_effective_date (effective_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    price_book_id INT NOT NULL,
    sku VARCHAR(255) NOT NULL,
    description TEXT,
    list_price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    category VARCHAR(100),
    finish_code VARCHAR(50),
    page_number INT,
    confidence_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    INDEX idx_price_book (price_book_id),
    INDEX idx_sku (sku),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE diff_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    old_price_book_id INT NOT NULL,
    new_price_book_id INT NOT NULL,
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_changes INT DEFAULT 0,
    new_products INT DEFAULT 0,
    removed_products INT DEFAULT 0,
    price_increases INT DEFAULT 0,
    price_decreases INT DEFAULT 0,
    diff_data JSON,
    FOREIGN KEY (old_price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    FOREIGN KEY (new_price_book_id) REFERENCES price_books(id) ON DELETE CASCADE,
    INDEX idx_old_book (old_price_book_id),
    INDEX idx_new_book (new_price_book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

**Document Version:** 1.0
**Last Updated:** October 21, 2025
**Next Review:** November 21, 2025
**Prepared By:** Development Team
**For:** CEO / Technical Stakeholders

---

*This deployment guide is specific to the ARC PDF Tool project using Railway MySQL, Render backend, and Vercel frontend. For questions or issues, refer to the Troubleshooting Guide or contact platform support.*

---

## Quick Reference Card

**Copy this section for quick access to important URLs and commands**

### URLs
- Frontend: https://arc-pdf-tool.vercel.app
- Backend: https://arc-pdf-api.onrender.com
- Health Check: https://arc-pdf-api.onrender.com/healthz

### Dashboards
- Railway: https://railway.app/project/[your-project]
- Render: https://dashboard.render.com/web/[your-service]
- Vercel: https://vercel.com/[your-username]/arc-pdf-tool

### Emergency Contacts
- Railway Support: support@railway.app
- Render Support: support@render.com
- Vercel Support: support@vercel.com

### Quick Troubleshooting
1. Check health endpoint first
2. Review Render logs
3. Verify Railway MySQL is running
4. Check CORS configuration
5. Clear browser cache

### Costs
- Railway: ~$1-5/month (usage-based)
- Render: $7/month (Starter recommended)
- Vercel: $0/month (Hobby tier)
- **Total: ~$8-12/month**
