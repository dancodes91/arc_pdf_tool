# PDF Price Book Parser

A comprehensive Python application for parsing manufacturer PDF price books, extracting structured pricing data, and managing price book updates with automated diff generation.

## 🚀 Features

- **Multi-Format PDF Parsing**: Support for both digital and scanned PDFs with OCR fallback
- **Manufacturer Support**: Specialized parsers for Hager and SELECT Hinges
- **Database Management**: SQLite/PostgreSQL integration with normalized data schema
- **Diff Engine**: Automated comparison of price book editions with change tracking
- **Export Capabilities**: Excel and CSV export with professional formatting
- **Modern Web UI**: Clean, responsive admin interface built with Bootstrap
- **Accuracy Validation**: 98%+ row accuracy, 99%+ numeric accuracy requirements

## 📋 Supported Manufacturers

### Hager
- Finish codes (US3, US4, US10B, US15, US26D, US32D, US33D)
- Adder rules and pricing calculations
- Product SKUs and descriptions
- Effective date extraction

### SELECT Hinges
- Net-add options (CTW, EPT, EMS, TIPIT, Hospital Tip, UL FR3)
- Option compatibility rules
- Product specifications and pricing
- Fire rating options

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Tesseract OCR (for scanned PDF support)
- Poppler utilities (for PDF processing)

### Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd pdf-price-book-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils
```

#### macOS
```bash
brew install tesseract poppler
```

#### Windows
Download and install:
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)

## 🚀 Quick Start

1. **Initialize the application**:
   ```bash
   python run.py
   ```

2. **Access the web interface**:
   Open your browser and navigate to `http://localhost:5000`

3. **Upload a PDF**:
   - Click "Upload PDF" in the navigation
   - Select manufacturer (or auto-detect)
   - Choose your PDF file
   - Click "Upload & Parse"

4. **View results**:
   - Preview parsed data
   - Export to Excel/CSV
   - Compare with other editions

## 📁 Project Structure

```
pdf-price-book-parser/
├── app.py                 # Flask application
├── run.py                 # Application runner
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── database/
│   ├── models.py          # SQLAlchemy models
│   └── manager.py         # Database operations
├── parsers/
│   ├── base_parser.py     # Base parser class
│   ├── hager_parser.py    # Hager-specific parser
│   └── select_hinges_parser.py  # SELECT Hinges parser
├── diff_engine.py         # Price book comparison
├── export_manager.py      # Export functionality
├── templates/             # HTML templates
├── static/                # CSS/JS assets
├── tests/                 # Test suite
├── uploads/               # PDF upload directory
├── exports/               # Export files
└── logs/                  # Application logs
```

## 🔧 Configuration

### Environment Variables

```bash
# Database configuration
DATABASE_URL=sqlite:///price_books.db

# OCR configuration
TESSERACT_CMD=/usr/bin/tesseract

# File upload limits
MAX_CONTENT_LENGTH=52428800  # 50MB
```

### Database Configuration

The application supports both SQLite (default) and PostgreSQL:

```python
# SQLite (default)
DATABASE_URL = 'sqlite:///price_books.db'

# PostgreSQL
DATABASE_URL = 'postgresql://user:password@localhost/price_books'
```

## 📊 API Endpoints

### Web Interface
- `GET /` - Dashboard
- `GET /upload` - Upload form
- `POST /upload` - Process PDF upload
- `GET /preview/<id>` - Preview parsed data
- `GET /compare` - Compare price books
- `GET /export/<id>` - Export data

### API Endpoints
- `POST /api/compare` - Compare price books
- `GET /api/products/<id>` - Get products

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python tests/test_parsers.py
python tests/test_database.py

# Run with coverage
python -m pytest tests/ --cov=.
```

## 📈 Usage Examples

### Parsing a Hager Price Book

```python
from parsers import HagerParser

parser = HagerParser('path/to/hager_price_book.pdf')
data = parser.parse()

print(f"Found {len(data['products'])} products")
print(f"Effective date: {data['effective_date']}")
```

### Comparing Price Books

```python
from diff_engine import DiffEngine

diff_engine = DiffEngine()
comparison = diff_engine.compare_price_books(old_book_id, new_book_id)

print(f"Total changes: {comparison['summary']['total_changes']}")
print(f"New products: {comparison['summary']['new_products']}")
```

### Exporting Data

```python
from export_manager import ExportManager

export_manager = ExportManager()
filepath = export_manager.export_price_book(price_book_id, format='excel')
print(f"Exported to: {filepath}")
```

## 🔍 Accuracy Requirements

The system is designed to meet strict accuracy requirements:

- **Row Accuracy**: ≥98% of table rows correctly parsed
- **Numeric Accuracy**: ≥99% of price values correctly extracted
- **SKU Recognition**: High accuracy for manufacturer-specific SKU patterns
- **Date Extraction**: Reliable extraction of effective dates

## 🚨 Troubleshooting

### Common Issues

1. **OCR not working**:
   - Ensure Tesseract is installed and in PATH
   - Check `TESSERACT_CMD` configuration

2. **PDF parsing errors**:
   - Verify PDF is not password-protected
   - Try OCR fallback for scanned PDFs

3. **Database errors**:
   - Check database permissions
   - Verify connection string

4. **Memory issues with large PDFs**:
   - Increase system memory
   - Process PDFs in smaller batches

### Logs

Check application logs in the `logs/` directory for detailed error information.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review application logs
3. Create an issue in the repository
4. Contact the development team

## 🔮 Future Enhancements

- Additional manufacturer support
- Advanced pricing rules engine
- REST API for external integrations
- Real-time collaboration features
- Advanced analytics and reporting
- Machine learning for improved accuracy

---

**Built with ❤️ for architectural hardware pricing automation**
