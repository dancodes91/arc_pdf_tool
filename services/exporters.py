"""
Data export utilities for parsed pricing data.
"""
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.models import (
    Manufacturer, PriceBook, Product, Finish, ProductPrice,
    ProductOption, ChangeLog
)


class DataExporter:
    """Export parsed data to various formats."""

    def __init__(self, session: Session):
        self.session = session

    def export_price_book_data(
        self,
        price_book_id: int,
        output_dir: str,
        formats: List[str] = None
    ) -> Dict[str, str]:
        """Export complete price book data in specified formats."""
        if formats is None:
            formats = ['csv', 'xlsx', 'json']

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get price book data
        price_book = self.session.get(PriceBook, price_book_id)
        if not price_book:
            raise ValueError(f"Price book {price_book_id} not found")

        # Gather all data
        data = self._gather_price_book_data(price_book)

        files_created = {}

        # Export in each requested format
        if 'csv' in formats:
            csv_files = self._export_to_csv(data, output_path, price_book)
            files_created.update(csv_files)

        if 'xlsx' in formats:
            xlsx_file = self._export_to_xlsx(data, output_path, price_book)
            files_created['xlsx'] = xlsx_file

        if 'json' in formats:
            json_file = self._export_to_json(data, output_path, price_book)
            files_created['json'] = json_file

        return files_created

    def export_manufacturer_catalog(
        self,
        manufacturer_id: int,
        output_dir: str,
        formats: List[str] = None
    ) -> Dict[str, str]:
        """Export complete manufacturer catalog."""
        if formats is None:
            formats = ['csv', 'xlsx', 'json']

        manufacturer = self.session.get(Manufacturer, manufacturer_id)
        if not manufacturer:
            raise ValueError(f"Manufacturer {manufacturer_id} not found")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get all price books for this manufacturer
        price_books = self.session.query(PriceBook).filter_by(
            manufacturer_id=manufacturer_id
        ).order_by(PriceBook.effective_date.desc()).all()

        catalog_data = {
            'manufacturer': {
                'name': manufacturer.name,
                'code': manufacturer.code,
                'created_at': manufacturer.created_at.isoformat() if manufacturer.created_at else None
            },
            'price_books': [],
            'all_products': [],
            'all_finishes': [],
            'summary': {
                'total_price_books': len(price_books),
                'total_products': 0,
                'total_finishes': 0,
                'date_range': None
            }
        }

        all_products = []
        all_finishes = []

        for pb in price_books:
            pb_data = self._gather_price_book_data(pb)
            catalog_data['price_books'].append({
                'id': pb.id,
                'edition': pb.edition,
                'effective_date': pb.effective_date.isoformat() if pb.effective_date else None,
                'upload_date': pb.upload_date.isoformat() if pb.upload_date else None,
                'status': pb.status,
                'product_count': len(pb_data['products']),
                'finish_count': len(pb_data['finishes'])
            })

            # Aggregate products and finishes
            all_products.extend(pb_data['products'])
            all_finishes.extend(pb_data['finishes'])

        catalog_data['all_products'] = all_products
        catalog_data['all_finishes'] = all_finishes
        catalog_data['summary']['total_products'] = len(all_products)
        catalog_data['summary']['total_finishes'] = len(all_finishes)

        # Set date range
        if price_books:
            earliest = min(pb.effective_date for pb in price_books if pb.effective_date)
            latest = max(pb.effective_date for pb in price_books if pb.effective_date)
            if earliest and latest:
                catalog_data['summary']['date_range'] = {
                    'earliest': earliest.isoformat(),
                    'latest': latest.isoformat()
                }

        files_created = {}

        # Export in requested formats
        if 'json' in formats:
            json_file = output_path / f"{manufacturer.name.lower()}_catalog.json"
            with open(json_file, 'w') as f:
                json.dump(catalog_data, f, indent=2, default=str)
            files_created['catalog_json'] = str(json_file)

        if 'csv' in formats:
            # Export products to CSV
            products_file = output_path / f"{manufacturer.name.lower()}_products.csv"
            self._write_csv(all_products, products_file)
            files_created['products_csv'] = str(products_file)

            # Export finishes to CSV
            finishes_file = output_path / f"{manufacturer.name.lower()}_finishes.csv"
            self._write_csv(all_finishes, finishes_file)
            files_created['finishes_csv'] = str(finishes_file)

        if 'xlsx' in formats:
            xlsx_file = output_path / f"{manufacturer.name.lower()}_catalog.xlsx"
            with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
                # Products sheet
                if all_products:
                    products_df = pd.DataFrame(all_products)
                    products_df.to_excel(writer, sheet_name='Products', index=False)

                # Finishes sheet
                if all_finishes:
                    finishes_df = pd.DataFrame(all_finishes)
                    finishes_df.to_excel(writer, sheet_name='Finishes', index=False)

                # Summary sheet
                summary_data = [
                    ['Manufacturer', manufacturer.name],
                    ['Code', manufacturer.code],
                    ['Total Price Books', len(price_books)],
                    ['Total Products', len(all_products)],
                    ['Total Finishes', len(all_finishes)],
                    ['Export Date', datetime.now().isoformat()]
                ]
                summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            files_created['catalog_xlsx'] = str(xlsx_file)

        return files_created

    def export_comparison_report(
        self,
        old_price_book_id: int,
        new_price_book_id: int,
        output_dir: str,
        formats: List[str] = None
    ) -> Dict[str, str]:
        """Export price comparison report between two price books."""
        if formats is None:
            formats = ['csv', 'xlsx']

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        old_pb = self.session.get(PriceBook, old_price_book_id)
        new_pb = self.session.get(PriceBook, new_price_book_id)

        if not old_pb or not new_pb:
            raise ValueError("One or both price books not found")

        # Get change logs between these price books
        changes = self.session.query(ChangeLog).filter_by(
            old_price_book_id=old_price_book_id,
            new_price_book_id=new_price_book_id
        ).all()

        comparison_data = []
        for change in changes:
            comparison_data.append({
                'product_id': change.product_id,
                'change_type': change.change_type,
                'old_value': change.old_value,
                'new_value': change.new_value,
                'description': change.description,
                'created_at': change.created_at.isoformat() if change.created_at else None
            })

        files_created = {}

        if 'csv' in formats:
            csv_file = output_path / f"comparison_{old_pb.edition}_to_{new_pb.edition}.csv"
            self._write_csv(comparison_data, csv_file)
            files_created['comparison_csv'] = str(csv_file)

        if 'xlsx' in formats:
            xlsx_file = output_path / f"comparison_{old_pb.edition}_to_{new_pb.edition}.xlsx"
            df = pd.DataFrame(comparison_data)
            df.to_excel(xlsx_file, sheet_name='Price Changes', index=False)
            files_created['comparison_xlsx'] = str(xlsx_file)

        return files_created

    def _gather_price_book_data(self, price_book: PriceBook) -> Dict[str, List[Dict[str, Any]]]:
        """Gather all data for a price book."""
        data = {
            'products': [],
            'finishes': [],
            'options': [],
            'price_book_info': {
                'id': price_book.id,
                'manufacturer': price_book.manufacturer.name if price_book.manufacturer else 'Unknown',
                'edition': price_book.edition,
                'effective_date': price_book.effective_date.isoformat() if price_book.effective_date else None,
                'upload_date': price_book.upload_date.isoformat() if price_book.upload_date else None,
                'status': price_book.status,
                'file_path': price_book.file_path
            }
        }

        # Get products
        products = self.session.query(Product).filter_by(price_book_id=price_book.id).all()
        for product in products:
            product_data = {
                'id': product.id,
                'sku': product.sku,
                'model': product.model,
                'description': product.description,
                'base_price': float(product.base_price) if product.base_price else None,
                'family': product.family.name if product.family else None,
                'is_active': product.is_active,
                'effective_date': product.effective_date.isoformat() if product.effective_date else None,
                'created_at': product.created_at.isoformat() if product.created_at else None
            }
            data['products'].append(product_data)

        # Get finishes for this manufacturer
        if price_book.manufacturer:
            finishes = self.session.query(Finish).filter_by(
                manufacturer_id=price_book.manufacturer_id
            ).all()
            for finish in finishes:
                finish_data = {
                    'id': finish.id,
                    'code': finish.code,
                    'name': finish.name,
                    'bhma_code': finish.bhma_code,
                    'description': finish.description,
                    'created_at': finish.created_at.isoformat() if finish.created_at else None
                }
                data['finishes'].append(finish_data)

        # Get options (not product-specific for now)
        options = self.session.query(ProductOption).filter(
            ProductOption.product_id.is_(None)  # Generic options
        ).all()
        for option in options:
            option_data = {
                'id': option.id,
                'option_type': option.option_type,
                'option_code': option.option_code,
                'option_name': option.option_name,
                'adder_type': option.adder_type,
                'adder_value': float(option.adder_value) if option.adder_value else None,
                'is_required': option.is_required,
                'created_at': option.created_at.isoformat() if option.created_at else None
            }
            data['options'].append(option_data)

        return data

    def _export_to_csv(self, data: Dict[str, Any], output_path: Path, price_book: PriceBook) -> Dict[str, str]:
        """Export data to CSV files."""
        files_created = {}
        output_path = Path(output_path)  # Ensure it's a Path object

        # Products CSV
        if data['products']:
            products_file = output_path / f"{price_book.edition}_products.csv"
            self._write_csv(data['products'], products_file)
            files_created['products_csv'] = str(products_file)

        # Finishes CSV
        if data['finishes']:
            finishes_file = output_path / f"{price_book.edition}_finishes.csv"
            self._write_csv(data['finishes'], finishes_file)
            files_created['finishes_csv'] = str(finishes_file)

        # Options CSV
        if data['options']:
            options_file = output_path / f"{price_book.edition}_options.csv"
            self._write_csv(data['options'], options_file)
            files_created['options_csv'] = str(options_file)

        return files_created

    def _export_to_xlsx(self, data: Dict[str, Any], output_path: Path, price_book: PriceBook) -> str:
        """Export data to Excel file."""
        output_path = Path(output_path)  # Ensure it's a Path object
        xlsx_file = output_path / f"{price_book.edition}_complete.xlsx"

        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            # Products sheet
            if data['products']:
                products_df = pd.DataFrame(data['products'])
                products_df.to_excel(writer, sheet_name='Products', index=False)

            # Finishes sheet
            if data['finishes']:
                finishes_df = pd.DataFrame(data['finishes'])
                finishes_df.to_excel(writer, sheet_name='Finishes', index=False)

            # Options sheet
            if data['options']:
                options_df = pd.DataFrame(data['options'])
                options_df.to_excel(writer, sheet_name='Options', index=False)

            # Price Book Info sheet
            info_data = [
                ['Price Book ID', data['price_book_info']['id']],
                ['Manufacturer', data['price_book_info']['manufacturer']],
                ['Edition', data['price_book_info']['edition']],
                ['Effective Date', data['price_book_info']['effective_date']],
                ['Upload Date', data['price_book_info']['upload_date']],
                ['Status', data['price_book_info']['status']],
                ['Source File', data['price_book_info']['file_path']],
                ['Export Date', datetime.now().isoformat()],
                ['Total Products', len(data['products'])],
                ['Total Finishes', len(data['finishes'])],
                ['Total Options', len(data['options'])]
            ]
            info_df = pd.DataFrame(info_data, columns=['Field', 'Value'])
            info_df.to_excel(writer, sheet_name='Info', index=False)

        return str(xlsx_file)

    def _export_to_json(self, data: Dict[str, Any], output_path: Path, price_book: PriceBook) -> str:
        """Export data to JSON file."""
        output_path = Path(output_path)  # Ensure it's a Path object
        json_file = output_path / f"{price_book.edition}_complete.json"

        export_data = {
            'price_book_info': data['price_book_info'],
            'products': data['products'],
            'finishes': data['finishes'],
            'options': data['options'],
            'export_metadata': {
                'export_date': datetime.now().isoformat(),
                'export_format': 'json',
                'total_products': len(data['products']),
                'total_finishes': len(data['finishes']),
                'total_options': len(data['options'])
            }
        }

        with open(json_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        return str(json_file)

    def _write_csv(self, data: List[Dict[str, Any]], file_path: Path) -> None:
        """Write data to CSV file."""
        if not data:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)


class QuickExporter:
    """Quick export utilities for common use cases."""

    @staticmethod
    def export_products_to_csv(products: List[Dict[str, Any]], output_file: str) -> None:
        """Quick CSV export for products."""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if not products:
                return

            fieldnames = products[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)

    @staticmethod
    def export_to_json(data: Dict[str, Any], output_file: str) -> None:
        """Quick JSON export."""
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def export_parsing_results(results: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """Export raw parsing results in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files_created = {}
        manufacturer = results.get('manufacturer', 'unknown').lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export complete results as JSON
        json_file = output_path / f"{manufacturer}_parsing_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        files_created['results_json'] = str(json_file)

        # Export products as CSV if available
        if results.get('products'):
            products_data = []
            for product_item in results['products']:
                if isinstance(product_item, dict) and 'value' in product_item:
                    product_data = product_item['value']
                    if isinstance(product_data, dict):
                        # Flatten the product data for CSV
                        csv_row = {
                            'sku': product_data.get('sku', ''),
                            'model': product_data.get('model', ''),
                            'series': product_data.get('series', ''),
                            'description': product_data.get('description', ''),
                            'base_price': product_data.get('base_price'),
                            'manufacturer': product_data.get('manufacturer', ''),
                            'is_active': product_data.get('is_active', True)
                        }
                        products_data.append(csv_row)

            if products_data:
                products_file = output_path / f"{manufacturer}_products_{timestamp}.csv"
                QuickExporter.export_products_to_csv(products_data, str(products_file))
                files_created['products_csv'] = str(products_file)

        # Export finishes as CSV if available
        if results.get('finish_symbols'):
            finishes_data = []
            for finish_item in results['finish_symbols']:
                if isinstance(finish_item, dict) and 'value' in finish_item:
                    finish_data = finish_item['value']
                    if isinstance(finish_data, dict):
                        csv_row = {
                            'code': finish_data.get('code', ''),
                            'name': finish_data.get('name', ''),
                            'bhma_code': finish_data.get('bhma_code', ''),
                            'description': finish_data.get('description', ''),
                            'base_price': finish_data.get('base_price')
                        }
                        finishes_data.append(csv_row)

            if finishes_data:
                finishes_file = output_path / f"{manufacturer}_finishes_{timestamp}.csv"
                QuickExporter.export_products_to_csv(finishes_data, str(finishes_file))
                files_created['finishes_csv'] = str(finishes_file)

        return files_created