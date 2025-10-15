#!/usr/bin/env bash
# Render build script for MySQL client dependencies

set -o errexit

# Install system dependencies for mysqlclient
apt-get update
apt-get install -y pkg-config default-libmysqlclient-dev

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head || echo "Migrations skipped (database may not be accessible during build)"
