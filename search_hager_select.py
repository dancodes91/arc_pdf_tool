"""Search for SELECT/Concealed Edge Mount in Hager PDF."""
import pypdf

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf'
pdf = pypdf.PdfReader(pdf_path)

print(f'Total pages: {len(pdf.pages)}\n')

# Search for various keywords
keywords = ['SELECT', 'CONCEALED EDGE', 'SL11', 'SL12', 'SL14', 'SL18', 'SL24']

for keyword in keywords:
    print(f'\n=== Searching for "{keyword}" ===')
    found_pages = []

    for i in range(len(pdf.pages)):
        text = pdf.pages[i].extract_text()
        if keyword in text:
            found_pages.append(i + 1)
            if len(found_pages) <= 5:  # Show first 5 matches
                print(f'Page {i+1}: Found "{keyword}"')
                # Find context around keyword
                lines = text.split('\n')
                for line in lines:
                    if keyword in line:
                        print(f'  Context: {line[:150]}')
                        break

    print(f'Total pages with "{keyword}": {len(found_pages)}')
    if found_pages:
        print(f'Page numbers: {found_pages[:20]}...')  # Show first 20
