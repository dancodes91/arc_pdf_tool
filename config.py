import os
from datetime import datetime

class Config:
    """Configuration settings for the PDF Price Book Parser"""
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///price_books.db')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # OCR Configuration
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', 'tesseract')
    OCR_LANGUAGE = 'eng'
    
    # Parsing Configuration
    MIN_TABLE_CONFIDENCE = 0.7
    MAX_PAGES_TO_PROCESS = 1000
    
    # Accuracy Requirements
    MIN_ROW_ACCURACY = 0.98
    MIN_NUMERIC_ACCURACY = 0.99
    
    # Supported Manufacturers
    MANUFACTURERS = {
        'hager': {
            'name': 'Hager',
            'code': 'HAG',
            'finish_codes': ['US3', 'US4', 'US10B', 'US15', 'US26D', 'US32D', 'US33D']
        },
        'select_hinges': {
            'name': 'SELECT Hinges',
            'code': 'SEL',
            'net_add_options': ['CTW', 'EPT', 'EMS', 'TIPIT', 'Hospital Tip', 'UL FR3']
        }
    }
    
    # BHMA Finish Standards
    BHMA_FINISHES = {
        'US3': 'Satin Chrome',
        'US4': 'Bright Chrome',
        'US10B': 'Satin Bronze',
        'US15': 'Satin Brass',
        'US26D': 'Oil Rubbed Bronze',
        'US32D': 'Antique Brass',
        'US33D': 'Antique Copper'
    }
    
    @staticmethod
    def init_app(app):
        """Initialize Flask app with configuration"""
        # Create upload directory if it doesn't exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Set Flask configuration
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
