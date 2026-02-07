#!/usr/bin/env python3
"""
Convert HTML report to PDF using Playwright
Supports Chart.js rendered charts
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def html_to_pdf(html_path: str, pdf_path: str = None, wait_for_charts: bool = True):
    """
    Convert HTML file to PDF using Playwright
    
    Args:
        html_path: Path to HTML file
        pdf_path: Output PDF path (default: same name as HTML but .pdf)
        wait_for_charts: Wait for Chart.js to render
    """
    if not os.path.exists(html_path):
        print(f"Error: HTML file not found: {html_path}")
        return False
    
    if pdf_path is None:
        pdf_path = html_path.replace('.html', '.pdf')
    
    # Convert to absolute path with file:// protocol
    html_absolute = os.path.abspath(html_path)
    file_url = f"file://{html_absolute}"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Loading HTML: {html_path}")
        await page.goto(file_url, wait_until='networkidle')
        
        # Wait for Chart.js to render
        if wait_for_charts:
            print("Waiting for charts to render...")
            await page.wait_for_timeout(2000)  # Wait 2 seconds for charts
            # Also wait for canvas elements to be present
            try:
                await page.wait_for_selector('canvas', timeout=5000)
            except:
                pass
        
        # Generate PDF with A4 size
        print(f"Generating PDF: {pdf_path}")
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={
                'top': '10mm',
                'bottom': '10mm',
                'left': '10mm',
                'right': '10mm'
            }
        )
        
        await browser.close()
        print(f"✓ PDF generated successfully: {pdf_path}")
        return True

async def main():
    if len(sys.argv) < 2:
        # Default file
        html_file = "/Users/alexchong/AI/MinerU/IQC_Report_20260122.html"
    else:
        html_file = sys.argv[1]
    
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = await html_to_pdf(html_file, pdf_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
