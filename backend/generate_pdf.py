#!/usr/bin/env python3
"""
PDF Generator for Deployment Workflow Guide
Converts the Markdown documentation to a downloadable PDF
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path
import os

def generate_pdf():
    """Convert the Markdown workflow guide to PDF"""
    
    # Read the markdown file
    md_file = Path("DEPLOYMENT_WORKFLOW_GUIDE.md")
    if not md_file.exists():
        print("❌ Markdown file not found!")
        return False
    
    print("📄 Reading Markdown file...")
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert markdown to HTML
    print("🔄 Converting Markdown to HTML...")
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
    html_content = md.convert(markdown_content)
    
    # Create complete HTML document with styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Shopify Chatbot - Deployment Workflow Guide</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2563eb;
                border-bottom: 3px solid #3b82f6;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #1e40af;
                border-bottom: 2px solid #60a5fa;
                padding-bottom: 5px;
                margin-top: 30px;
            }}
            h3 {{
                color: #1d4ed8;
                margin-top: 25px;
            }}
            code {{
                background-color: #f3f4f6;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', monospace;
            }}
            pre {{
                background-color: #1f2937;
                color: #f9fafb;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: 'Consolas', 'Monaco', monospace;
            }}
            blockquote {{
                border-left: 4px solid #3b82f6;
                padding-left: 15px;
                margin-left: 0;
                color: #4b5563;
            }}
            .emoji {{
                font-size: 1.2em;
            }}
            hr {{
                border: none;
                border-top: 2px solid #e5e7eb;
                margin: 30px 0;
            }}
            ul, ol {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }}
            th, td {{
                border: 1px solid #d1d5db;
                padding: 8px 12px;
                text-align: left;
            }}
            th {{
                background-color: #f3f4f6;
                font-weight: bold;
            }}
            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF
    print("📝 Generating PDF...")
    output_file = "Shopify_Chatbot_Deployment_Guide.pdf"
    
    try:
        HTML(string=full_html).write_pdf(
            output_file,
            stylesheets=[CSS(string="""
                @page {
                    size: A4;
                    margin: 1in;
                }
                body {
                    font-size: 11pt;
                }
                h1 {
                    font-size: 18pt;
                }
                h2 {
                    font-size: 14pt;
                }
                h3 {
                    font-size: 12pt;
                }
                pre {
                    font-size: 9pt;
                }
            """)]
        )
        
        print(f"✅ PDF generated successfully!")
        print(f"📁 File location: {os.path.abspath(output_file)}")
        print(f"📊 File size: {os.path.getsize(output_file) / 1024:.1f} KB")
        return True
        
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 SHOPIFY CHATBOT - PDF GENERATOR")
    print("=" * 50)
    
    success = generate_pdf()
    
    if success:
        print("\n🎉 SUCCESS! Your deployment guide PDF is ready for download!")
        print("\n📋 The PDF contains:")
        print("   • Complete workflow commands")
        print("   • Directory structure guide") 
        print("   • Testing procedures")
        print("   • Deployment checklist")
        print("   • Troubleshooting guide")
        print("   • Quick reference commands")
    else:
        print("\n❌ PDF generation failed. Please check the error above.")
