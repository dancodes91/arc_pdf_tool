"""
Generate PDF deployment guide from markdown
Requires: pip install markdown weasyprint
"""
import markdown
from weasyprint import HTML, CSS
from pathlib import Path

def create_pdf_from_markdown(md_file, output_pdf):
    """Convert markdown file to styled PDF"""

    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )

    # Custom CSS for professional styling
    css_style = """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "ARC PDF Tool - Deployment Guide";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }

    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        font-size: 11pt;
    }

    h1 {
        color: #2563eb;
        font-size: 24pt;
        margin-top: 0;
        margin-bottom: 20px;
        border-bottom: 3px solid #2563eb;
        padding-bottom: 10px;
        page-break-after: avoid;
    }

    h2 {
        color: #1e40af;
        font-size: 18pt;
        margin-top: 30px;
        margin-bottom: 15px;
        border-bottom: 2px solid #ddd;
        padding-bottom: 5px;
        page-break-after: avoid;
    }

    h3 {
        color: #1e3a8a;
        font-size: 14pt;
        margin-top: 20px;
        margin-bottom: 10px;
        page-break-after: avoid;
    }

    h4 {
        color: #1e293b;
        font-size: 12pt;
        margin-top: 15px;
        margin-bottom: 8px;
        page-break-after: avoid;
    }

    p {
        margin: 10px 0;
        text-align: justify;
    }

    code {
        background-color: #f1f5f9;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        color: #e11d48;
    }

    pre {
        background-color: #1e293b;
        color: #f8fafc;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 9pt;
        line-height: 1.4;
        page-break-inside: avoid;
    }

    pre code {
        background-color: transparent;
        color: #f8fafc;
        padding: 0;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        page-break-inside: avoid;
    }

    th {
        background-color: #2563eb;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: bold;
    }

    td {
        padding: 8px 10px;
        border: 1px solid #ddd;
    }

    tr:nth-child(even) {
        background-color: #f8fafc;
    }

    ul, ol {
        margin: 10px 0;
        padding-left: 25px;
    }

    li {
        margin: 5px 0;
    }

    blockquote {
        border-left: 4px solid #2563eb;
        margin: 20px 0;
        padding: 10px 20px;
        background-color: #eff6ff;
        font-style: italic;
    }

    .screenshot-placeholder {
        background-color: #fef3c7;
        border: 2px dashed #f59e0b;
        padding: 30px;
        margin: 20px 0;
        text-align: center;
        font-weight: bold;
        color: #92400e;
        page-break-inside: avoid;
    }

    hr {
        border: none;
        border-top: 2px solid #e5e7eb;
        margin: 30px 0;
    }

    a {
        color: #2563eb;
        text-decoration: none;
    }

    .page-break {
        page-break-after: always;
    }

    .warning {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 15px;
        margin: 15px 0;
    }

    .info {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        margin: 15px 0;
    }

    .success {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 15px;
        margin: 15px 0;
    }
    """

    # Wrap HTML with proper structure
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>ARC PDF Tool - Deployment Guide</title>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Convert HTML to PDF
    HTML(string=full_html).write_pdf(
        output_pdf,
        stylesheets=[CSS(string=css_style)]
    )

    print(f"✅ PDF created successfully: {output_pdf}")

if __name__ == "__main__":
    # Get script directory
    script_dir = Path(__file__).parent

    # Input and output files
    markdown_file = script_dir / "DEPLOYMENT_RAILWAY_RENDER_VERCEL.md"
    pdf_file = script_dir / "ARC_PDF_Tool_Deployment_Guide.pdf"

    if not markdown_file.exists():
        print(f"❌ Markdown file not found: {markdown_file}")
        print("Please create DEPLOYMENT_RAILWAY_RENDER_VERCEL.md first")
    else:
        create_pdf_from_markdown(markdown_file, pdf_file)
        print(f"\n📄 PDF Guide: {pdf_file}")
