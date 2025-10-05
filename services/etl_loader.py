"""
ETL loader for parsed data into normalized database.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from database.models import (
    Manufacturer,
    PriceBook,
    ProductFamily,
    Product,
    Finish,
    ProductOption,
    ChangeLog,
)


logger = logging.getLogger(__name__)


class ETLLoader:
    """Load parsed data into normalized database structure."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.logger = logging.getLogger(f"{__class__.__name__}")

    def load_parsing_results(self, results: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Load complete parsing results into database."""
        self.logger.info(f"Loading parsing results for {results.get('manufacturer', 'Unknown')}")

        load_summary = {
            "manufacturer_id": None,
            "price_book_id": None,
            "products_loaded": 0,
            "finishes_loaded": 0,
            "options_loaded": 0,
            "rules_loaded": 0,
            "errors": [],
        }

        try:
            # Load manufacturer
            manufacturer = self._load_manufacturer(results, session)
            load_summary["manufacturer_id"] = manufacturer.id

            # Load price book
            price_book = self._load_price_book(results, manufacturer, session)
            load_summary["price_book_id"] = price_book.id

            # Load finishes
            if "finish_symbols" in results:
                finish_count = self._load_finishes(results["finish_symbols"], manufacturer, session)
                load_summary["finishes_loaded"] = finish_count

            # Load products
            if "products" in results:
                product_count = self._load_products(results["products"], price_book, session)
                load_summary["products_loaded"] = product_count

            # Load options
            option_count = 0
            if "net_add_options" in results:
                option_count += self._load_options(results["net_add_options"], price_book, session)
            if "hinge_additions" in results:
                option_count += self._load_options(results["hinge_additions"], price_book, session)
            load_summary["options_loaded"] = option_count

            # Load rules
            if "price_rules" in results:
                rule_count = self._load_rules(results["price_rules"], price_book, session)
                load_summary["rules_loaded"] = rule_count

            session.commit()
            self.logger.info(f"Successfully loaded: {load_summary}")

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error loading results: {e}")
            load_summary["errors"].append(str(e))
            raise

        return load_summary

    def _load_manufacturer(self, results: Dict[str, Any], session: Session) -> Manufacturer:
        """Load or get manufacturer."""
        manufacturer_name = results.get("manufacturer", "Unknown")

        # Check if manufacturer exists
        manufacturer = session.query(Manufacturer).filter_by(name=manufacturer_name).first()

        if not manufacturer:
            manufacturer = Manufacturer(
                name=manufacturer_name,
                code=self._generate_manufacturer_code(manufacturer_name),
                created_at=datetime.utcnow(),
            )
            session.add(manufacturer)
            session.flush()  # Get ID
            self.logger.info(f"Created new manufacturer: {manufacturer_name}")
        else:
            self.logger.info(f"Using existing manufacturer: {manufacturer_name}")

        return manufacturer

    def _load_price_book(
        self, results: Dict[str, Any], manufacturer: Manufacturer, session: Session
    ) -> PriceBook:
        """Load price book."""
        effective_date_item = results.get("effective_date")
        effective_date = None

        if effective_date_item and isinstance(effective_date_item, dict):
            date_value = effective_date_item.get("value")
            if isinstance(date_value, (date, str)):
                effective_date = date_value if isinstance(date_value, date) else None

        source_file = results.get("source_file", "unknown.pdf")
        edition = self._extract_edition_from_filename(source_file)

        price_book = PriceBook(
            manufacturer_id=manufacturer.id,
            edition=edition,
            effective_date=effective_date,
            upload_date=datetime.utcnow(),
            file_path=source_file,
            status="processed",
            parsing_notes=f"Parsed with {results.get('parsing_metadata', {}).get('parser_version', '1.0')}",
        )

        session.add(price_book)
        session.flush()  # Get ID
        self.logger.info(f"Created price book: {edition}")

        return price_book

    def _load_finishes(
        self, finish_items: List[Dict[str, Any]], manufacturer: Manufacturer, session: Session
    ) -> int:
        """Load finish symbols."""
        count = 0

        for finish_item in finish_items:
            if not finish_item or not isinstance(finish_item.get("value"), dict):
                continue

            finish_data = finish_item["value"]

            # Check if finish exists
            existing_finish = (
                session.query(Finish)
                .filter_by(manufacturer_id=manufacturer.id, code=finish_data.get("code", ""))
                .first()
            )

            if not existing_finish:
                finish = Finish(
                    manufacturer_id=manufacturer.id,
                    code=finish_data.get("code", ""),
                    name=finish_data.get("name", ""),
                    bhma_code=finish_data.get("bhma_code"),
                    description=finish_data.get("description", ""),
                    created_at=datetime.utcnow(),
                )
                session.add(finish)
                count += 1

        session.flush()
        self.logger.info(f"Loaded {count} finishes")
        return count

    def _load_products(
        self, product_items: List[Dict[str, Any]], price_book: PriceBook, session: Session
    ) -> int:
        """Load products."""
        count = 0

        for product_item in product_items:
            if not product_item or not isinstance(product_item.get("value"), dict):
                continue

            product_data = product_item["value"]

            # Get or create product family
            family = self._get_or_create_family(product_data, price_book.manufacturer_id, session)

            # Create product
            product = Product(
                family_id=family.id if family else None,
                price_book_id=price_book.id,
                sku=product_data.get("sku", ""),
                model=product_data.get("model", ""),
                description=product_data.get("description", ""),
                base_price=product_data.get("base_price"),
                effective_date=price_book.effective_date,
                is_active=product_data.get("is_active", True),
                created_at=datetime.utcnow(),
            )

            session.add(product)
            count += 1

        session.flush()
        self.logger.info(f"Loaded {count} products")
        return count

    def _load_options(
        self, option_items: List[Dict[str, Any]], price_book: PriceBook, session: Session
    ) -> int:
        """Load product options."""
        count = 0

        for option_item in option_items:
            if not option_item or not isinstance(option_item.get("value"), dict):
                continue

            option_data = option_item["value"]

            # For now, create generic product options (not linked to specific products)
            option = ProductOption(
                product_id=None,  # Generic option, not product-specific
                option_type=option_data.get("option_code", "unknown"),
                option_code=option_data.get("option_code", ""),
                option_name=option_data.get("option_name", ""),
                adder_type=option_data.get("adder_type", "net_add"),
                adder_value=option_data.get("adder_value"),
                is_required=option_data.get("is_required", False),
                created_at=datetime.utcnow(),
            )

            session.add(option)
            count += 1

        session.flush()
        self.logger.info(f"Loaded {count} options")
        return count

    def _load_rules(
        self, rule_items: List[Dict[str, Any]], price_book: PriceBook, session: Session
    ) -> int:
        """Load pricing rules (stored as change logs for now)."""
        count = 0

        for rule_item in rule_items:
            if not rule_item or not isinstance(rule_item.get("value"), dict):
                continue

            rule_data = rule_item["value"]

            # Store rule as change log entry
            change_log = ChangeLog(
                old_price_book_id=None,
                new_price_book_id=price_book.id,
                change_type="price_rule",
                product_id=None,
                old_value=rule_data.get("source_finish"),
                new_value=rule_data.get("target_finish"),
                description=rule_data.get("description", ""),
                created_at=datetime.utcnow(),
            )

            session.add(change_log)
            count += 1

        session.flush()
        self.logger.info(f"Loaded {count} rules")
        return count

    def _get_or_create_family(
        self, product_data: Dict[str, Any], manufacturer_id: int, session: Session
    ) -> Optional[ProductFamily]:
        """Get or create product family."""
        series = product_data.get("series") or product_data.get("model", "")
        if not series:
            return None

        family = (
            session.query(ProductFamily)
            .filter_by(manufacturer_id=manufacturer_id, name=series)
            .first()
        )

        if not family:
            family = ProductFamily(
                manufacturer_id=manufacturer_id,
                name=series,
                category=self._determine_category(product_data),
                description=f"{series} Series",
                created_at=datetime.utcnow(),
            )
            session.add(family)
            session.flush()

        return family

    def _generate_manufacturer_code(self, name: str) -> str:
        """Generate manufacturer code from name."""
        if "select" in name.lower():
            return "SEL"
        elif "hager" in name.lower():
            return "HAG"
        else:
            # Take first 3 letters
            return name[:3].upper()

    def _extract_edition_from_filename(self, filename: str) -> str:
        """Extract edition from filename."""
        import re

        # Try to extract year
        year_match = re.search(r"(\d{4})", filename)
        if year_match:
            return f"{year_match.group(1)} Edition"

        return "Unknown Edition"

    def _determine_category(self, product_data: Dict[str, Any]) -> str:
        """Determine product category from data."""
        description = product_data.get("description", "").lower()
        series = product_data.get("series", "").lower()

        if "hinge" in description or "hinge" in series:
            return "Hinges"
        elif "lock" in description or "lock" in series:
            return "Locks"
        elif "door" in description:
            return "Door Hardware"
        else:
            return "Hardware"


def create_session(database_url: str) -> Session:
    """Create database session."""
    engine = create_engine(database_url)
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    return Session()
