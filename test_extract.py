import sys
from src.ocr_service import OCRService

def test():
    ocr = OCRService()
    file_path = "Scan PDF/AJ26010702驱动棘轮AJR26010702原材料进货检验记录9-60.pdf"
    
    print(f"Extracting for {file_path}")
    data = ocr.extract_table_data(file_path)
    if data:
        print(f"Extracted {len(data)} dimensions")
        for i, d in enumerate(data):
            print(f"  Dim {i+1}: {d['header']['dimension_name']} - {len(d['measurements'])} points")
    else:
        print("No data extracted")

if __name__ == "__main__":
    test()
