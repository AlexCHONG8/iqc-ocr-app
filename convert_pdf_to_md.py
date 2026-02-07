#!/usr/bin/env python3
"""
PDF to Markdown converter using PyMuPDF (fitz)
"""
import fitz  # PyMuPDF
import sys
import os
from pathlib import Path

def pdf_to_markdown(pdf_path, output_path=None):
    """Convert PDF to Markdown format"""
    pdf_path = Path(pdf_path)

    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.md"
    else:
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = output_path / f"{pdf_path.stem}.md"

    doc = fitz.open(pdf_path)
    md_content = []

    md_content.append(f"# {pdf_path.stem}\n\n")
    md_content.append(f"*Converted from PDF: {pdf_path.name}*\n\n---\n\n")

    for page_num, page in enumerate(doc, start=1):
        md_content.append(f"## Page {page_num}\n\n")

        # Extract text blocks
        blocks = page.get_text("blocks")
        for block in blocks:
            if block[6] == 0:  # Text block
                text = block[4]
                md_content.append(text + "\n\n")

        # Extract tables if any
        tables = page.find_tables()
        if tables:
            for table_idx, table in enumerate(tables):
                df = table.to_pandas()
                md_content.append(f"\n### Table {table_idx + 1}\n\n")
                md_content.append(df.to_markdown(index=False) + "\n\n")

        md_content.append("\n---\n\n")

    doc.close()

    # Write to file
    output_path.write_text("".join(md_content), encoding="utf-8")
    print(f"✅ Converted: {pdf_path} -> {output_path}")
    return str(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_pdf_to_md.py <pdf_file> [output_dir]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    pdf_to_markdown(pdf_file, output_dir)
