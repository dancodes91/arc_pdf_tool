#!/usr/bin/env python3
"""
Command-line utility to parse PDFs and export results.
Demonstrates the complete parsing and export pipeline.
"""
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.select.parser import SelectHingesParser
from parsers.hager.parser import HagerParser
from services.etl_loader import ETLLoader, create_session
from services.exporters import QuickExporter, DataExporter


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def detect_manufacturer(pdf_path: str) -> str:
    """Detect manufacturer from PDF filename."""
    filename = Path(pdf_path).name.lower()

    if 'select' in filename or 'hinges' in filename:
        return 'select'
    elif 'hager' in filename:
        return 'hager'
    else:
        # Default to select for now
        print(f"Warning: Could not detect manufacturer from '{filename}', defaulting to SELECT")
        return 'select'


def parse_pdf(pdf_path: str, manufacturer: str = None) -> dict:
    """Parse PDF using appropriate parser."""
    if manufacturer is None:
        manufacturer = detect_manufacturer(pdf_path)

    print(f"Parsing {pdf_path} as {manufacturer.upper()} manufacturer...")

    if manufacturer.lower() == 'select':
        parser = SelectHingesParser(pdf_path)
    elif manufacturer.lower() == 'hager':
        parser = HagerParser(pdf_path)
    else:
        raise ValueError(f"Unknown manufacturer: {manufacturer}")

    results = parser.parse()
    return results


def export_results(results: dict, output_dir: str, formats: list):
    """Export parsing results in specified formats."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting results to {output_dir} in formats: {', '.join(formats)}")

    files_created = QuickExporter.export_parsing_results(results, str(output_path))

    print("Files created:")
    for export_type, file_path in files_created.items():
        print(f"  {export_type}: {file_path}")

    return files_created


def load_to_database(results: dict, database_url: str):
    """Load parsing results to database."""
    print(f"Loading results to database: {database_url}")

    session = create_session(database_url)
    loader = ETLLoader(database_url)

    try:
        load_summary = loader.load_parsing_results(results, session)
        print("Load Summary:")
        print(f"  Manufacturer ID: {load_summary['manufacturer_id']}")
        print(f"  Price Book ID: {load_summary['price_book_id']}")
        print(f"  Products Loaded: {load_summary['products_loaded']}")
        print(f"  Finishes Loaded: {load_summary['finishes_loaded']}")
        print(f"  Options Loaded: {load_summary['options_loaded']}")
        print(f"  Rules Loaded: {load_summary['rules_loaded']}")

        if load_summary['errors']:
            print("  Errors:")
            for error in load_summary['errors']:
                print(f"    - {error}")

        return load_summary

    except Exception as e:
        print(f"Error loading to database: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def export_from_database(price_book_id: int, database_url: str, output_dir: str, formats: list):
    """Export data from database."""
    print(f"Exporting price book {price_book_id} from database...")

    session = create_session(database_url)
    exporter = DataExporter(session)

    try:
        files_created = exporter.export_price_book_data(
            price_book_id=price_book_id,
            output_dir=output_dir,
            formats=formats
        )

        print("Database export files created:")
        for export_type, file_path in files_created.items():
            print(f"  {export_type}: {file_path}")

        return files_created

    finally:
        session.close()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Parse PDF price books and export results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse and export directly (no database)
  python parse_and_export.py input.pdf --output ./exports --formats json csv

  # Parse and load to database
  python parse_and_export.py input.pdf --database sqlite:///test.db --load-only

  # Export from database
  python parse_and_export.py --export-db-id 1 --database sqlite:///test.db --output ./exports

  # Full pipeline: parse, load to DB, then export from DB
  python parse_and_export.py input.pdf --database sqlite:///test.db --output ./exports --formats xlsx json
        """
    )

    # Input options
    parser.add_argument('pdf_path', nargs='?', help='Path to PDF file to parse')
    parser.add_argument('--manufacturer', choices=['select', 'hager'],
                       help='Manufacturer type (auto-detected if not specified)')

    # Output options
    parser.add_argument('--output', '-o', default='./exports',
                       help='Output directory for exports (default: ./exports)')
    parser.add_argument('--formats', nargs='+', choices=['json', 'csv', 'xlsx'],
                       default=['json', 'csv'], help='Export formats (default: json csv)')

    # Database options
    parser.add_argument('--database', '--db',
                       help='Database URL (e.g., sqlite:///test.db)')
    parser.add_argument('--load-only', action='store_true',
                       help='Only load to database, don\'t export files')
    parser.add_argument('--export-db-id', type=int,
                       help='Export existing price book from database by ID')

    # Other options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Validate arguments
    if not args.pdf_path and not args.export_db_id:
        parser.error("Must specify either a PDF file to parse or --export-db-id")

    if args.export_db_id and not args.database:
        parser.error("--export-db-id requires --database")

    if args.load_only and not args.database:
        parser.error("--load-only requires --database")

    try:
        # Export from database only
        if args.export_db_id:
            export_from_database(args.export_db_id, args.database, args.output, args.formats)
            return

        # Parse PDF
        results = parse_pdf(args.pdf_path, args.manufacturer)

        # Print parsing summary
        summary = results.get('summary', {})
        validation = results.get('validation', {})

        print(f"\nParsing Summary:")
        print(f"  Manufacturer: {results.get('manufacturer', 'Unknown')}")
        print(f"  Total Products: {summary.get('total_products', 0)}")
        print(f"  Total Finishes: {summary.get('total_finishes', 0)}")
        print(f"  Total Rules: {summary.get('total_rules', 0)}")
        print(f"  Total Options: {summary.get('total_additions', 0) + summary.get('total_options', 0)}")
        print(f"  Has Effective Date: {summary.get('has_effective_date', False)}")
        print(f"  Validation: {'[VALID]' if validation.get('is_valid', False) else '[INVALID]'}")

        if validation.get('errors'):
            print(f"  Validation Errors:")
            for error in validation['errors']:
                print(f"    - {error}")

        # Load to database if requested
        load_summary = None
        if args.database:
            load_summary = load_to_database(results, args.database)

        # Export results
        if not args.load_only:
            if args.database and load_summary and load_summary['price_book_id']:
                # Export from database for better formatting
                export_from_database(
                    load_summary['price_book_id'],
                    args.database,
                    args.output,
                    args.formats
                )
            else:
                # Export parsing results directly
                export_results(results, args.output, args.formats)

        print(f"\n[OK] Complete! Results processed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()