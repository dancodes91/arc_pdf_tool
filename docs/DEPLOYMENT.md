# Production Deployment Guide

## Architecture
- **Backend**: Flask API on Render
- **Frontend**: Next.js on Vercel
- **Database**: PostgreSQL on Render
- **Storage**: File uploads handled by backend

## Prerequisites
- Render account (render.com)
- Vercel account (vercel.com)
- GitHub repository with code pushed

---

## Backend Deployment (Render)

### 1. Create PostgreSQL Database
1. Log into Render dashboard
2. Click "New +" > "PostgreSQL"
3. Settings:
   - Name: arc-pdf-db
   - Database: arc_pdf_tool
   - Region: Select nearest
   - Plan: Free (testing) or Starter ($7/month)
4. Create database
5. Copy "Internal Database URL" for later

### 2. Deploy Flask API
1. Click "New +" > "Web Service"
2. Connect GitHub repository
3. Settings:
   - Name: arc-pdf-api
   - Environment: Python 3
   - Branch: alex-feature
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app:app
   - Plan: Free (testing) or Starter ($7/month)

4. Environment Variables (click "Advanced"):
   ```
   DATABASE_URL = [PostgreSQL Internal URL]
   SECRET_KEY = [Generate with: openssl rand -hex 32]
   FLASK_ENV = production
   TESSERACT_CMD = /usr/bin/tesseract
   ```

5. Click "Create Web Service"
6. Wait 5-10 minutes for deployment
7. Copy service URL: https://arc-pdf-api.onrender.com

### 3. Verify Backend
```bash
curl https://arc-pdf-api.onrender.com/api/health
# Should return: {"status":"healthy",...}
```

---

## Frontend Deployment (Vercel)

### 1. Deploy Next.js App
1. Log into Vercel dashboard
2. Click "Add New..." > "Project"
3. Import GitHub repository
4. Settings:
   - Framework: Next.js (auto-detected)
   - Root Directory: frontend
   - Build Command: npm run build
   - Output Directory: .next

5. Environment Variable:
   - Key: NEXT_PUBLIC_API_URL
   - Value: https://arc-pdf-api.onrender.com

6. Click "Deploy"
7. Wait 2-3 minutes
8. Copy deployment URL: https://arc-pdf-tool.vercel.app

### 2. Verify Frontend
Open browser to: https://arc-pdf-tool.vercel.app

---

## CORS Configuration

Update `app.py` to allow Vercel domain:

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "https://arc-pdf-tool.vercel.app"
        ]
    }
})
```

Commit and push - Render will auto-deploy.

---

## Testing Deployment

### Upload Test
1. Navigate to /upload
2. Select manufacturer
3. Upload PDF from test_data/pdfs/
4. Verify parsing completes
5. Check preview page shows results

### Export Test
1. Go to preview page
2. Click CSV, Excel, or JSON export
3. Verify download works

### Compare Test
1. Upload 2 price books
2. Navigate to /compare
3. Select both books
4. Verify fuzzy matching works

---

## Monitoring

### Backend Logs
Render Dashboard > arc-pdf-api > Logs

### Frontend Logs
Vercel Dashboard > Project > Deployments > Function Logs

---

## Cost Breakdown

### Free Tier (Testing)
- Render Backend: Free (sleeps after 15min idle)
- Render PostgreSQL: Free (limited storage)
- Vercel Frontend: Free
- Total: $0/month

### Production Tier
- Render Backend: Starter $7/month
- Render PostgreSQL: Starter $7/month
- Vercel Frontend: Free
- Total: $14/month

---

## Troubleshooting

### Backend 500 Error
Check Render logs for:
- Missing environment variables
- Database connection errors
- Module import failures

### CORS Errors
Verify:
- Vercel domain added to CORS origins
- Backend redeployed after CORS update
- Browser cache cleared

### Frontend API Errors
Check:
- NEXT_PUBLIC_API_URL is set in Vercel
- Backend is awake (free tier sleeps)
- Backend health endpoint responds

---

## Continuous Deployment

Both platforms auto-deploy on git push:
- Push to GitHub
- Render rebuilds backend (5-10min)
- Vercel rebuilds frontend (2-3min)

---

## Post-Deployment Checklist

- [ ] Backend health check returns 200
- [ ] Frontend loads without errors
- [ ] Upload PDF works
- [ ] Preview displays products
- [ ] Export (CSV/Excel/JSON) works
- [ ] Compare shows fuzzy matches
- [ ] CORS configured for Vercel domain
- [ ] All environment variables set
- [ ] Logs accessible on both platforms

---

Estimated deployment time: 30-45 minutes

After deployment, application accessible at:
- Frontend: https://arc-pdf-tool.vercel.app
- Backend API: https://arc-pdf-api.onrender.com
