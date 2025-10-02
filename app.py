from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_cors import CORS
import os
import logging
from werkzeug.utils import secure_filename
from datetime import datetime
import json

from config import Config
from database.manager import PriceBookManager
from diff_engine import DiffEngine
from parsers import HagerParser, SelectHingesParser
from export_manager import ExportManager
from api_routes import api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
Config.init_app(app)
CORS(app, origins=['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002', 'http://127.0.0.1:3000', 'http://127.0.0.1:3001', 'http://127.0.0.1:3002'])

# Register API blueprint
app.register_blueprint(api)

# Initialize managers
price_book_manager = PriceBookManager()
diff_engine = DiffEngine()
export_manager = ExportManager()

# Ensure required directories exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('exports', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main dashboard"""
    try:
        price_books = price_book_manager.list_price_books()
        return render_template('dashboard.html', price_books=price_books)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', price_books=[])

@app.route('/upload', methods=['GET', 'POST'])
def upload_pdf():
    """Upload PDF file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        manufacturer = request.form.get('manufacturer', '').lower()
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Save file
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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
                logger.info(f"Parsing {filename} with enhanced parser")
                parsed_data = parser.parse()

                # Extract metadata for logging and user feedback
                parsing_metadata = parsed_data.get('parsing_metadata', {})
                overall_confidence = parsing_metadata.get('overall_confidence', 0)
                total_products = parsed_data.get('summary', {}).get('total_products', 0)

                # Check confidence and warn user
                if overall_confidence < 0.7:
                    flash(f'Warning: Parsing confidence is {overall_confidence:.1%}. Manual review recommended.', 'warning')

                logger.info(f"Parsed {total_products} products with {overall_confidence:.1%} confidence")

                # Add file metadata to parsed data
                parsed_data['file_path'] = filepath
                parsed_data['file_size'] = file_size

                # Store in database using ETL loader
                from services.etl_loader import ETLLoader
                from database.models import DatabaseManager

                db_manager = DatabaseManager()
                session = db_manager.get_session()

                try:
                    etl_loader = ETLLoader(database_url=Config.DATABASE_URL)
                    load_result = etl_loader.load_parsing_results(parsed_data, session)

                    price_book_id = load_result['price_book_id']
                    products_created = load_result['products_loaded']

                    session.commit()
                    result = {'price_book_id': price_book_id, 'products_created': products_created}
                except Exception as db_error:
                    session.rollback()
                    logger.error(f"Database error: {db_error}", exc_info=True)
                    raise
                finally:
                    session.close()
                
                flash(f'Successfully uploaded and parsed {filename}. Found {result["products_created"]} products.', 'success')
                return redirect(url_for('preview', price_book_id=result['price_book_id']))
                
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload a PDF file.', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/preview/<int:price_book_id>')
def preview(price_book_id):
    """Preview parsed data"""
    try:
        summary = price_book_manager.get_price_book_summary(price_book_id)
        products = price_book_manager.get_products_by_price_book(price_book_id, limit=50)
        
        return render_template('preview.html', 
                             summary=summary, 
                             products=products,
                             price_book_id=price_book_id)
    except Exception as e:
        logger.error(f"Error loading preview: {e}")
        flash('Error loading preview', 'error')
        return redirect(url_for('index'))

@app.route('/compare')
def compare():
    """Compare price books"""
    try:
        price_books = price_book_manager.list_price_books()
        return render_template('compare.html', price_books=price_books)
    except Exception as e:
        logger.error(f"Error loading compare page: {e}")
        flash('Error loading compare page', 'error')
        return redirect(url_for('index'))

@app.route('/api/compare', methods=['POST'])
def api_compare():
    """API endpoint for comparing price books"""
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

@app.route('/export/<int:price_book_id>')
def export(price_book_id):
    """Export price book data"""
    try:
        format_type = request.args.get('format', 'excel')
        
        if format_type == 'excel':
            return export_to_excel(price_book_id)
        elif format_type == 'csv':
            return export_to_csv(price_book_id)
        else:
            flash('Invalid export format', 'error')
            return redirect(url_for('preview', price_book_id=price_book_id))
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        flash('Error exporting data', 'error')
        return redirect(url_for('preview', price_book_id=price_book_id))

def export_to_excel(price_book_id):
    """Export to Excel format"""
    try:
        filepath = export_manager.export_price_book(price_book_id, format='excel')
        filename = os.path.basename(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error creating Excel export: {e}")
        raise

def export_to_csv(price_book_id):
    """Export to CSV format"""
    try:
        filepath = export_manager.export_price_book(price_book_id, format='csv')
        filename = os.path.basename(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error creating CSV export: {e}")
        raise

@app.route('/api/products/<int:price_book_id>')
def api_products(price_book_id):
    """API endpoint for getting products"""
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
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/healthz')
def healthz():
    """Health check endpoint - returns 200 if service is alive."""
    return jsonify({
        'status': 'healthy',
        'service': 'arc_pdf_tool',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/readyz')
def readyz():
    """Readiness check endpoint - returns 200 if service is ready to accept traffic."""
    checks = {
        'database': False,
        'filesystem': False
    }

    try:
        # Check database connection
        price_book_manager.list_price_books()
        checks['database'] = True
    except Exception as e:
        logger.warning(f"Database check failed: {e}")

    try:
        # Check filesystem access
        os.path.exists(app.config['UPLOAD_FOLDER'])
        checks['filesystem'] = True
    except Exception as e:
        logger.warning(f"Filesystem check failed: {e}")

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return jsonify({
        'status': 'ready' if all_ready else 'not_ready',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), status_code

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize database
    price_book_manager.initialize_database()
    
    # Run app
    app.run(debug=True, host='0.0.0.0', port=5000)
