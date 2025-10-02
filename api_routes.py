"""
API routes for the PDF Price Book Parser
This module provides REST API endpoints for the React frontend
"""

from flask import Blueprint, request, jsonify, send_file
import os
import logging
from datetime import datetime

from database.manager import PriceBookManager
from diff_engine import DiffEngine
from export_manager import ExportManager

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Initialize managers
price_book_manager = PriceBookManager()
diff_engine = DiffEngine()
export_manager = ExportManager()

logger = logging.getLogger(__name__)

@api.route('/price-books', methods=['GET'])
def get_price_books():
    """Get all price books"""
    try:
        price_books = price_book_manager.list_price_books()
        return jsonify(price_books)
    except Exception as e:
        logger.error(f"Error fetching price books: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/price-books/<int:price_book_id>', methods=['GET'])
def get_price_book(price_book_id):
    """Get specific price book details"""
    try:
        summary = price_book_manager.get_price_book_summary(price_book_id)
        if not summary:
            return jsonify({'error': 'Price book not found'}), 404
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error fetching price book {price_book_id}: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/products/<int:price_book_id>', methods=['GET'])
def get_products(price_book_id):
    """Get products for a specific price book"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        products = price_book_manager.get_products_by_price_book(
            price_book_id, 
            limit=per_page, 
            offset=offset
        )
        
        return jsonify({
            'products': products,
            'page': page,
            'per_page': per_page,
            'total': len(products)  # This should be improved with actual count
        })
    except Exception as e:
        logger.error(f"Error fetching products for price book {price_book_id}: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload and parse PDF file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        manufacturer = request.form.get('manufacturer', '').lower()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Save file
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Parse PDF based on manufacturer using enhanced parsers
        if manufacturer == 'hager':
            from parsers.hager.parser import HagerParser
            parser = HagerParser(filepath)
        elif manufacturer == 'select_hinges':
            from parsers.select.parser import SelectHingesParser
            parser = SelectHingesParser(filepath)
        else:
            # Try to auto-detect manufacturer
            from parsers.hager.parser import HagerParser
            parser = HagerParser(filepath)
            detected = parser.identify_manufacturer()
            if detected == 'select_hinges':
                from parsers.select.parser import SelectHingesParser
                parser = SelectHingesParser(filepath)

        # Parse the PDF with enhanced parser
        parsed_data = parser.parse()
        parsed_data['file_path'] = filepath
        parsed_data['file_size'] = file_size

        # Store in database using ETL loader
        from services.etl_loader import ETLLoader
        from database.models import DatabaseManager
        import os

        db_manager = DatabaseManager()
        session = db_manager.get_session()

        try:
            etl_loader = ETLLoader(database_url=os.getenv('DATABASE_URL', 'sqlite:///price_books.db'))
            load_result = etl_loader.load_parsing_results(parsed_data, session)
            session.commit()

            result = {
                'price_book_id': load_result['price_book_id'],
                'products_created': load_result['products_loaded'],
                'finishes_loaded': load_result.get('finishes_loaded', 0),
                'confidence': parsed_data.get('parsing_metadata', {}).get('overall_confidence', 0)
            }
        except Exception as db_error:
            session.rollback()
            logger.error(f"Database error: {db_error}", exc_info=True)
            raise
        finally:
            session.close()
        
        return jsonify({
            'success': True,
            'price_book_id': result['price_book_id'],
            'products_created': result['products_created'],
            'finishes_loaded': result['finishes_loaded'],
            'confidence': result['confidence'],
            'message': f'Successfully uploaded and parsed {filename}'
        })
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/compare', methods=['POST'])
def compare_price_books():
    """Compare two price books"""
    try:
        data = request.get_json()
        old_book_id = data.get('old_price_book_id')
        new_book_id = data.get('new_price_book_id')
        
        if not old_book_id or not new_book_id:
            return jsonify({'error': 'Both price book IDs are required'}), 400
        
        if old_book_id == new_book_id:
            return jsonify({'error': 'Cannot compare a price book with itself'}), 400
        
        # Generate comparison
        comparison = diff_engine.compare_price_books(old_book_id, new_book_id)
        return jsonify(comparison)
        
    except Exception as e:
        logger.error(f"Error comparing price books: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/export/<int:price_book_id>', methods=['GET'])
def export_price_book(price_book_id):
    """Export price book data"""
    try:
        format_type = request.args.get('format', 'excel')
        
        if format_type not in ['excel', 'csv']:
            return jsonify({'error': 'Invalid format. Use excel or csv'}), 400
        
        # Export the data
        filepath = export_manager.export_price_book(price_book_id, format_type)
        filename = os.path.basename(filepath)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if format_type == 'excel' else 'text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error exporting price book {price_book_id}: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/change-log/<int:old_id>/<int:new_id>', methods=['GET'])
def get_change_log(old_id, new_id):
    """Get change log between two price books"""
    try:
        changes = diff_engine.get_change_log(old_id, new_id)
        return jsonify(changes)
    except Exception as e:
        logger.error(f"Error fetching change log: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
