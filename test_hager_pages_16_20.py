"""Test Hager pages 16-20 for SELECT content."""
import pypdf
import camelot

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf'
pdf = pypdf.PdfReader(pdf_path)

for page_num in range(16, 21):
    print(f"\n{'='*80}")
    print(f"PAGE {page_num}")
    print('='*80)

    # Get text
    text = pdf.pages[page_num - 1].extract_text()
    print(f"\nText snippet:")
    print(text[:400])

    # Check for SELECT models
    if any(model in text for model in ['SL11', 'SL12', 'SL14', 'CONCEALED EDGE']):
        print(f"\n*** FOUND SELECT CONTENT! ***")

        # Try stream flavor
        print(f"\n--- Stream flavor tables ---")
        stream_tables = camelot.read_pdf(pdf_path, pages=str(page_num), flavor='stream')
        print(f"Found {stream_tables.n} tables")

        if stream_tables.n > 0:
            df = stream_tables[0].df
            print(f"\nTable shape: {df.shape}")
            print(f"Header: {df.iloc[0].tolist()}")
            print(f"\nFirst 5 rows:")
            print(df.head(5).to_string())
