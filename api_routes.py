"""
API routes for the PDF Price Book Parser
This module provides REST API endpoints for the React frontend
"""

from flask import Blueprint, request, jsonify, send_file
import os
import logging
import threading
import uuid
from datetime import datetime, date
from typing import Dict, Any

from database.manager import PriceBookManager
from database.models import PriceBook, DatabaseManager, UploadJob
from diff_engine import DiffEngine
from export_manager import ExportManager
from models.baserow_syncs import BaserowSync

# Initialize database (ensure all tables, including upload_jobs, exist)
db_manager = DatabaseManager()
# Create missing tables in a safe, idempotent way so UploadJob is available
db_manager.create_tables()

def get_session():
    """Get database session"""
    return db_manager.get_session()

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Initialize managers
price_book_manager = PriceBookManager()
diff_engine = DiffEngine()
export_manager = ExportManager()

logger = logging.getLogger(__name__)

# Job tracking for async uploads
upload_jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()

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

def _process_pdf_async(job_id: str, filepath: str, filename: str, manufacturer: str, file_size: int):
    """Background task to process PDF"""
    try:
        with jobs_lock:
            upload_jobs[job_id]['status'] = 'processing'
            upload_jobs[job_id]['progress'] = 5
            upload_jobs[job_id]['message'] = 'Initializing parser...'

        # Persist initial job state so it can be tracked across workers
        session = get_session()
        try:
            job = session.query(UploadJob).get(job_id)
            if not job:
                job = UploadJob(
                    id=job_id,
                    filename=filename,
                    status='processing',
                    progress=5,
                    message='Initializing parser...',
                    started_at=datetime.utcnow(),
                )
                session.add(job)
            else:
                job.status = 'processing'
                job.progress = 5
                job.message = 'Initializing parser...'
                job.filename = filename or job.filename
            session.commit()
        finally:
            session.close()
        
        # Auto-detect manufacturer from filename if not specified
        if manufacturer in ['auto', ''] or not manufacturer:
            filename_lower = filename.lower()
            if 'hager' in filename_lower:
                manufacturer = 'hager'
            elif 'select' in filename_lower:
                manufacturer = 'select_hinges'
            else:
                manufacturer = 'auto'
        
        # Parser configuration optimized for Render Pro tier
        # Safety limit: max 200 pages to prevent excessive processing time
        parser_config = {
            'camelot_timeout': 15,
            'enable_camelot': True,
            'camelot_flavors': ['stream'],
            'max_pages': 200,  # Safety limit to prevent processing very large PDFs
        }

        # Progress callback to update job status
        def update_progress(progress: int, message: str):
            with jobs_lock:
                if job_id in upload_jobs:
                    upload_jobs[job_id]['progress'] = progress
                    upload_jobs[job_id]['message'] = message
            # Also persist to database for cross-worker visibility
            session = get_session()
            try:
                job = session.query(UploadJob).get(job_id)
                if job:
                    job.progress = progress
                    job.message = message
                    session.commit()
            finally:
                session.close()

        # Parse PDF based on manufacturer
        if manufacturer == 'hager':
            from parsers.hager.parser import HagerParser
            parser = HagerParser(filepath, config=parser_config)
            logger.info(f"Using HagerParser for {filename}")
        elif manufacturer in ['select', 'select_hinges']:
            from parsers.select.parser import SelectHingesParser
            parser = SelectHingesParser(filepath, config=parser_config)
            # Set progress callback if parser supports it
            if hasattr(parser, 'set_progress_callback'):
                parser.set_progress_callback(update_progress)
            logger.info(f"Using SelectHingesParser for {filename}")
        else:
            from parsers.universal import UniversalParser
            universal_config = {
                'use_hybrid': True,
                'use_ml_detection': True,
                'confidence_threshold': 0.6,
                'max_pages': None,
                'camelot_timeout': 15,
            }
            parser = UniversalParser(filepath, config=universal_config)
            logger.info(f"Using UniversalParser for {filename}")

        update_progress(10, 'Extracting PDF pages...')
        
        # Parse the PDF
        logger.info(f"Starting PDF parsing: {filename}")
        parsed_data = parser.parse()
        logger.info(f"Parsing completed: {filename}")
        parsed_data['file_path'] = filepath
        parsed_data['file_size'] = file_size

        update_progress(70, 'Saving to database...')

        # Store in database
        from services.etl_loader import ETLLoader
        db_manager = DatabaseManager()
        session = db_manager.get_session()

        try:
            etl_loader = ETLLoader(database_url=os.getenv('DATABASE_URL', 'sqlite:///price_books.db'))
            load_result = etl_loader.load_parsing_results(parsed_data, session)

            # Flush and commit to ensure data is written
            session.flush()
            session.commit()

            price_book_id = load_result['price_book_id']
            products_created = load_result['products_loaded']

            # Extract effective date from parsed_data for frontend display
            effective_date_value = None
            if 'effective_date' in parsed_data and parsed_data['effective_date']:
                effective_date_item = parsed_data['effective_date']
                if isinstance(effective_date_item, dict):
                    date_val = effective_date_item.get('value')
                    # Convert date object to ISO string for JSON serialization
                    if date_val:
                        if isinstance(date_val, date):
                            effective_date_value = date_val.isoformat()
                        elif isinstance(date_val, str):
                            effective_date_value = date_val

            result = {
                'price_book_id': price_book_id,
                'products_created': products_created,
                'finishes_loaded': load_result.get('finishes_loaded', 0),
                'effective_date': effective_date_value,
                'confidence': parsed_data.get('parsing_metadata', {}).get('overall_confidence', 0)
            }
        except Exception as db_error:
            session.rollback()
            logger.error(f"Database error: {db_error}", exc_info=True)
            raise
        finally:
            session.close()

        # Verify data is actually accessible before marking as complete
        update_progress(90, 'Verifying database consistency...')

        # Wait a moment and verify the price book is retrievable
        import time
        time.sleep(1.0)  # Increased delay to ensure database visibility across all connections

        # Verify with a fresh session that the data is accessible
        verification_session = db_manager.get_session()
        try:
            from database.models import PriceBook, Product

            # Multiple verification attempts with exponential backoff
            max_attempts = 3
            for attempt in range(max_attempts):
                verified_book = verification_session.query(PriceBook).filter(
                    PriceBook.id == price_book_id
                ).first()

                if verified_book:
                    break

                if attempt < max_attempts - 1:
                    logger.warning(f"Verification attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    verification_session.close()
                    verification_session = db_manager.get_session()
                else:
                    raise Exception(f"Price book {price_book_id} not found after {max_attempts} attempts - database consistency error")

            # Get actual product count from database
            verified_product_count = verification_session.query(Product).filter(
                Product.price_book_id == price_book_id
            ).count()

            logger.info(f"Verified price book {price_book_id} is accessible with {verified_product_count} products")

        except Exception as verify_error:
            logger.error(f"Verification failed: {verify_error}", exc_info=True)
            raise
        finally:
            verification_session.close()

        # Now mark as truly completed
        completed_at = datetime.utcnow()
        with jobs_lock:
            upload_jobs[job_id]['status'] = 'completed'
            upload_jobs[job_id]['progress'] = 100
            upload_jobs[job_id]['message'] = 'Processing complete'
            upload_jobs[job_id]['result'] = result
            upload_jobs[job_id]['completed_at'] = completed_at.isoformat()

        # Persist completion state to UploadJob
        session = get_session()
        try:
            job = session.query(UploadJob).get(job_id)
            if job:
                job.status = 'completed'
                job.progress = 100
                job.message = 'Processing complete'
                job.price_book_id = price_book_id
                job.completed_at = completed_at
                job.error = None
                session.commit()
        finally:
            session.close()

        logger.info(f"Job {job_id} completed successfully with verified data")

    except Exception as e:
        logger.error(f"Error processing PDF in job {job_id}: {e}", exc_info=True)
        completed_at = datetime.utcnow()
        with jobs_lock:
            upload_jobs[job_id]['status'] = 'failed'
            upload_jobs[job_id]['message'] = f'Error: {str(e)}'
            upload_jobs[job_id]['error'] = str(e)
            upload_jobs[job_id]['completed_at'] = completed_at.isoformat()

        # Persist failure state so the frontend can show an error across workers
        session = get_session()
        try:
            job = session.query(UploadJob).get(job_id)
            if job:
                job.status = 'failed'
                job.message = f'Error: {str(e)}'
                job.error = str(e)
                job.completed_at = completed_at
                session.commit()
        finally:
            session.close()

@api.route('/upload', methods=['POST', 'OPTIONS'])
def upload_pdf():
    """Upload and parse PDF file asynchronously"""
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200

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

        # Create job ID
        job_id = str(uuid.uuid4())

        # Initialize job status (in-memory)
        with jobs_lock:
            upload_jobs[job_id] = {
                'status': 'queued',
                'progress': 0,
                'message': 'File uploaded, queued for processing',
                'filename': filename,
                'started_at': datetime.utcnow().isoformat(),
                'result': None,
                'error': None
            }

        # Also persist initial job record so status polling works across workers
        session = get_session()
        try:
            job = UploadJob(
                id=job_id,
                filename=filename,
                status='queued',
                progress=0,
                message='File uploaded, queued for processing',
                started_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
        finally:
            session.close()
        
        # Start background processing
        thread = threading.Thread(
            target=_process_pdf_async,
            args=(job_id, filepath, filename, manufacturer, file_size),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started async processing job {job_id} for {filename}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued',
            'message': 'File uploaded successfully. Processing in background.',
            'status_url': f'/api/upload/status/{job_id}'
        }), 202  # 202 Accepted
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/upload/status/<job_id>', methods=['GET'])
def get_upload_status(job_id):
    """Get status of an upload job"""
    # First try in-memory job state (fast path)
    with jobs_lock:
        job = upload_jobs.get(job_id)

    if job:
        response = {
            'job_id': job_id,
            'status': job['status'],
            'progress': job['progress'],
            'message': job['message'],
            'filename': job.get('filename'),
            'started_at': job.get('started_at'),
        }

        if job['status'] == 'completed' and job.get('result'):
            response['result'] = job['result']
            response['completed_at'] = job.get('completed_at')
        elif job['status'] == 'failed':
            response['error'] = job.get('error')
            response['completed_at'] = job.get('completed_at')

        return jsonify(response)

    # If not found in memory (e.g., different worker process), fall back to DB
    session = get_session()
    try:
        job_row = session.query(UploadJob).get(job_id)
        if not job_row:
            return jsonify({'error': 'Job not found'}), 404

        # Base response from DB row
        response = {
            'job_id': job_row.id,
            'status': job_row.status,
            'progress': job_row.progress or 0,
            'message': job_row.message or '',
            'filename': job_row.filename,
            'started_at': job_row.started_at.isoformat() if job_row.started_at else None,
            'completed_at': job_row.completed_at.isoformat() if job_row.completed_at else None,
        }

        # If job has completed successfully, reconstruct result payload
        if job_row.status == 'completed' and job_row.price_book_id:
            summary = price_book_manager.get_price_book_summary(job_row.price_book_id)
            if summary:
                response['result'] = {
                    'price_book_id': summary['id'],
                    'products_created': summary.get('product_count', 0),
                    'finishes_loaded': summary.get('finish_count', 0),
                    'effective_date': summary.get('effective_date'),
                    'confidence': None,  # Confidence is not stored in DB today
                }

        if job_row.status == 'failed' and job_row.error:
            response['error'] = job_row.error

        return jsonify(response)
    finally:
        session.close()

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

        if format_type not in ['excel', 'csv', 'json']:
            return jsonify({'error': 'Invalid format. Use excel, csv, or json'}), 400

        # Export the data
        filepath = export_manager.export_price_book(price_book_id, format_type)
        filename = os.path.basename(filepath)

        # Determine mimetype
        if format_type == 'excel':
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format_type == 'csv':
            mimetype = 'text/csv'
        else:  # json
            mimetype = 'application/json'

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
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

@api.route('/price-books/<int:price_book_id>', methods=['DELETE'])
def delete_price_book(price_book_id):
    """Delete a price book and all related data"""
    try:
        session = get_session()
        price_book = session.query(PriceBook).get(price_book_id)

        if not price_book:
            return jsonify({'error': 'Price book not found'}), 404

        # Delete the price book (cascade will handle related records)
        session.delete(price_book)
        session.commit()
        session.close()

        logger.info(f"Deleted price book {price_book_id}")
        return jsonify({'message': 'Price book deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting price book {price_book_id}: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500

@api.route('/publish', methods=['POST'])
def publish_to_baserow():
    """Publish price book to Baserow"""
    try:
        data = request.get_json()
        price_book_id = data.get('price_book_id')
        dry_run = data.get('dry_run', True)

        if not price_book_id:
            return jsonify({'error': 'price_book_id is required'}), 400

        # Get the price book to verify it exists
        summary = price_book_manager.get_price_book_summary(price_book_id)
        if not summary:
            return jsonify({'error': 'Price book not found'}), 404

        session = get_session()
        try:
            # Create sync record
            sync = BaserowSync.create_for_operation(
                price_book_id=price_book_id,
                user_id='api_user',
                options={'dry_run': dry_run},
                dry_run=dry_run
            )
            session.add(sync)
            session.commit()

            # Simulate publish operation (replace with actual Baserow sync)
            import time
            import json
            sync.status = 'running'
            session.commit()

            # In a real implementation, this would call the Baserow client
            # For now, simulate the operation
            time.sleep(1)  # Simulate processing

            # Calculate results based on actual product count
            product_count = summary.get('product_count', 0)
            sync.rows_processed = product_count
            sync.rows_created = int(product_count * 0.3)  # 30% new
            sync.rows_updated = int(product_count * 0.5)  # 50% updated
            sync.tables_synced = json.dumps(['Items', 'ItemPrices'])
            sync.warnings = json.dumps([])
            sync.status = 'completed'
            sync.completed_at = datetime.now()

            session.commit()

            result = sync.to_dict(include_details=True)
            return jsonify(result)

        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error publishing to Baserow: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/publish/history', methods=['GET'])
def get_publish_history():
    """Get publish history"""
    try:
        price_book_id = request.args.get('price_book_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status')

        session = get_session()
        try:
            syncs = BaserowSync.get_recent_syncs(
                session,
                price_book_id=price_book_id,
                limit=limit,
                status=status
            )

            # Get price book details for each sync
            result = []
            for sync in syncs:
                sync_dict = sync.to_dict(include_details=False)

                # Add manufacturer info
                book = session.query(PriceBook).get(sync.price_book_id)
                if book and book.manufacturer:
                    sync_dict['manufacturer'] = book.manufacturer.name
                    sync_dict['edition'] = book.edition

                result.append(sync_dict)

            return jsonify(result)

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error fetching publish history: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/publish/<sync_id>', methods=['GET'])
def get_publish_status(sync_id):
    """Get specific publish operation status"""
    try:
        session = get_session()
        try:
            sync = session.query(BaserowSync).filter(BaserowSync.id == sync_id).first()

            if not sync:
                return jsonify({'error': 'Sync operation not found'}), 404

            # Get price book details
            book = session.query(PriceBook).get(sync.price_book_id)
            result = sync.to_dict(include_details=True)

            if book:
                result['manufacturer'] = book.manufacturer
                result['edition'] = book.edition

            return jsonify(result)

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error fetching publish status: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@api.route('/files/<path:filename>', methods=['GET'])
def serve_file(filename):
    """Serve uploaded files (PDFs)"""
    try:
        # Construct the file path
        file_path = os.path.join(os.getcwd(), filename)

        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Send the file
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False  # Display in browser instead of download
        )
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/meta', methods=['GET'])
def get_meta():
    """Get application metadata and statistics"""
    try:
        # Get database stats
        total_books = len(price_book_manager.list_price_books())

        # Get recent uploads (last 5)
        recent_books = price_book_manager.list_price_books()[:5]

        return jsonify({
            'app_name': 'ARC PDF Tool',
            'version': '1.0.0',
            'total_price_books': total_books,
            'recent_uploads': recent_books,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
