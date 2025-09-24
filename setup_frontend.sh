#!/bin/bash

# PDF Price Book Parser - Frontend Setup Script

echo "🚀 Setting up PDF Price Book Parser Frontend"
echo "=============================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm version: $(npm -v)"

# Navigate to frontend directory
cd frontend

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Create .env.local file
echo "⚙️  Creating environment configuration..."
cat > .env.local << EOF
# PDF Price Book Parser - Frontend Environment
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_NAME="PDF Price Book Parser"
EOF

echo "✅ Environment configuration created"

# Check if Python backend is running
echo "🔍 Checking if Python backend is running..."
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ Python backend is running"
else
    echo "⚠️  Python backend is not running. Please start it with: python app.py"
    echo "   The frontend will still work, but API calls will fail."
fi

# Build the project to check for errors
echo "🔨 Building project to check for errors..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed. Please check the errors above."
    exit 1
fi

echo "✅ Build successful"

# Start the development server
echo "🎉 Setup complete! Starting development server..."
echo ""
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API should be running at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the development server"
echo ""

npm run dev
