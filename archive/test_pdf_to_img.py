import fitz
import sys
doc = fitz.open("sample_scan.pdf")
page = doc.load_page(0)
pix = page.get_pixmap(dpi=300)
pix.save("sample_scan_page0.jpg")
print("Saved sample_scan_page0.jpg successfully!")
