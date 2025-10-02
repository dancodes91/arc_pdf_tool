# Quick Start Guide - Running the Web UI

## Prerequisites
- Python 3.11+ installed
- Node.js 18+ installed
- UV package manager: `pip install uv`

## Start Backend (Terminal 1)
```bash
uv run python app.py
# Opens on http://127.0.0.1:5000
```

## Start Frontend (Terminal 2)
```bash
cd frontend
npm install  # First time only
npm run dev
# Opens on http://localhost:3000
```

## Access the UI
Open browser: **http://localhost:3000**

### Pages Available:
- `/` - Dashboard
- `/upload` - Upload PDFs
- `/preview/[id]` - View parsed products
- `/compare` - Compare price books (NEW!)

## Features Working
- ✅ Upload & Parse PDFs
- ✅ Export (CSV, Excel, JSON)
- ✅ Preview with confidence scores
- ✅ Compare with fuzzy matching
