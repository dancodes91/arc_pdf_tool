"""Find SELECT hinge pages in Hager PDF."""
import pypdf

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf'
pdf = pypdf.PdfReader(pdf_path)

print(f'Total pages: {len(pdf.pages)}\n')
print('Searching for SELECT/Concealed Edge Mount pages...\n')

select_pages = []
for i in range(len(pdf.pages)):
    text = pdf.pages[i].extract_text().upper()

    # Look for SELECT model numbers or "Concealed Edge Mount" section
    if any(keyword in text for keyword in ['SL11', 'SL12', 'SL14', 'SL18', 'SL24', 'CONCEALED EDGE MOUNT']):
        select_pages.append(i + 1)
        print(f'Page {i+1}: Found SELECT content')

        # Print first 200 chars
        snippet = pdf.pages[i].extract_text()[:200].replace('\n', ' ')
        print(f'  Snippet: {snippet}...\n')

print(f'\nSummary: Found SELECT content on {len(select_pages)} pages')
print(f'Page numbers: {select_pages}')
