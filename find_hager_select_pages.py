"""Find SELECT/Concealed Edge Mount pages in Hager PDF."""
import pypdf

pdf_path = r'C:\Users\Vache\projects\arc_pdf_tool\test_data\pdfs\2025-hager-price-book.pdf'
pdf = pypdf.PdfReader(pdf_path)

print(f'Total pages: {len(pdf.pages)}\n')
print('Searching for CONCEALED or SL11/SL12/SL14...\n')

select_pages = []
for i in range(len(pdf.pages)):
    text = pdf.pages[i].extract_text()

    # Look for CONCEALED EDGE MOUNT or SELECT model numbers
    if 'CONCEALED' in text or 'SL11' in text or 'SL12' in text or 'SL14' in text:
        select_pages.append(i + 1)
        print(f'Page {i+1}: Found SELECT content')

        # Print snippet
        lines = text.split('\n')[:15]
        snippet = ' '.join(lines)[:200]
        print(f'  Snippet: {snippet}...\n')

print(f'\n=== Summary ===')
print(f'Found SELECT content on {len(select_pages)} pages: {select_pages[:20]}')
