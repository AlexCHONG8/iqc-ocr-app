import sys
import os
from pprint import pprint

# Add src to path to import OCRService
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from ocr_service import OCRService

def run_test():
    print("🚀 Initializing OCR Service...")
    service = OCRService()
    
    file_path = "/Users/alexchong/Desktop/AI  projects/6SPC/Scan PDF/AJ26010702驱动棘轮AJR26010702原材料进货检验记录9-60.pdf"
    print(f"📄 Processing file: {file_path}")
    
    try:
        # This will upload to tmpfiles, send to MinerU, wait for zip, and parse the HTML
        results = service.extract_table_data(file_path)
        
        if not results:
            print("❌ Extracted results are Empty/None!")
            return
            
        print(f"✅ Successfully completed extraction. Found {len(results)} Dimension Sets.")
        
        # Print summary of each dimension
        for i, dim_data in enumerate(results):
            header = dim_data["header"]
            measurements = dim_data["measurements"]
            print(f"\n--- Dimension {i+1}: {header['dimension_name']} ---")
            print(f"Batch: {header['batch_id']}")
            print(f"USL: {header['usl']} | LSL: {header['lsl']}")
            if header.get('batch_size'):
                print(f"Batch Size: {header['batch_size']}")
                
            print(f"Extracted {len(measurements)} data points.")
            print(f"First 5: {measurements[:5]}")
            print(f"Last 5: {measurements[-5:]}")
            
    except Exception as e:
        print(f"❌ Error during backend extraction: {e}")

if __name__ == "__main__":
    run_test()
