from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, and_
from sqlalchemy.types import DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, date
import os

Base = declarative_base()

class Manufacturer(Base):
    """Manufacturer information"""
    __tablename__ = 'manufacturers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    price_books = relationship("PriceBook", back_populates="manufacturer")
    product_families = relationship("ProductFamily", back_populates="manufacturer")
    finishes = relationship("Finish", back_populates="manufacturer")

class PriceBook(Base):
    """Price book editions and metadata"""
    __tablename__ = 'price_books'
    
    id = Column(Integer, primary_key=True)
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.id'), nullable=False)
    edition = Column(String(100))
    effective_date = Column(Date)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(Text)
    file_size = Column(Integer)
    status = Column(String(50), default='processing')  # processing, completed, failed
    parsing_notes = Column(Text)
    
    # Relationships
    manufacturer = relationship("Manufacturer", back_populates="price_books")
    products = relationship("Product", back_populates="price_book")

class ProductFamily(Base):
    """Product families/categories"""
    __tablename__ = 'product_families'
    
    id = Column(Integer, primary_key=True)
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.id'), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    manufacturer = relationship("Manufacturer", back_populates="product_families")
    products = relationship("Product", back_populates="family")

class Product(Base):
    """Individual products/SKUs"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('product_families.id'))
    price_book_id = Column(Integer, ForeignKey('price_books.id'), nullable=False)
    sku = Column(String(100), nullable=False)
    model = Column(String(100))
    description = Column(Text)
    base_price = Column(DECIMAL(10, 2))
    effective_date = Column(Date)
    retired_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship("ProductFamily", back_populates="products")
    price_book = relationship("PriceBook", back_populates="products")
    options = relationship("ProductOption", back_populates="product")
    prices = relationship("ProductPrice", back_populates="product")

class Finish(Base):
    """Finish options and their codes"""
    __tablename__ = 'finishes'
    
    id = Column(Integer, primary_key=True)
    manufacturer_id = Column(Integer, ForeignKey('manufacturers.id'), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    bhma_code = Column(String(20))  # BHMA standard code
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    manufacturer = relationship("Manufacturer", back_populates="finishes")

class ProductOption(Base):
    """Product options, adders, and rules"""
    __tablename__ = 'product_options'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    option_type = Column(String(50), nullable=False)  # 'finish', 'size', 'preparation', 'net_add'
    option_code = Column(String(50))
    option_name = Column(String(255))
    adder_type = Column(String(20))  # 'net_add', 'percent', 'replace', 'multiply'
    adder_value = Column(DECIMAL(10, 2))
    requires_option = Column(String(50))  # Option that must be present
    excludes_option = Column(String(50))  # Option that cannot be present
    is_required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="options")

class ProductPrice(Base):
    """Price history and calculations"""
    __tablename__ = 'product_prices'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    base_price = Column(DECIMAL(10, 2), nullable=False)
    finish_adder = Column(DECIMAL(10, 2), default=0)
    size_adder = Column(DECIMAL(10, 2), default=0)
    option_adder = Column(DECIMAL(10, 2), default=0)
    preparation_adder = Column(DECIMAL(10, 2), default=0)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="prices")

class ChangeLog(Base):
    """Track changes between price book editions"""
    __tablename__ = 'change_logs'
    
    id = Column(Integer, primary_key=True)
    old_price_book_id = Column(Integer, ForeignKey('price_books.id'))
    new_price_book_id = Column(Integer, ForeignKey('price_books.id'), nullable=False)
    change_type = Column(String(50), nullable=False)  # 'price_change', 'new_product', 'retired_product', 'option_change'
    product_id = Column(Integer, ForeignKey('products.id'))
    old_value = Column(Text)
    new_value = Column(Text)
    change_percentage = Column(DECIMAL(5, 2))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    old_price_book = relationship("PriceBook", foreign_keys=[old_price_book_id])
    new_price_book = relationship("PriceBook", foreign_keys=[new_price_book_id])
    product = relationship("Product")

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or 'sqlite:///price_books.db'
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def init_database(self):
        """Initialize database with sample data"""
        self.create_tables()
        
        session = self.get_session()
        try:
            # Check if manufacturers already exist
            if not session.query(Manufacturer).first():
                # Add sample manufacturers
                hager = Manufacturer(name='Hager', code='HAG')
                select_hinges = Manufacturer(name='SELECT Hinges', code='SEL')
                
                session.add(hager)
                session.add(select_hinges)
                session.flush()  # Get the IDs
                
                # Add BHMA finishes for Hager
                finishes_data = [
                    ('US3', 'Satin Chrome', 'US3'),
                    ('US4', 'Bright Chrome', 'US4'),
                    ('US10B', 'Satin Bronze', 'US10B'),
                    ('US15', 'Satin Brass', 'US15'),
                    ('US26D', 'Oil Rubbed Bronze', 'US26D'),
                    ('US32D', 'Antique Brass', 'US32D'),
                    ('US33D', 'Antique Copper', 'US33D')
                ]
                
                for hager_finish in finishes_data:
                    finish = Finish(
                        manufacturer_id=hager.id,
                        code=hager_finish[0],
                        name=hager_finish[1],
                        bhma_code=hager_finish[2]
                    )
                    session.add(finish)
                
                # Add finishes for SELECT Hinges
                select_finishes_data = [
                    ('STD', 'Standard', 'STD'),
                    ('BLK', 'Black', 'BLK'),
                    ('BRZ', 'Bronze', 'BRZ')
                ]
                
                for select_finish in select_finishes_data:
                    finish = Finish(
                        manufacturer_id=select_hinges.id,
                        code=select_finish[0],
                        name=select_finish[1],
                        bhma_code=select_finish[2]
                    )
                    session.add(finish)
                
                session.commit()
                print("Database initialized with sample data")
        except Exception as e:
            session.rollback()
            print(f"Error initializing database: {e}")
        finally:
            session.close()
