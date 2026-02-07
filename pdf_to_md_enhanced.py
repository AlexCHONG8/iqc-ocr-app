#!/usr/bin/env python3
"""
Enhanced PDF to Markdown converter with OCR fallback
"""
import fitz  # PyMuPDF
from pathlib import Path
import sys


def extract_pdf_with_ocr_fallback(pdf_path, output_path=None):
    """Convert PDF to Markdown with enhanced text extraction."""
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

    has_text = False
    for page_num, page in enumerate(doc, start=1):
        md_content.append(f"## Page {page_num}\n\n")

        # Try multiple text extraction methods
        text_methods = [
            ("text", page.get_text),
            ("blocks", lambda: page.get_text("blocks")),
            ("dict", lambda: page.get_text("dict")),
            ("html", lambda: page.get_text("html")),
        ]

        page_text = ""
        for method_name, method_func in text_methods:
            try:
                if method_name == "text":
                    result = method_func()
                elif method_name == "blocks":
                    blocks = method_func()
                    result = "\n\n".join([b[4] for b in blocks if b[6] == 0])
                elif method_name == "dict":
                    result = method_func().get("text", "")
                elif method_name == "html":
                    result = method_func()
                else:
                    continue

                if result and result.strip():
                    page_text = result
                    has_text = True
                    break
            except Exception:
                continue

        if page_text.strip():
            md_content.append(page_text + "\n\n")
        else:
            md_content.append(f"[Page {page_num} appears to be image-based - OCR required]\n\n")

        # Extract images info
        image_list = page.get_images()
        if image_list:
            md_content.append(f"\n*This page contains {len(image_list)} image(s)*\n\n")

        md_content.append("\n---\n\n")

    doc.close()

    output_path.write_text("".join(md_content), encoding="utf-8")

    if not has_text:
        print(f"⚠️  Warning: PDF appears to be image-based (scanned)")
        print(f"   For OCR conversion, install Tesseract: brew install tesseract")
        print(f"   Or use online OCR tools like https://www.onlineocr.net/")

    print(f"✅ Extracted: {pdf_path} -> {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_md_enhanced.py <pdf_file> [output_dir]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    extract_pdf_with_ocr_fallback(pdf_file, output_dir)
