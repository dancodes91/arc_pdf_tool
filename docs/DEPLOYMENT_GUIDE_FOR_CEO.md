# ARC PDF Tool - Complete Deployment Guide
## Flask Backend + React Frontend + MySQL Database

**Prepared for:** CEO
**Date:** October 21, 2025
**Estimated Deployment Time:** 45-60 minutes
**Cost:** $14-21/month (production tier)

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Database Setup (MySQL on PlanetScale)](#database-setup)
5. [Backend Deployment (Render)](#backend-deployment)
6. [Frontend Deployment (Vercel)](#frontend-deployment)
7. [Testing & Verification](#testing-verification)
8. [Monitoring & Maintenance](#monitoring-maintenance)
9. [Cost Breakdown](#cost-breakdown)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide walks through deploying the ARC PDF Tool, a comprehensive application for parsing manufacturer PDF price books. The application consists of:

- **Backend:** Flask Python API for PDF parsing, database management, and business logic
- **Frontend:** Next.js React application for user interface
- **Database:** MySQL for storing parsed price book data
- **File Storage:** Backend-managed file uploads

**Why these platforms?**
- **Render:** Excellent Python support, auto-scaling, easy deployment
- **PlanetScale/MySQL:** Industry-standard database with excellent performance
- **Vercel:** Best-in-class Next.js hosting with automatic deployments

---

## Architecture

```
┌─────────────────┐
│   Users         │
│   (Browser)     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│   Frontend (Vercel)     │
│   - Next.js/React       │
│   - Responsive UI       │
│   - Port: 443 (HTTPS)   │
└──────────┬──────────────┘
           │
           ↓
┌─────────────────────────┐
│   Backend (Render)      │
│   - Flask API           │
│   - PDF Processing      │
│   - Port: 10000         │
└──────────┬──────────────┘
           │
           ↓
┌─────────────────────────┐
│   Database              │
│   - MySQL (PlanetScale) │
│   - Port: 3306          │
└─────────────────────────┘
```

---

## Prerequisites

### Required Accounts (All Free to Create)
- ✅ **GitHub Account** - For code hosting and deployments
- ✅ **Render Account** - Sign up at https://render.com
- ✅ **PlanetScale Account** - Sign up at https://planetscale.com
- ✅ **Vercel Account** - Sign up at https://vercel.com

### Local Requirements (For Initial Setup)
- ✅ Git installed on your machine
- ✅ GitHub repository with project code
- ✅ Basic understanding of command line

**📸 SCREENSHOT PLACEHOLDER:** Screenshot of all four platform logos/signup pages

---

## Database Setup (MySQL on PlanetScale)

### Why PlanetScale?
- **Free Tier:** Perfect for development and small production deployments
- **MySQL Compatible:** Works with existing MySQL code
- **Auto-Scaling:** Handles traffic spikes automatically
- **Branching:** Database branches like Git for safe schema changes
- **Global Availability:** Fast from anywhere

### Step 1: Create PlanetScale Database

1. Go to https://planetscale.com
2. Click **"Sign Up"** (or Login if you have an account)
3. Click **"Create a database"**
4. Configure database:
   - **Name:** `arc-pdf-tool-db`
   - **Region:** Select closest to your users (e.g., `US East (Northern Virginia)`)
   - **Plan:** Select **"Hobby"** (Free tier)
5. Click **"Create database"**

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale dashboard showing database creation form

### Step 2: Get Database Credentials

1. In your database dashboard, click **"Connect"**
2. Select **"Connect with: General"**
3. You'll see credentials like:
   ```
   Host: aws.connect.psdb.cloud
   Username: xxxxxxxxxxxxxxxx
   Password: pscale_pw_xxxxxxxxxxxxxxxx
   Database: arc-pdf-tool-db
   Port: 3306
   ```
4. **IMPORTANT:** Copy these credentials to a secure location (you'll need them in Step 5)

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale connection modal showing credentials

### Step 3: Initialize Database Schema

1. Click **"Console"** tab in PlanetScale
2. Run the following SQL to create tables:

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

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
    INDEX idx_sku (sku)
);

-- Verify tables were created
SHOW TABLES;
```

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale console showing successful table creation

### Step 4: Enable Production Branch

1. Go to **"Branches"** tab
2. Your database comes with a `main` branch
3. Click **"Promote to production"** next to `main` branch
4. Confirm the promotion

This enables connection from external services like Render.

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale branches page showing production branch

---

## Backend Deployment (Render)

### Why Render for Backend?
- **Python Native:** Excellent support for Flask applications
- **Auto-Deploy:** Connects to GitHub for automatic deployments
- **Gunicorn:** Production-ready WSGI server included
- **Environment Variables:** Easy secrets management
- **Health Checks:** Automatic monitoring and restarts

### Step 5: Prepare Backend Code

Before deploying, ensure your repository has these files:

**✅ requirements.txt** (already exists in your project)
```txt
Flask==3.1.2
flask-cors==6.0.1
mysqlclient==2.2.0
gunicorn==23.0.0
[... other dependencies ...]
```

**✅ render-build.sh** (create if doesn't exist)
```bash
#!/bin/bash
# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr poppler-utils default-libmysqlclient-dev

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations (if using Alembic)
# alembic upgrade head
```

Make it executable:
```bash
chmod +x render-build.sh
```

**✅ render.yaml** (already exists, verify content)
```yaml
services:
  - type: web
    name: arc-pdf-api
    env: python
    buildCommand: chmod +x render-build.sh && ./render-build.sh
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
```

**📸 SCREENSHOT PLACEHOLDER:** VS Code or file explorer showing these files

### Step 6: Push Code to GitHub

```bash
# Add all files
git add .

# Commit changes
git commit -m "Prepare for Render deployment with MySQL"

# Push to GitHub
git push origin main
```

### Step 7: Create Render Web Service

1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect Account"** to link GitHub
4. Select your repository: `arc_pdf_tool`
5. Click **"Connect"**

**📸 SCREENSHOT PLACEHOLDER:** Render dashboard showing "New" button

### Step 8: Configure Web Service

Fill in the configuration form:

**Basic Settings:**
- **Name:** `arc-pdf-api`
- **Region:** `Ohio (US East)` (or closest to your users)
- **Branch:** `alex-feature` (or `main`)
- **Runtime:** `Python 3`

**Build Settings:**
- **Build Command:** `chmod +x render-build.sh && ./render-build.sh`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

**📸 SCREENSHOT PLACEHOLDER:** Render service configuration form

### Step 9: Add Environment Variables

Click **"Advanced"** and add these environment variables:

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.11.0` | Python version |
| `FLASK_ENV` | `production` | Environment mode |
| `SECRET_KEY` | [Auto-generated] | Click "Generate" button |
| `MYSQL_HOST` | [From PlanetScale Step 2] | Database host |
| `MYSQL_USER` | [From PlanetScale Step 2] | Database username |
| `MYSQL_PASSWORD` | [From PlanetScale Step 2] | Database password |
| `MYSQL_DB` | `arc-pdf-tool-db` | Database name |
| `MYSQL_PORT` | `3306` | Database port |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | OCR path |
| `CORS_ORIGINS` | `http://localhost:3000` | (Will update after Vercel deploy) |

**📸 SCREENSHOT PLACEHOLDER:** Render environment variables page with fields filled

### Step 10: Deploy Backend

1. Click **"Create Web Service"**
2. Render will start building your application
3. Watch the logs in real-time (this takes 5-10 minutes)
4. Look for: `==> Your service is live 🎉`

**Build process includes:**
- Installing system dependencies (Tesseract, Poppler, MySQL client)
- Installing Python packages
- Starting Gunicorn server

**📸 SCREENSHOT PLACEHOLDER:** Render build logs showing successful deployment

### Step 11: Get Backend URL

Once deployed, Render provides a URL like:
```
https://arc-pdf-api.onrender.com
```

**Copy this URL** - you'll need it for frontend deployment.

### Step 12: Verify Backend Health

Test the backend is working:

1. Open a browser and go to: `https://arc-pdf-api.onrender.com/healthz`
2. You should see:
   ```json
   {
     "status": "healthy",
     "service": "arc_pdf_tool",
     "timestamp": "2025-10-21T12:00:00Z"
   }
   ```

**📸 SCREENSHOT PLACEHOLDER:** Browser showing healthy backend response

---

## Frontend Deployment (Vercel)

### Why Vercel for Frontend?
- **Next.js Optimized:** Built by the creators of Next.js
- **Global CDN:** Lightning-fast worldwide
- **Automatic HTTPS:** SSL certificates included
- **Preview Deployments:** Every PR gets a preview URL
- **Zero Configuration:** Just connect and deploy

### Step 13: Prepare Frontend Environment

Update your frontend environment variables file:

**frontend/.env.local** (for local development)
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
```

**For Production:** We'll set this in Vercel dashboard

### Step 14: Create Vercel Project

1. Go to https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Click **"Import Git Repository"**
4. Find your repository: `arc_pdf_tool`
5. Click **"Import"**

**📸 SCREENSHOT PLACEHOLDER:** Vercel import project page

### Step 15: Configure Project Settings

**Framework Preset:** Next.js (should auto-detect)

**Build & Output Settings:**
- **Root Directory:** `frontend` ← **IMPORTANT!**
- **Build Command:** `npm run build` (default)
- **Output Directory:** `.next` (default)
- **Install Command:** `npm install` (default)

**📸 SCREENSHOT PLACEHOLDER:** Vercel project configuration with Root Directory highlighted

### Step 16: Add Environment Variables

Click **"Environment Variables"** and add:

| Key | Value | Environments |
|-----|-------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://arc-pdf-api.onrender.com` | Production, Preview, Development |

**IMPORTANT:** Use the backend URL from Step 11.

**Note:** The `NEXT_PUBLIC_` prefix makes this variable accessible to client-side code.

**📸 SCREENSHOT PLACEHOLDER:** Vercel environment variables configuration

### Step 17: Deploy Frontend

1. Click **"Deploy"**
2. Vercel will build your Next.js application (2-3 minutes)
3. Watch the build logs
4. Look for: **"✓ Build Completed"**

**📸 SCREENSHOT PLACEHOLDER:** Vercel build logs showing success

### Step 18: Get Frontend URL

After deployment, Vercel provides URLs:
- **Production:** `https://arc-pdf-tool.vercel.app`
- **Generated:** `https://arc-pdf-tool-abc123.vercel.app`

**Copy the production URL** for the next step.

**📸 SCREENSHOT PLACEHOLDER:** Vercel deployment success page with URL

### Step 19: Update Backend CORS

The backend needs to allow requests from your Vercel domain.

1. Go back to **Render Dashboard**
2. Open your **arc-pdf-api** service
3. Go to **"Environment"** tab
4. Find `CORS_ORIGINS` variable
5. Update value to:
   ```
   http://localhost:3000,https://arc-pdf-tool.vercel.app
   ```
6. Click **"Save Changes"**
7. Render will automatically redeploy (2-3 minutes)

**📸 SCREENSHOT PLACEHOLDER:** Render environment variable update

---

## Testing & Verification

### Step 20: Verify Complete Integration

**Test 1: Access Frontend**
1. Open browser to: `https://arc-pdf-tool.vercel.app`
2. You should see the dashboard page
3. Check browser console for errors (F12 → Console tab)

**Expected:** No CORS errors, page loads correctly

**📸 SCREENSHOT PLACEHOLDER:** Frontend dashboard homepage

**Test 2: Backend API Connection**
1. On the dashboard, check if price books are loading
2. Open browser DevTools (F12) → Network tab
3. Look for API requests to `/api/price-books`
4. Status should be `200 OK`

**Expected:** API requests succeed

**📸 SCREENSHOT PLACEHOLDER:** Browser DevTools showing successful API call

**Test 3: Upload Functionality**
1. Click **"Upload"** in navigation
2. Select manufacturer (e.g., "Hager")
3. Choose a test PDF file
4. Click **"Upload & Parse"**
5. Wait for processing (30-60 seconds for large PDFs)

**Expected:** Progress indication, successful parsing, redirect to preview

**📸 SCREENSHOT PLACEHOLDER:** Upload page with file selected

**Test 4: Database Verification**
1. Go to PlanetScale dashboard
2. Open **"Console"** tab
3. Run query:
   ```sql
   SELECT COUNT(*) FROM price_books;
   SELECT COUNT(*) FROM products;
   ```

**Expected:** Shows uploaded data

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale console showing data

**Test 5: Export Functionality**
1. From preview page, click **"Export"**
2. Select format (Excel, CSV, or JSON)
3. Click **"Download"**

**Expected:** File downloads successfully

**Test 6: Compare Functionality**
1. Upload a second PDF (different edition)
2. Go to **"Compare"** page
3. Select two price books
4. Click **"Generate Comparison"**

**Expected:** Diff results showing price changes, new/removed products

---

## Monitoring & Maintenance

### Application Monitoring

**Backend Logs (Render)**
1. Go to Render Dashboard
2. Click on **"arc-pdf-api"**
3. Click **"Logs"** tab
4. View real-time application logs

**What to look for:**
- `ERROR` level messages
- `500` status codes
- Database connection errors
- Memory issues

**📸 SCREENSHOT PLACEHOLDER:** Render logs dashboard

**Frontend Logs (Vercel)**
1. Go to Vercel Dashboard
2. Click on your project
3. Click **"Deployments"** tab
4. Click on latest deployment
5. Click **"Functions"** or **"Build Logs"**

**What to look for:**
- Build failures
- Runtime errors
- API connection issues

**📸 SCREENSHOT PLACEHOLDER:** Vercel function logs

### Database Monitoring

**PlanetScale Insights**
1. Go to PlanetScale Dashboard
2. Click **"Insights"** tab
3. View:
   - Query performance
   - Slow queries
   - Storage usage
   - Connection count

**📸 SCREENSHOT PLACEHOLDER:** PlanetScale insights dashboard

### Uptime Monitoring (Optional)

**Recommended Tools:**
- **UptimeRobot** (free) - https://uptimerobot.com
- **Pingdom** (paid) - https://pingdom.com

**Setup:**
1. Monitor URL: `https://arc-pdf-api.onrender.com/healthz`
2. Check interval: 5 minutes
3. Alert on: 2 consecutive failures

### Performance Optimization

**Backend (Render):**
- Monitor response times in logs
- Consider upgrading to **Standard** plan ($25/month) for:
  - No cold starts
  - Faster builds
  - More memory (1GB → 2GB)

**Frontend (Vercel):**
- Check **Analytics** tab for:
  - Page load times
  - Core Web Vitals
  - Geographic performance

**Database (PlanetScale):**
- Monitor **Insights** for slow queries
- Add indexes for frequently queried fields
- Consider upgrading to **Scaler** plan ($39/month) for:
  - More storage (10GB → 100GB)
  - More connections (1000 → 10000)

---

## Cost Breakdown

### Development/Testing (Free Tier)

| Service | Plan | Cost | Limitations |
|---------|------|------|-------------|
| Render Backend | Free | $0/month | Sleeps after 15min inactivity, 750 hours/month |
| PlanetScale MySQL | Hobby | $0/month | 5GB storage, 1 billion row reads/month |
| Vercel Frontend | Hobby | $0/month | 100GB bandwidth, unlimited sites |
| **TOTAL** | | **$0/month** | Good for testing, not production |

**Limitations for Production:**
- ⚠️ Backend sleeps = First request after idle takes 30-60 seconds
- ⚠️ Database row limits may be hit with heavy usage
- ⚠️ No SLA guarantees

### Production (Recommended)

| Service | Plan | Cost | Benefits |
|---------|------|------|----------|
| Render Backend | Starter | $7/month | Always on, 512MB RAM, faster builds |
| PlanetScale MySQL | Scaler | $39/month | 100GB storage, 100 billion row reads |
| Vercel Frontend | Hobby | $0/month | Sufficient for most use cases |
| **TOTAL** | | **$46/month** | Professional production setup |

**OR** (Budget Option):

| Service | Plan | Cost | Benefits |
|---------|------|------|----------|
| Render Backend | Starter | $7/month | Always on, 512MB RAM |
| PlanetScale MySQL | Scaler Pro | $29/month | 25GB storage, 25B row reads |
| Vercel Frontend | Hobby | $0/month | Sufficient for most use cases |
| **TOTAL** | | **$36/month** | Cost-effective production |

### Enterprise (High Traffic)

| Service | Plan | Cost | Benefits |
|---------|------|------|----------|
| Render Backend | Pro | $25/month | 2GB RAM, priority support |
| PlanetScale MySQL | Enterprise | Custom | Unlimited, dedicated resources |
| Vercel Frontend | Pro | $20/month | Advanced analytics, team features |
| **TOTAL** | | **$45+/month** | High availability, scalable |

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Backend Returns 404 for All Routes

**Symptoms:**
- Frontend shows "Network Error"
- All API calls return 404
- Backend logs show: `Not found`

**Causes:**
- Routes not registered properly
- Application not starting correctly

**Solution:**
```bash
# Check Render logs for startup errors
# Verify app.py has:
app.register_blueprint(api)

# Redeploy:
git commit --allow-empty -m "Trigger redeploy"
git push origin main
```

#### Issue 2: CORS Errors in Browser

**Symptoms:**
```
Access to XMLHttpRequest at 'https://arc-pdf-api.onrender.com/api/price-books'
from origin 'https://arc-pdf-tool.vercel.app' has been blocked by CORS policy
```

**Solution:**
1. Check backend `CORS_ORIGINS` includes your Vercel URL
2. Ensure URL has NO trailing slash
3. Redeploy backend after changing

```python
# In app.py, verify:
CORS(app, origins=[
    r"http://localhost:\d+",
    r"https?://.*\.vercel\.app",
])
```

#### Issue 3: Database Connection Fails

**Symptoms:**
- Backend logs: `Can't connect to MySQL server`
- `/healthz` shows database check failed

**Causes:**
- Wrong credentials
- PlanetScale branch not promoted to production
- Firewall blocking connection

**Solution:**
1. Verify environment variables in Render:
   - `MYSQL_HOST`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_DB`
2. Check PlanetScale:
   - Branch is promoted to production
   - Connection is allowed from external IPs
3. Test connection from Render shell:
   ```bash
   # In Render shell
   mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DB -e "SHOW TABLES;"
   ```

#### Issue 4: Frontend Environment Variable Not Working

**Symptoms:**
- API calls go to wrong URL
- Undefined errors in console

**Causes:**
- Environment variable not prefixed with `NEXT_PUBLIC_`
- Variable not set in correct environment (Production/Preview/Development)
- Deployment not rebuilt after adding variable

**Solution:**
1. Ensure variable name starts with `NEXT_PUBLIC_`
2. Add to all environments in Vercel
3. Trigger new deployment:
   - Vercel Dashboard → Deployments → ⋯ → Redeploy

#### Issue 5: PDF Upload Fails

**Symptoms:**
- Upload returns 500 error
- Backend logs show Tesseract or Poppler errors

**Causes:**
- System dependencies not installed
- Insufficient memory
- Invalid PDF file

**Solution:**
1. Verify `render-build.sh` installs dependencies:
   ```bash
   apt-get install -y tesseract-ocr poppler-utils
   ```
2. Check Render logs during build
3. Test with small, valid PDF first
4. Consider upgrading Render plan for more memory

#### Issue 6: Slow First Request (Cold Start)

**Symptoms:**
- First request after idle takes 30-60 seconds
- Subsequent requests are fast

**Cause:**
- Free tier backend sleeps after 15 minutes of inactivity

**Solutions:**
1. **Upgrade to Starter plan** ($7/month) - Eliminates cold starts
2. **Keep-alive ping** - Set up external monitor to ping `/healthz` every 10 minutes
3. **Accept trade-off** - Inform users first load may be slow

#### Issue 7: Build Fails on Render

**Symptoms:**
- Build logs show errors
- Deployment fails

**Common Causes & Solutions:**

**Missing dependencies:**
```bash
# Add to requirements.txt
mysqlclient==2.2.0
```

**Permission denied on build script:**
```bash
# In render-build.sh, first line:
#!/bin/bash

# Make executable locally:
chmod +x render-build.sh
git add render-build.sh
git commit -m "Make build script executable"
```

**Python version mismatch:**
```yaml
# In render.yaml, ensure:
envVars:
  - key: PYTHON_VERSION
    value: 3.11.0
```

### Getting Help

**Official Documentation:**
- Render: https://render.com/docs
- PlanetScale: https://planetscale.com/docs
- Vercel: https://vercel.com/docs
- Flask: https://flask.palletsprojects.com/

**Community Support:**
- Render Community: https://community.render.com
- PlanetScale Discord: https://planetscale.com/discord
- Vercel Discord: https://vercel.com/discord

**Direct Support:**
- Render: support@render.com
- PlanetScale: support@planetscale.com
- Vercel: support@vercel.com

---

## Continuous Deployment

### Automatic Deployments

Both Render and Vercel automatically deploy when you push to GitHub:

**Workflow:**
1. Make code changes locally
2. Commit changes: `git commit -m "Your message"`
3. Push to GitHub: `git push origin main`
4. **Render** detects push and rebuilds backend (5-10 min)
5. **Vercel** detects push and rebuilds frontend (2-3 min)

**📸 SCREENSHOT PLACEHOLDER:** Git workflow diagram

### Preview Deployments (Vercel)

Every pull request automatically gets a preview URL:

1. Create feature branch: `git checkout -b feature/new-ui`
2. Make changes and push
3. Create pull request on GitHub
4. Vercel automatically deploys preview
5. Test at preview URL before merging

**Benefit:** Test changes in production-like environment before going live.

---

## Post-Deployment Checklist

Use this checklist to ensure everything is working:

### Backend Verification
- [ ] Backend URL is accessible: `https://arc-pdf-api.onrender.com`
- [ ] Health check returns 200: `/healthz`
- [ ] API endpoints respond: `/api/price-books`
- [ ] Database connection works (check PlanetScale Console)
- [ ] Logs are clean (no errors in Render logs)
- [ ] CORS is configured for Vercel domain
- [ ] All environment variables are set
- [ ] Build completes successfully

### Frontend Verification
- [ ] Frontend URL loads: `https://arc-pdf-tool.vercel.app`
- [ ] Dashboard displays without errors
- [ ] API calls succeed (check browser DevTools → Network)
- [ ] No CORS errors in console
- [ ] Environment variable `NEXT_PUBLIC_API_URL` is set
- [ ] Build completes successfully

### Database Verification
- [ ] PlanetScale database is created
- [ ] Branch is promoted to production
- [ ] Tables are created (price_books, products)
- [ ] Connection credentials are correct
- [ ] Can query data from Console

### Functionality Testing
- [ ] Can upload PDF file
- [ ] PDF parsing completes successfully
- [ ] Data appears in database
- [ ] Preview page shows parsed products
- [ ] Export (Excel/CSV/JSON) works
- [ ] Compare feature generates diffs
- [ ] All navigation links work

### Monitoring Setup
- [ ] Can access Render logs
- [ ] Can access Vercel deployment logs
- [ ] Can view PlanetScale Insights
- [ ] Optional: Uptime monitoring configured
- [ ] Optional: Error tracking (Sentry) configured

### Documentation
- [ ] Deployment URLs documented
- [ ] Credentials stored securely
- [ ] Team has access to dashboards
- [ ] This guide is saved for reference

---

## Next Steps

### Immediate (After Deployment)
1. **Custom Domain** (Optional)
   - Purchase domain (e.g., arc-pdf-tool.com)
   - Configure in Vercel: Settings → Domains
   - Update CORS_ORIGINS in backend

2. **SSL Certificate**
   - Automatic on Render and Vercel
   - Verify HTTPS works

3. **Backups**
   - PlanetScale: Automatic daily backups included
   - Download database backup manually:
     ```bash
     pscale database dump arc-pdf-tool-db main
     ```

### Short Term (Week 1-2)
1. **Monitor Performance**
   - Check response times
   - Monitor error rates
   - Track database query performance

2. **User Testing**
   - Have team test all features
   - Upload real PDFs
   - Verify accuracy

3. **Documentation**
   - Create user guide
   - Document API endpoints
   - Write troubleshooting guide

### Long Term (Month 1-3)
1. **Performance Optimization**
   - Add database indexes
   - Optimize slow queries
   - Implement caching if needed

2. **Feature Enhancements**
   - Add more manufacturers
   - Improve UI/UX
   - Add analytics

3. **Scaling Preparation**
   - Monitor usage patterns
   - Plan for traffic growth
   - Consider CDN for uploaded files

---

## Conclusion

You now have a fully deployed, production-ready application with:

✅ **Secure Database:** MySQL on PlanetScale with automatic backups
✅ **Scalable Backend:** Flask API on Render with auto-scaling
✅ **Fast Frontend:** Next.js on Vercel with global CDN
✅ **Continuous Deployment:** Automatic updates on git push
✅ **Monitoring:** Real-time logs and insights

**Application URLs:**
- Frontend: `https://arc-pdf-tool.vercel.app`
- Backend API: `https://arc-pdf-api.onrender.com`
- Database: `aws.connect.psdb.cloud` (PlanetScale)

**Total Cost:** $46/month (production tier) or $0/month (free tier for testing)

**Support:** For questions or issues, refer to the Troubleshooting section or contact platform support.

---

**Document Version:** 1.0
**Last Updated:** October 21, 2025
**Next Review:** November 21, 2025

---

*This deployment guide was created specifically for the ARC PDF Tool project. For updates or questions, please contact the development team.*
