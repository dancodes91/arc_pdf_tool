import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fuzzywuzzy import fuzz, process
import pandas as pd

from .models import (
    DatabaseManager, Manufacturer, PriceBook, ProductFamily, Product, 
    Finish, ProductOption, ProductPrice, ChangeLog
)

class PriceBookManager:
    """Manager for price book operations and data normalization"""
    
    def __init__(self, database_url: str = None):
        self.db_manager = DatabaseManager(database_url)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def initialize_database(self):
        """Initialize database with tables and sample data"""
        self.db_manager.init_database()
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_manager.get_session()
    
    def normalize_and_store_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and store parsed data in database"""
        session = self.get_session()
        try:
            # Get or create manufacturer
            manufacturer = self._get_or_create_manufacturer(session, parsed_data['manufacturer'])
            
            # Create price book record
            price_book = self._create_price_book(session, manufacturer.id, parsed_data)
            
            # Process products
            products_created = self._process_products(session, price_book.id, parsed_data['products'])
            
            # Process finishes
            finishes_created = self._process_finishes(session, manufacturer.id, parsed_data.get('finishes', []))
            
            # Process options
            options_created = self._process_options(session, products_created, parsed_data.get('options', []))
            
            # Update price book status
            price_book.status = 'completed'
            price_book.parsing_notes = f"Processed {len(products_created)} products, {len(finishes_created)} finishes, {len(options_created)} options"
            
            session.commit()
            
            result = {
                'price_book_id': price_book.id,
                'manufacturer_id': manufacturer.id,
                'products_created': len(products_created),
                'finishes_created': len(finishes_created),
                'options_created': len(options_created),
                'status': 'success'
            }
            
            self.logger.info(f"Successfully stored data: {result}")
            return result
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing data: {e}")
            raise
        finally:
            session.close()
    
    def _get_or_create_manufacturer(self, session: Session, manufacturer_name: str) -> Manufacturer:
        """Get or create manufacturer"""
        manufacturer = session.query(Manufacturer).filter(
            func.lower(Manufacturer.name) == manufacturer_name.lower()
        ).first()
        
        if not manufacturer:
            # Get manufacturer code from config
            from config import Config
            manufacturer_code = Config.MANUFACTURERS.get(manufacturer_name.lower(), {}).get('code', manufacturer_name[:3].upper())
            
            manufacturer = Manufacturer(
                name=manufacturer_name.title(),
                code=manufacturer_code
            )
            session.add(manufacturer)
            session.flush()  # Get the ID
        
        return manufacturer
    
    def _create_price_book(self, session: Session, manufacturer_id: int, parsed_data: Dict[str, Any]) -> PriceBook:
        """Create price book record"""
        price_book = PriceBook(
            manufacturer_id=manufacturer_id,
            edition=parsed_data.get('edition', 'Unknown'),
            effective_date=self._parse_date(parsed_data.get('effective_date')),
            file_path=parsed_data.get('file_path', ''),
            file_size=parsed_data.get('file_size', 0),
            status='processing'
        )
        session.add(price_book)
        session.flush()
        return price_book
    
    def _process_products(self, session: Session, price_book_id: int, products_data: List[Dict[str, Any]]) -> List[Product]:
        """Process and store products"""
        created_products = []
        
        for product_data in products_data:
            try:
                # Get or create product family
                family = self._get_or_create_family(session, product_data)
                
                # Create product
                product = Product(
                    family_id=family.id if family else None,
                    price_book_id=price_book_id,
                    sku=product_data['sku'],
                    model=product_data.get('model', ''),
                    description=product_data.get('description', ''),
                    base_price=product_data.get('base_price'),
                    effective_date=self._parse_date(product_data.get('effective_date')),
                    is_active=product_data.get('is_active', True)
                )
                session.add(product)
                session.flush()
                
                # Create price record
                if product_data.get('base_price'):
                    price = ProductPrice(
                        product_id=product.id,
                        base_price=product_data['base_price'],
                        total_price=product_data['base_price'],
                        effective_date=self._parse_date(product_data.get('effective_date')) or date.today()
                    )
                    session.add(price)
                
                created_products.append(product)
                
            except Exception as e:
                self.logger.error(f"Error processing product {product_data.get('sku', 'Unknown')}: {e}")
                continue
        
        return created_products
    
    def _get_or_create_family(self, session: Session, product_data: Dict[str, Any]) -> Optional[ProductFamily]:
        """Get or create product family"""
        # Try to extract family from SKU or description
        family_name = self._extract_family_name(product_data)
        
        if not family_name:
            return None
        
        # Get manufacturer from price book
        price_book = session.query(PriceBook).filter(PriceBook.id == product_data.get('price_book_id')).first()
        if not price_book:
            return None
        
        family = session.query(ProductFamily).filter(
            and_(
                ProductFamily.manufacturer_id == price_book.manufacturer_id,
                func.lower(ProductFamily.name) == family_name.lower()
            )
        ).first()
        
        if not family:
            family = ProductFamily(
                manufacturer_id=price_book.manufacturer_id,
                name=family_name,
                category=self._categorize_family(family_name)
            )
            session.add(family)
            session.flush()
        
        return family
    
    def _extract_family_name(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Extract family name from product data"""
        sku = product_data.get('sku', '')
        description = product_data.get('description', '')
        
        # Try to extract from SKU patterns
        if sku:
            # Common patterns: BB1191 -> BB series, H3A -> H series
            if sku.startswith('BB'):
                return 'BB Series'
            elif sku.startswith('H'):
                return 'H Series'
            elif sku.startswith('S'):
                return 'S Series'
        
        # Try to extract from description
        if description:
            description_lower = description.lower()
            if 'hinge' in description_lower:
                return 'Hinges'
            elif 'lock' in description_lower:
                return 'Locks'
            elif 'handle' in description_lower:
                return 'Handles'
        
        return None
    
    def _categorize_family(self, family_name: str) -> str:
        """Categorize product family"""
        family_lower = family_name.lower()
        
        if 'hinge' in family_lower:
            return 'Hinges'
        elif 'lock' in family_lower:
            return 'Locks'
        elif 'handle' in family_lower:
            return 'Handles'
        elif 'series' in family_lower:
            return 'Hardware'
        else:
            return 'General'
    
    def _process_finishes(self, session: Session, manufacturer_id: int, finishes_data: List[Dict[str, Any]]) -> List[Finish]:
        """Process and store finishes"""
        created_finishes = []
        
        for finish_data in finishes_data:
            try:
                # Check if finish already exists
                existing_finish = session.query(Finish).filter(
                    and_(
                        Finish.manufacturer_id == manufacturer_id,
                        func.lower(Finish.code) == finish_data['code'].lower()
                    )
                ).first()
                
                if not existing_finish:
                    finish = Finish(
                        manufacturer_id=manufacturer_id,
                        code=finish_data['code'],
                        name=finish_data['name'],
                        bhma_code=finish_data.get('bhma_code', finish_data['code'])
                    )
                    session.add(finish)
                    created_finishes.append(finish)
                else:
                    created_finishes.append(existing_finish)
                    
            except Exception as e:
                self.logger.error(f"Error processing finish {finish_data.get('code', 'Unknown')}: {e}")
                continue
        
        return created_finishes
    
    def _process_options(self, session: Session, products: List[Product], options_data: List[Dict[str, Any]]) -> List[ProductOption]:
        """Process and store product options"""
        created_options = []
        
        for option_data in options_data:
            try:
                # Create option for all products (or specific products if specified)
                for product in products:
                    option = ProductOption(
                        product_id=product.id,
                        option_type=option_data['option_type'],
                        option_code=option_data.get('option_code'),
                        option_name=option_data['option_name'],
                        adder_type=option_data['adder_type'],
                        adder_value=option_data.get('adder_value'),
                        requires_option=','.join(option_data.get('requires_option', [])),
                        excludes_option=','.join(option_data.get('excludes_option', [])),
                        is_required=option_data.get('is_required', False)
                    )
                    session.add(option)
                    created_options.append(option)
                    
            except Exception as e:
                self.logger.error(f"Error processing option {option_data.get('option_name', 'Unknown')}: {e}")
                continue
        
        return created_options
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            date_formats = [
                '%m/%d/%Y',
                '%m-%d-%Y',
                '%Y-%m-%d',
                '%m/%d/%y',
                '%m-%d-%y'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(date_str), fmt).date()
                except ValueError:
                    continue
            
            # If no format works, return today
            return date.today()
            
        except Exception:
            return date.today()
    
    def get_price_book_summary(self, price_book_id: int) -> Dict[str, Any]:
        """Get summary of a price book"""
        session = self.get_session()
        try:
            price_book = session.query(PriceBook).filter(PriceBook.id == price_book_id).first()
            if not price_book:
                return {}
            
            product_count = session.query(Product).filter(Product.price_book_id == price_book_id).count()
            option_count = session.query(ProductOption).join(Product).filter(Product.price_book_id == price_book_id).count()
            
            return {
                'id': price_book.id,
                'manufacturer': price_book.manufacturer.name,
                'edition': price_book.edition,
                'effective_date': price_book.effective_date.isoformat() if price_book.effective_date else None,
                'upload_date': price_book.upload_date.isoformat(),
                'status': price_book.status,
                'product_count': product_count,
                'option_count': option_count,
                'file_path': price_book.file_path
            }
            
        finally:
            session.close()
    
    def list_price_books(self, manufacturer_id: int = None) -> List[Dict[str, Any]]:
        """List all price books"""
        session = self.get_session()
        try:
            query = session.query(PriceBook).join(Manufacturer)
            
            if manufacturer_id:
                query = query.filter(PriceBook.manufacturer_id == manufacturer_id)
            
            price_books = query.order_by(PriceBook.upload_date.desc()).all()
            
            return [self.get_price_book_summary(pb.id) for pb in price_books]
            
        finally:
            session.close()
    
    def get_products_by_price_book(self, price_book_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get products from a specific price book"""
        session = self.get_session()
        try:
            products = session.query(Product).filter(
                Product.price_book_id == price_book_id
            ).offset(offset).limit(limit).all()
            
            result = []
            for product in products:
                result.append({
                    'id': product.id,
                    'sku': product.sku,
                    'model': product.model,
                    'description': product.description,
                    'base_price': float(product.base_price) if product.base_price else None,
                    'effective_date': product.effective_date.isoformat() if product.effective_date else None,
                    'is_active': product.is_active,
                    'family': product.family.name if product.family else None
                })
            
            return result
            
        finally:
            session.close()
