# Railway MySQL + Render Backend Deployment Guide

Complete step-by-step guide for deploying the ARC PDF Tool backend on Render with MySQL database on Railway.

---

## Overview

**Architecture:**
- **Database**: MySQL 8.0 on Railway (managed service)
- **Backend API**: Flask app on Render (web service)
- **Frontend**: Already deployed on Vercel (https://arcpdftool.vercel.app)

**Cost:**
- Railway MySQL: Trial ($5/month credit) → Hobby ($5/month)
- Render Backend: Free tier available (750 hours/month)
- Network egress charges apply for Railway → Render traffic

---

## Part 1: Setup MySQL Database on Railway

### Step 1: Create Railway Account
1. Go to https://railway.app/
2. Sign up using GitHub (recommended for integration)
3. Verify your email address

### Step 2: Create a New Project
1. Click **"New Project"** in Railway dashboard
2. Select **"Provision MySQL"** from template list
3. Wait 30-60 seconds for database provisioning

### Step 3: Get MySQL Connection Details
1. Click on the MySQL service in your Railway project
2. Go to **"Variables"** tab
3. Railway automatically provides these environment variables:
   - `MYSQLHOST` - Database host address
   - `MYSQLPORT` - Port (default: 3306)
   - `MYSQLUSER` - Username (default: root)
   - `MYSQLPASSWORD` - Auto-generated password
   - `MYSQLDATABASE` - Database name (default: railway)
   - `MYSQL_URL` - Full connection string

4. **Copy the `MYSQL_URL` value** - format:
   ```
   mysql://root:<password>@<host>:<port>/railway
   ```

### Step 4: Enable Public Networking (TCP Proxy)
1. In the MySQL service, go to **"Settings"** tab
2. Scroll to **"Networking"**
3. Click **"Enable TCP Proxy"** (if not already enabled)
4. Note the public proxy URL (e.g., `tcp-proxy-region.railway.app:12345`)
5. ⚠️ **Important**: Network egress charges apply for external connections

### Step 5: Create Application Database
Railway creates a default `railway` database. To create `arc_pdf_tool` database:

**Option A: Using Railway CLI** (recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Connect to MySQL
railway run mysql -u root -p

# Create database
CREATE DATABASE arc_pdf_tool;
USE arc_pdf_tool;
exit;
```

**Option B: Using External MySQL Client**
```bash
# Use the MYSQL_URL from Step 3
mysql -h <MYSQLHOST> -P <MYSQLPORT> -u root -p

# Enter password when prompted
# Then create database:
CREATE DATABASE arc_pdf_tool;
```

### Step 6: Initialize Database Schema
On your local machine:

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="mysql://root:<password>@<host>:<port>/arc_pdf_tool"

# Run migration script
python scripts/init_mysql.py
```

Expected output:
```
Initializing MySQL database...
Running SQL file: migrations/versions/001_initial_schema.sql
Verifying table creation...
✓ All 8 tables created successfully
Database initialization complete!
```

---

## Part 2: Deploy Flask Backend on Render

### Step 1: Prepare GitHub Repository
1. Ensure your `arc_pdf_tool` code is pushed to GitHub
2. Verify these files exist:
   - `requirements.txt` - Python dependencies
   - `app.py` - Flask application entry point
   - `.gitignore` - Excludes `.env`, `uploads/`, etc.

### Step 2: Create Render Account
1. Go to https://render.com/
2. Sign up using GitHub (recommended)
3. Authorize Render to access your repositories

### Step 3: Create New Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your `arc_pdf_tool` GitHub repository
3. Configure service:
   - **Name**: `arc-pdf-tool` (or your preferred name)
   - **Region**: Choose closest to users (e.g., Oregon, Ohio, Frankfurt)
   - **Branch**: `main` (or `alex-feature` if using current branch)
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
     ```

### Step 4: Configure Environment Variables
In Render dashboard, go to **"Environment"** tab and add these variables:

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `mysql://root:<password>@<host>:<port>/arc_pdf_tool` | From Railway MYSQL_URL |
| `SECRET_KEY` | Generate random string | Flask secret: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | `production` | Production mode |
| `UPLOAD_FOLDER` | `uploads` | PDF upload directory |
| `EXPORT_FOLDER` | `exports` | Export files directory |
| `PYTHONUNBUFFERED` | `1` | Enable real-time logs |

**Optional (for Baserow export):**
| Key | Value |
|-----|-------|
| `BASEROW_API_TOKEN` | Your Baserow API token |
| `BASEROW_DATABASE_ID` | Your Baserow database ID |
| `BASEROW_TABLE_ID` | Your Baserow table ID |

### Step 5: Deploy Service
1. Click **"Save and Deploy"** or **"Create Web Service"**
2. Wait 3-5 minutes for build and deployment
3. Monitor logs in Render dashboard
4. Once deployed, note your service URL: `https://arc-pdf-tool.onrender.com`

### Step 6: Verify Deployment
Test health check endpoints:

```bash
# Health check
curl https://arc-pdf-tool.onrender.com/healthz

# Expected response:
{
  "status": "healthy",
  "service": "arc_pdf_tool",
  "timestamp": "2025-10-16T12:34:56Z"
}

# Readiness check
curl https://arc-pdf-tool.onrender.com/readyz

# Expected response:
{
  "status": "ready",
  "checks": {
    "database": true,
    "filesystem": true
  },
  "timestamp": "2025-10-16T12:34:56Z"
}
```

---

## Part 3: Connect Frontend to Backend

### Update Vercel Frontend Environment Variables
1. Go to Vercel dashboard → Your project → **"Settings"** → **"Environment Variables"**
2. Update/add these variables:
   - `NEXT_PUBLIC_API_URL` = `https://arc-pdf-tool.onrender.com`
3. Redeploy frontend:
   ```bash
   # In Vercel dashboard, go to Deployments
   # Click "Redeploy" on latest deployment
   ```

### Verify CORS Configuration
Your `app.py` already has CORS configured (from previous fix):

```python
CORS(app,
     origins=[
         'https://arcpdftool.vercel.app',  # ✅ Production frontend
         'http://localhost:3000',
         # ... other origins
     ],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
)
```

---

## Part 4: Post-Deployment Verification

### Test PDF Upload Workflow
1. Go to https://arcpdftool.vercel.app
2. Click **"Upload PDF"**
3. Select a test PDF (e.g., `test_data/pdfs/hager-price-book.pdf`)
4. Select manufacturer (if applicable)
5. Upload and verify:
   - Parse completes successfully
   - Products displayed in preview
   - Price book status is `pending_approval`

### Test Database Connection
From local machine with Railway DATABASE_URL:

```bash
export DATABASE_URL="mysql://root:<password>@<host>:<port>/arc_pdf_tool"

python << EOF
from database.manager import PriceBookManager

manager = PriceBookManager()
price_books = manager.list_price_books()
print(f"Found {len(price_books)} price books in database")
for pb in price_books[:5]:
    print(f"- {pb['manufacturer']} ({pb['created_at']})")
EOF
```

### Monitor Logs
**Railway MySQL logs:**
1. Go to Railway dashboard → MySQL service
2. Click **"Logs"** tab
3. Monitor connection activity

**Render Backend logs:**
1. Go to Render dashboard → Your web service
2. Click **"Logs"** tab
3. Monitor API requests and errors

---

## Part 5: Troubleshooting

### Issue 1: Database Connection Failed
**Error**: `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")`

**Solutions:**
1. Verify Railway TCP Proxy is enabled
2. Check DATABASE_URL format:
   ```
   mysql://<user>:<password>@<host>:<port>/<database>
   ```
3. Ensure Railway MySQL service is running (green status)
4. Test connection manually:
   ```bash
   mysql -h <host> -P <port> -u root -p
   ```

### Issue 2: Render Build Fails
**Error**: `ModuleNotFoundError: No module named 'pymysql'`

**Solutions:**
1. Verify `requirements.txt` includes all dependencies:
   ```
   Flask==3.0.0
   Flask-CORS==4.0.0
   pymysql==1.1.0
   SQLAlchemy==2.0.23
   gunicorn==21.2.0
   # ... other dependencies
   ```
2. Check build logs for specific missing modules
3. Rebuild service after updating `requirements.txt`

### Issue 3: CORS Errors Persist
**Error**: "No 'Access-Control-Allow-Origin' header"

**Solutions:**
1. Verify Vercel frontend URL matches CORS origins in `app.py`
2. Check Render service URL is correct in Vercel env vars
3. Clear browser cache and test in incognito mode
4. Verify `api_routes.py` has OPTIONS handler (already implemented)

### Issue 4: Render Timeout (502 Bad Gateway)
**Error**: Service times out after 30 seconds

**Solutions:**
1. **Upgrade to Render paid tier** (increases timeout to 10 minutes)
2. **Optimize parsing**:
   - Process fewer pages initially
   - Use async processing for large PDFs
   - Add progress updates to frontend
3. **Current config** (`app.py` line 122):
   ```python
   'max_pages': None  # Process all pages
   ```
   Consider changing to `'max_pages': 50` for free tier

### Issue 5: Railway Network Egress Costs
**Warning**: High network charges from external connections

**Solutions:**
1. **Monitor usage** in Railway billing dashboard
2. **Optimize queries**:
   - Use pagination for large datasets
   - Cache frequently accessed data
   - Minimize database round trips
3. **Consider alternatives**:
   - Use Railway for hosting both database and backend (private networking)
   - Switch to Render PostgreSQL (free tier, no egress charges)

---

## Part 6: Production Best Practices

### 1. Database Backups
**Railway:**
1. Go to MySQL service → **"Settings"** → **"Backups"**
2. Enable automatic daily backups
3. Configure retention period (7-30 days recommended)
4. Test restore procedure monthly

**Manual backup:**
```bash
# Backup to local file
mysqldump -h <host> -P <port> -u root -p arc_pdf_tool > backup_$(date +%Y%m%d).sql

# Restore from backup
mysql -h <host> -P <port> -u root -p arc_pdf_tool < backup_20251016.sql
```

### 2. Monitoring & Alerts
**Render:**
1. Enable email alerts for build failures
2. Monitor response times in dashboard
3. Set up UptimeRobot or Pingdom for external monitoring

**Custom health checks:**
```python
# Already implemented in app.py:280-318
GET /healthz  # Liveness check
GET /readyz   # Readiness check (includes DB connectivity)
```

### 3. Logging
**Enhance logging** in production:
```python
# config.py or app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
```

### 4. Security
**Environment variables:**
- Never commit `.env` files to GitHub
- Rotate `SECRET_KEY` periodically
- Use strong database passwords (Railway auto-generates)

**CORS:**
- Only allow trusted origins (already configured)
- Review CORS settings quarterly

**File uploads:**
- Validate file types (already implemented: `allowed_file()`)
- Limit file sizes (consider adding to config)
- Scan PDFs for malware (optional: integrate ClamAV)

### 5. Performance Optimization
**Database:**
```sql
-- Add indexes for common queries (already in schema)
CREATE INDEX idx_sku ON products(sku);
CREATE INDEX idx_model ON products(model);
CREATE INDEX idx_price_book ON products(price_book_id);
```

**Caching:**
Consider adding Redis for frequently accessed data:
```python
# Example: Cache price book summaries
from functools import lru_cache

@lru_cache(maxsize=100)
def get_price_book_summary(price_book_id):
    # ... fetch from database
```

**Async processing:**
For large PDFs, use Celery + Redis for background tasks:
```bash
# Future enhancement (not currently implemented)
pip install celery redis
```

---

## Part 7: Cost Estimates

### Railway MySQL
| Plan | Monthly Cost | Features |
|------|-------------|----------|
| Trial | $5 credit (once) | Full features, expires after credit used |
| Hobby | $5/month | Unlimited projects, shared resources |
| Pro | $20/month | Priority support, dedicated resources |

**Network egress**: ~$0.10/GB (Render → Railway traffic)

### Render Backend
| Plan | Monthly Cost | Features |
|------|-------------|----------|
| Free | $0 | 750 hours/month, 512MB RAM, sleeps after inactivity |
| Starter | $7/month | Always-on, 512MB RAM, 30s timeout → 10min |
| Standard | $25/month | 2GB RAM, autoscaling, custom domains |

**Estimated total**: $5-12/month for hobby/starter deployment

---

## Part 8: Quick Reference Commands

### Railway CLI
```bash
# Install
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Run commands in Railway environment
railway run python scripts/init_mysql.py

# View logs
railway logs
```

### Render CLI (Alternative)
```bash
# Deploy via Git push (automatic)
git push origin main

# Manual redeploy
curl -X POST https://api.render.com/deploy/srv-<service-id>
```

### Database Management
```bash
# Connect to Railway MySQL
mysql -h <host> -P <port> -u root -p

# Import test data
python scripts/load_test_data.py

# Verify data
python scripts/evaluate_accuracy.py
```

---

## Part 9: Deployment Checklist

- [ ] Railway MySQL provisioned
- [ ] Database `arc_pdf_tool` created
- [ ] Schema initialized (`scripts/init_mysql.py`)
- [ ] Render web service created
- [ ] Environment variables configured in Render
- [ ] CORS origins include Vercel frontend
- [ ] Build and start commands correct
- [ ] Service deployed successfully (green status)
- [ ] Health checks return 200 OK
- [ ] Frontend connected to backend API
- [ ] Test PDF upload workflow
- [ ] Review/approve workflow tested
- [ ] Export functionality verified (CSV/Excel)
- [ ] Backups enabled on Railway
- [ ] Monitoring alerts configured
- [ ] Documentation updated with production URLs

---

## Support Resources

**Railway:**
- Docs: https://docs.railway.com/
- Community: https://discord.gg/railway
- Status: https://status.railway.app/

**Render:**
- Docs: https://render.com/docs
- Community: https://community.render.com/
- Status: https://status.render.com/

**Project-Specific:**
- GitHub Issues: (your repo)/issues
- Runbook: `docs/RUNBOOK.md`
- API Docs: `docs/API.md` (if exists)

---

**Last Updated**: 2025-10-16
**Version**: 1.0.0
