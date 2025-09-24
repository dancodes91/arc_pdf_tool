#!/usr/bin/env python3
"""
PDF Price Book Parser - Main Application Runner

This script initializes and runs the PDF Price Book Parser application.
It handles database initialization, configuration, and starts the Flask server.
"""

import os
import sys
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, price_book_manager
from config import Config

def setup_logging():
    """Configure logging for the application"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def check_dependencies():
    """Check if all required dependencies are available"""
    required_packages = [
        'flask', 'pandas', 'openpyxl', 'pdfplumber', 
        'camelot', 'sqlalchemy', 'fuzzywuzzy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nPlease install missing packages with:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def initialize_application():
    """Initialize the application and database"""
    try:
        print("🚀 Initializing PDF Price Book Parser...")
        
        # Check dependencies
        if not check_dependencies():
            return False
        
        # Initialize database
        print("📊 Initializing database...")
        price_book_manager.initialize_database()
        print("✅ Database initialized successfully")
        
        # Create required directories
        directories = ['uploads', 'exports', 'logs', 'static/css', 'static/js', 'templates']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print("✅ Application initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing application: {e}")
        return False

def print_startup_info():
    """Print startup information"""
    print("\n" + "="*60)
    print("🔧 PDF Price Book Parser")
    print("="*60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: http://localhost:5000")
    print(f"📁 Upload Directory: {Config.UPLOAD_FOLDER}")
    print(f"💾 Database: {Config.DATABASE_URL}")
    print("="*60)
    print("\n📋 Features:")
    print("   • PDF parsing with OCR fallback")
    print("   • Hager and SELECT Hinges support")
    print("   • Price book comparison and diff engine")
    print("   • Excel/CSV export functionality")
    print("   • Modern web interface")
    print("\n🎯 Supported Manufacturers:")
    for key, manufacturer in Config.MANUFACTURERS.items():
        print(f"   • {manufacturer['name']} ({manufacturer['code']})")
    print("\n" + "="*60)

def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize application
        if not initialize_application():
            sys.exit(1)
        
        # Print startup information
        print_startup_info()
        
        # Start Flask application
        logger.info("Starting Flask application")
        app.run(
            debug=Config.DEBUG if hasattr(Config, 'DEBUG') else False,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
        logger.info("Application stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
