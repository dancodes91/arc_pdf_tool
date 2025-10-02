import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from fuzzywuzzy import fuzz, process
    RAPIDFUZZ_AVAILABLE = False
import pandas as pd

from database.models import DatabaseManager, Product, PriceBook, ChangeLog, ProductPrice
from database.manager import PriceBookManager

class DiffEngine:
    """Engine for comparing price book editions and generating change logs"""
    
    def __init__(self, database_url: str = None):
        self.db_manager = DatabaseManager(database_url)
        self.price_book_manager = PriceBookManager(database_url)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    def compare_price_books(self, old_price_book_id: int, new_price_book_id: int) -> Dict[str, Any]:
        """Compare two price book editions and generate change log"""
        session = self.get_session()
        try:
            # Get price books
            old_book = session.query(PriceBook).filter(PriceBook.id == old_price_book_id).first()
            new_book = session.query(PriceBook).filter(PriceBook.id == new_price_book_id).first()
            
            if not old_book or not new_book:
                raise ValueError("One or both price books not found")
            
            # Get products from both books
            old_products = self._get_products_with_prices(session, old_price_book_id)
            new_products = self._get_products_with_prices(session, new_price_book_id)
            
            # Generate change log
            changes = self._generate_change_log(session, old_book, new_book, old_products, new_products)
            
            # Calculate summary statistics
            summary = self._calculate_summary_stats(changes)
            
            result = {
                'old_price_book_id': old_price_book_id,
                'new_price_book_id': new_price_book_id,
                'old_edition': old_book.edition,
                'new_edition': new_book.edition,
                'changes': changes,
                'summary': summary,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Generated change log: {summary}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error comparing price books: {e}")
            raise
        finally:
            session.close()
    
    def _get_products_with_prices(self, session: Session, price_book_id: int) -> List[Dict[str, Any]]:
        """Get products with their current prices"""
        products = session.query(Product).filter(
            Product.price_book_id == price_book_id
        ).all()
        
        result = []
        for product in products:
            # Get latest price
            latest_price = session.query(ProductPrice).filter(
                ProductPrice.product_id == product.id
            ).order_by(ProductPrice.effective_date.desc()).first()
            
            result.append({
                'id': product.id,
                'sku': product.sku,
                'model': product.model,
                'description': product.description,
                'base_price': float(product.base_price) if product.base_price else None,
                'total_price': float(latest_price.total_price) if latest_price else None,
                'effective_date': product.effective_date,
                'is_active': product.is_active
            })
        
        return result
    
    def _generate_change_log(self, session: Session, old_book: PriceBook, new_book: PriceBook, 
                           old_products: List[Dict], new_products: List[Dict]) -> List[Dict[str, Any]]:
        """Generate detailed change log"""
        changes = []
        
        # Create lookup dictionaries
        old_products_by_sku = {p['sku']: p for p in old_products}
        new_products_by_sku = {p['sku']: p for p in new_products}
        
        # Find new products (will be filtered after fuzzy matching)
        new_skus = set(new_products_by_sku.keys()) - set(old_products_by_sku.keys())
        
        # Find retired products (but check for fuzzy matches first)
        retired_skus = set(old_products_by_sku.keys()) - set(new_products_by_sku.keys())

        # Try fuzzy matching for potentially renamed products
        fuzzy_matched = set()
        for old_sku in list(retired_skus):
            old_product = old_products_by_sku[old_sku]

            # Try to find fuzzy match in new products
            best_match = None
            best_score = 0

            for new_sku in new_skus:
                new_product = new_products_by_sku[new_sku]

                # Calculate fuzzy similarity
                sku_score = fuzz.ratio(old_sku, new_sku)
                desc_score = fuzz.ratio(old_product['description'] or '', new_product['description'] or '')
                model_score = fuzz.ratio(old_product['model'] or '', new_product['model'] or '')

                # Combined score
                combined_score = (sku_score * 0.5 + desc_score * 0.3 + model_score * 0.2)

                if combined_score > best_score and combined_score > 70:  # Threshold
                    best_score = combined_score
                    best_match = (new_sku, new_product, combined_score)

            # If good fuzzy match found, treat as rename
            if best_match:
                new_sku, new_product, score = best_match
                fuzzy_matched.add(old_sku)
                fuzzy_matched.add(new_sku)

                change = self._create_change_log_entry(
                    session, old_book.id, new_book.id, new_product['id'],
                    'fuzzy_match', old_sku, new_sku,
                    f"Product likely renamed: {old_sku} → {new_sku} (similarity: {score:.0f}%)"
                )
                changes.append(change)

        # Remove fuzzy matched items from new/retired sets
        retired_skus = retired_skus - fuzzy_matched
        new_skus = new_skus - fuzzy_matched

        # Now mark truly retired products
        for sku in retired_skus:
            product = old_products_by_sku[sku]
            change = self._create_change_log_entry(
                session, old_book.id, new_book.id, product['id'],
                'retired_product', product['sku'], None,
                f"Product retired: {product['sku']} - {product['description']}"
            )
            changes.append(change)

        # Mark truly new products (after fuzzy matching)
        for sku in new_skus:
            product = new_products_by_sku[sku]
            change = self._create_change_log_entry(
                session, old_book.id, new_book.id, product['id'],
                'new_product', None, product['sku'],
                f"New product added: {product['sku']} - {product['description']}"
            )
            changes.append(change)

        # Find price changes and updates
        common_skus = set(old_products_by_sku.keys()) & set(new_products_by_sku.keys())
        for sku in common_skus:
            old_product = old_products_by_sku[sku]
            new_product = new_products_by_sku[sku]
            
            # Check for price changes
            if old_product['base_price'] != new_product['base_price']:
                old_price = old_product['base_price']
                new_price = new_product['base_price']
                
                if old_price and new_price:
                    change_percentage = ((new_price - old_price) / old_price) * 100
                    change = self._create_change_log_entry(
                        session, old_book.id, new_book.id, new_product['id'],
                        'price_change', str(old_price), str(new_price),
                        f"Price changed from ${old_price:.2f} to ${new_price:.2f} ({change_percentage:+.1f}%)",
                        change_percentage
                    )
                    changes.append(change)
            
            # Check for description changes
            if old_product['description'] != new_product['description']:
                change = self._create_change_log_entry(
                    session, old_book.id, new_book.id, new_product['id'],
                    'description_change', old_product['description'], new_product['description'],
                    f"Description updated for {sku}"
                )
                changes.append(change)
            
            # Check for status changes
            if old_product['is_active'] != new_product['is_active']:
                status = "activated" if new_product['is_active'] else "deactivated"
                change = self._create_change_log_entry(
                    session, old_book.id, new_book.id, new_product['id'],
                    'status_change', str(old_product['is_active']), str(new_product['is_active']),
                    f"Product {status}: {sku}"
                )
                changes.append(change)
        
        # Find fuzzy matches for similar products
        self._find_fuzzy_matches(session, old_book, new_book, old_products, new_products, changes)
        
        return changes
    
    def _create_change_log_entry(self, session: Session, old_book_id: int, new_book_id: int,
                               product_id: int, change_type: str, old_value: str, new_value: str,
                               description: str, change_percentage: float = None) -> Dict[str, Any]:
        """Create a change log entry"""
        change_log = ChangeLog(
            old_price_book_id=old_book_id,
            new_price_book_id=new_book_id,
            product_id=product_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            change_percentage=change_percentage,
            description=description
        )
        session.add(change_log)
        
        return {
            'id': change_log.id,
            'change_type': change_type,
            'product_id': product_id,
            'old_value': old_value,
            'new_value': new_value,
            'change_percentage': change_percentage,
            'description': description
        }
    
    def _find_fuzzy_matches(self, session: Session, old_book: PriceBook, new_book: PriceBook,
                          old_products: List[Dict], new_products: List[Dict], changes: List[Dict]):
        """Find potential matches using fuzzy string matching"""
        # This is a simplified version - in production, you'd want more sophisticated matching
        for old_product in old_products:
            if old_product['sku'] in [p['sku'] for p in new_products]:
                continue  # Already matched exactly
            
            # Find best fuzzy match
            best_match = None
            best_score = 0
            
            for new_product in new_products:
                if new_product['sku'] in [p['sku'] for p in old_products]:
                    continue  # Already matched
                
                # Calculate similarity score
                sku_score = fuzz.ratio(old_product['sku'], new_product['sku'])
                desc_score = fuzz.ratio(old_product['description'], new_product['description'])
                combined_score = (sku_score + desc_score) / 2
                
                if combined_score > best_score and combined_score > 70:  # Threshold for fuzzy matching
                    best_score = combined_score
                    best_match = new_product
            
            if best_match:
                change = self._create_change_log_entry(
                    session, old_book.id, new_book.id, best_match['id'],
                    'fuzzy_match', old_product['sku'], best_match['sku'],
                    f"Potential match: {old_product['sku']} -> {best_match['sku']} (similarity: {best_score:.1f}%)"
                )
                changes.append(change)
    
    def _calculate_summary_stats(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from changes"""
        change_types = {}
        price_changes = []
        
        for change in changes:
            change_type = change['change_type']
            change_types[change_type] = change_types.get(change_type, 0) + 1
            
            if change_type == 'price_change' and change.get('change_percentage'):
                price_changes.append(change['change_percentage'])
        
        summary = {
            'total_changes': len(changes),
            'change_types': change_types,
            'new_products': change_types.get('new_product', 0),
            'retired_products': change_types.get('retired_product', 0),
            'price_changes': change_types.get('price_change', 0),
            'description_changes': change_types.get('description_change', 0),
            'status_changes': change_types.get('status_change', 0),
            'fuzzy_matches': change_types.get('fuzzy_match', 0)
        }
        
        if price_changes:
            summary['average_price_change'] = sum(price_changes) / len(price_changes)
            summary['max_price_increase'] = max(price_changes)
            summary['max_price_decrease'] = min(price_changes)
        
        return summary
    
    def get_change_log(self, old_price_book_id: int, new_price_book_id: int) -> List[Dict[str, Any]]:
        """Get existing change log between two price books"""
        session = self.get_session()
        try:
            change_logs = session.query(ChangeLog).filter(
                and_(
                    ChangeLog.old_price_book_id == old_price_book_id,
                    ChangeLog.new_price_book_id == new_price_book_id
                )
            ).order_by(ChangeLog.created_at.desc()).all()
            
            return [{
                'id': cl.id,
                'change_type': cl.change_type,
                'product_id': cl.product_id,
                'old_value': cl.old_value,
                'new_value': cl.new_value,
                'change_percentage': float(cl.change_percentage) if cl.change_percentage else None,
                'description': cl.description,
                'created_at': cl.created_at.isoformat()
            } for cl in change_logs]
            
        finally:
            session.close()
    
    def approve_changes(self, change_log_ids: List[int]) -> bool:
        """Approve specific changes (mark for application)"""
        session = self.get_session()
        try:
            # This would implement the approval workflow
            # For now, just mark changes as approved
            changes = session.query(ChangeLog).filter(ChangeLog.id.in_(change_log_ids)).all()
            
            for change in changes:
                # In a real implementation, you'd have an 'approved' field
                # and logic to apply the changes
                pass
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error approving changes: {e}")
            return False
        finally:
            session.close()
    
    def export_change_log(self, old_price_book_id: int, new_price_book_id: int, 
                         format: str = 'excel') -> str:
        """Export change log to file"""
        changes = self.get_change_log(old_price_book_id, new_price_book_id)
        
        if not changes:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(changes)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"change_log_{old_price_book_id}_to_{new_price_book_id}_{timestamp}"
        
        if format.lower() == 'excel':
            filepath = f"exports/{filename}.xlsx"
            df.to_excel(filepath, index=False)
        elif format.lower() == 'csv':
            filepath = f"exports/{filename}.csv"
            df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return filepath
