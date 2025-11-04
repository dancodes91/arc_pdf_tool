# MySQL Deployment Guide

## Overview
This guide covers deploying the ARC PDF Tool with MySQL database instead of PostgreSQL.

---

## Database Options for Render

### Option 1: Render MySQL (Recommended)
**Status**: Render does not offer MySQL as a managed database service.

**Alternatives**:
- PlanetScale (MySQL-compatible, free tier available)
- AWS RDS MySQL
- Railway MySQL
- Self-hosted MySQL on Render

### Option 2: PlanetScale (Easiest)
Free tier with 5GB storage, 1 billion row reads/month.

### Option 3: Railway (Simple)
$5/month for MySQL with easy setup.

---

## Deployment Option A: Railway MySQL

### Step 1: Create MySQL Database on Railway

1. Go to https://railway.app and sign up/login
2. Click **"New Project"**
3. Click **"Add Service"** → **"Database"** → **"Add MySQL"**
4. Railway automatically creates the database
5. Click on the MySQL service → **"Connect"** tab
6. **Copy the connection string** (looks like: `mysql://user:pass@host:port/dbname`)

### Step 2: Update Render Backend Environment

1. Go to **Render Dashboard** → Your web service
2. Click **"Environment"**
3. Update `DATABASE_URL`:
   ```
   DATABASE_URL = [Paste Railway MySQL URL]
   ```
4. Save → Render will redeploy

### Step 3: Test Connection

```bash
curl https://arc-pdf-tool.onrender.com/api/health
```

Should return: `{"status":"healthy"}`

---

## Deployment Option B: PlanetScale (Serverless MySQL)

### Step 1: Create PlanetScale Database

1. Go to https://planetscale.com and sign up
2. Click **"Create a database"**
3. Configure:
   - Name: `arc-pdf-tool`
   - Region: Select nearest to Render
   - Plan: Free (Hobby)
4. Click **"Create database"**

### Step 2: Get Connection String

1. In PlanetScale dashboard, click **"Connect"**
2. Select **"General"** connection
3. Copy the connection string:
   ```
   mysql://user:password@host/arc_pdf_tool?sslmode=require
   ```

### Step 3: Update Render

1. Render Dashboard → Web service → Environment
2. Set `DATABASE_URL` to PlanetScale connection string
3. Save and redeploy

---

## Deployment Option C: AWS RDS MySQL

### Step 1: Create RDS Instance

1. AWS Console → RDS → **"Create database"**
2. Choose **MySQL**
3. Template: **Free tier** or **Production**
4. Settings:
   - DB instance identifier: `arc-pdf-db`
   - Master username: `arc_admin`
   - Master password: [Strong password]
5. Instance configuration:
   - db.t3.micro (free tier) or larger
6. Storage: 20GB SSD
7. Connectivity:
   - Public access: **Yes**
   - VPC security group: Create new
8. Database name: `arc_pdf_tool`
9. Create database

### Step 2: Configure Security Group

1. EC2 → Security Groups → Select your RDS security group
2. Inbound rules → Edit → Add rule:
   - Type: MySQL/Aurora
   - Port: 3306
   - Source: Anywhere (0.0.0.0/0) or Render IPs
3. Save

### Step 3: Get Connection String

Format:
```
mysql://arc_admin:YOUR_PASSWORD@your-db.region.rds.amazonaws.com:3306/arc_pdf_tool
```

### Step 4: Update Render

Set `DATABASE_URL` in Render environment to RDS connection string.

---

## Local Development with MySQL

### Option 1: Docker MySQL (Recommended)

```bash
# Start MySQL container
docker run -d \
  --name arc-mysql \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -e MYSQL_DATABASE=arc_pdf_tool \
  -e MYSQL_USER=arc_user \
  -e MYSQL_PASSWORD=arc_password \
  -p 3306:3306 \
  mysql:8.0

# Connection string
DATABASE_URL=mysql://arc_user:arc_password@localhost:3306/arc_pdf_tool
```

### Option 2: Install MySQL Locally

**Windows**:
1. Download MySQL Installer from https://dev.mysql.com/downloads/installer/
2. Run installer, select "Developer Default"
3. Create database:
   ```sql
   CREATE DATABASE arc_pdf_tool;
   CREATE USER 'arc_user'@'localhost' IDENTIFIED BY 'arc_password';
   GRANT ALL PRIVILEGES ON arc_pdf_tool.* TO 'arc_user'@'localhost';
   ```

**Mac**:
```bash
brew install mysql
brew services start mysql
mysql -u root -p
# Then run the CREATE DATABASE commands above
```

**Linux**:
```bash
sudo apt-get install mysql-server
sudo mysql_secure_installation
sudo mysql -u root -p
# Then run the CREATE DATABASE commands above
```

---

## Environment Variables

### Required for MySQL:

```bash
# Production (Railway/PlanetScale/RDS)
DATABASE_URL=mysql://user:password@host:3306/arc_pdf_tool

# Local Development
DATABASE_URL=mysql://arc_user:arc_password@localhost:3306/arc_pdf_tool

# Or use SQLite for quick local testing
DATABASE_URL=sqlite:///arc_pdf_tool.db
```

### Full Environment Configuration:

```bash
# Database
DATABASE_URL=mysql://user:password@host:3306/arc_pdf_tool

# Application
ENV=production
DEBUG=false
SECRET_KEY=[Generate with: openssl rand -hex 32]

# CORS
CORS_ORIGINS=https://arcpdftool.vercel.app,http://localhost:3000

# OCR
TESSERACT_CMD=/usr/bin/tesseract

# Optional: Redis
REDIS_URL=redis://redis:6379/0
```

---

## Running Database Migrations

After setting up MySQL:

```bash
# Install dependencies with MySQL driver
pip install -r requirements.txt
# OR with uv
uv sync

# Run migrations
alembic upgrade head
```

On Render, migrations run automatically if you add this to build command:
```bash
pip install -r requirements.txt && alembic upgrade head
```

---

## Verifying MySQL Setup

### 1. Check Connection

```bash
# From command line
mysql -h your-host -u your-user -p arc_pdf_tool
```

### 2. Check Tables Created

```sql
USE arc_pdf_tool;
SHOW TABLES;

-- Should show:
-- manufacturers
-- price_books
-- product_families
-- products
-- product_options
-- product_prices
-- finishes
-- change_logs
```

### 3. Test API Health

```bash
curl https://arc-pdf-tool.onrender.com/api/health
```

---

## Cost Comparison

| Option | Cost | Storage | Notes |
|--------|------|---------|-------|
| **Railway MySQL** | $5/month | 5GB | Easiest setup, automatic backups |
| **PlanetScale Free** | $0 | 5GB | Serverless, scales to zero |
| **PlanetScale Pro** | $29/month | 10GB | Production-ready |
| **AWS RDS Free Tier** | $0 (12 months) | 20GB | Then ~$15/month |
| **AWS RDS t3.micro** | ~$15/month | 20GB SSD | Production |

**Recommendation**: Start with **Railway** ($5/month) for simplicity, or **PlanetScale Free** for zero cost.

---

## Troubleshooting

### Error: "Access denied for user"
- Verify username and password in DATABASE_URL
- Check database user has correct permissions
- Ensure host allows remote connections

### Error: "Can't connect to MySQL server"
- Check security group/firewall allows port 3306
- Verify host URL is correct
- Ensure database is running

### Error: "Unknown database"
- Database name doesn't exist
- Create database first: `CREATE DATABASE arc_pdf_tool;`

### Error: "Client does not support authentication protocol"
- MySQL 8.0 uses caching_sha2_password
- Use older auth method or update mysqlclient version

### Migrations Fail
```bash
# Drop all tables and recreate
alembic downgrade base
alembic upgrade head
```

---

## Migration from PostgreSQL

If you already have data in PostgreSQL:

### Option 1: Export/Import

```bash
# Export from PostgreSQL
pg_dump -U user -d arc_pdf_tool > backup.sql

# Convert PostgreSQL syntax to MySQL (manual edits needed)
# Then import to MySQL
mysql -u user -p arc_pdf_tool < backup_mysql.sql
```

### Option 2: Use ETL Tool

Use tools like:
- pgloader
- AWS Database Migration Service
- Railway's migration tools

### Option 3: Start Fresh

Just run migrations on new MySQL database:
```bash
alembic upgrade head
```

Then re-upload PDFs through the UI.

---

## Production Checklist

- [ ] MySQL database created
- [ ] Connection string configured in Render
- [ ] Migrations run successfully
- [ ] Health endpoint responds
- [ ] Can upload PDF and parse
- [ ] Data persists after restart
- [ ] Backups configured
- [ ] Monitoring set up

---

## Support

For issues:
1. Check Render logs for database connection errors
2. Verify DATABASE_URL format is correct
3. Test MySQL connection with mysql CLI
4. Check security groups/firewall rules

---

**Recommended Quick Start**: Railway MySQL ($5/month) - simplest setup with automatic backups and monitoring.
