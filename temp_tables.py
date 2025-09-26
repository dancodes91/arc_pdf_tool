import json
from parsers.shared.pdf_io import EnhancedPDFExtractor
pdf_path = r"D:\%BkUP_DntRMvMe!\MyDocDrvD\Desktop\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf"
extractor = EnhancedPDFExtractor(pdf_path)
doc = extractor.extract_document()
page9 = doc.pages[8]
print('Page', page9.page_number, 'method', page9.extraction_method, 'tables', len(page9.tables))
for t_i, table in enumerate(page9.tables):
    print('\nTable', t_i)
    print(table.head())
print('--- done ---')
