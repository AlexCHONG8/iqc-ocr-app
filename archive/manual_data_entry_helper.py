"""
Manual Data Entry Helper for IQC Pro Max
Use this when OCR extraction fails or you want to enter data manually from your QC inspection records.
"""

import sys
sys.path.insert(0, '/Users/alexchong/Desktop/AI  projects/6SPC')

from src.ocr_service import OCRService
from src.spc_engine import SPCEngine
import json

def create_manual_qc_data():
    """
    Creates dimension data from manual entry based on your QC inspection record.
    """

    print("="*70)
    print("IQC Pro Max - Manual Data Entry Helper")
    print("="*70)
    print("\nThis helps you enter data when OCR fails.")
    print("You'll need your QC inspection record (PDF/paper copy) ready.\n")

    # Example format for one dimension
    print("\n" + "="*70)
    print("EXAMPLE: How to enter your data")
    print("="*70)

    example = {
        "location": "1",  # 检验位置
        "name": "外径 Outer Diameter",  # Dimension name
        "usl": 27.90,  # Upper Specification Limit (from 检验标准: 27.80+0.10)
        "lsl": 27.80,  # Lower Specification Limit (27.80+0.00-0.00)
        "measurements": [
            # Enter your 50 measurements here
            27.85, 27.86, 27.84, 27.87, 27.85,
            27.83, 27.86, 27.85, 27.84, 27.86,
            27.85, 27.87, 27.84, 27.85, 27.83,
            27.86, 27.85, 27.84, 27.86, 27.85,
            27.87, 27.84, 27.85, 27.86, 27.83,
            27.85, 27.84, 27.86, 27.85, 27.87,
            27.84, 27.85, 27.86, 27.83, 27.85,
            27.86, 27.85, 27.84, 27.87, 27.85,
            27.84, 27.86, 27.85, 27.83, 27.86,
            27.85, 27.87, 27.84, 27.85, 27.86
        ]
    }

    print("\n📋 Example structure:")
    print(json.dumps(example, indent=2, ensure_ascii=False))

    print("\n" + "="*70)
    print("PARSING SPECS FROM QC REPORT")
    print("="*70)

    print("\nHow to parse specifications like these:")
    print("  • 27.80+0.10-0.00 → USL=27.90, LSL=27.80")
    print("  • Φ6.00±0.10 → USL=6.10, LSL=5.90")
    print("  • 73.20+0.00-0.15 → USL=73.20, LSL=73.05")

    print("\n" + "="*70)
    print("CREATE YOUR OWN DATA")
    print("="*70)

    # Template for user to fill
    template = {
        "dimensions": [
            {
                "location": "1",  # Change to your location number
                "name": "Dimension Name",  # e.g., "位置1 检验位置"
                "usl": 0.0,  # Enter USL value
                "lsl": 0.0,  # Enter LSL value
                "measurements": [
                    # Enter all 50 measurements here
                    # 0.0, 0.0, 0.0, ... (replace with actual values)
                ]
            }
        ]
    }

    print("\n📝 Copy this template and fill in your data:")
    print(json.dumps(template, indent=2, ensure_ascii=False))

    print("\n" + "="*70)
    print("HOW TO USE THIS DATA")
    print("="*70)

    print("""
Once you've filled in the template:

1. Save your data to a JSON file (e.g., my_data.json)

2. Load and process it:
   ```python
   from src.ocr_service import OCRService
   import json

   # Load your manual data
   with open('my_data.json', 'r') as f:
       manual_data = json.load(f)

   # Create dimension sets
   ocr = OCRService()
   dim_data = ocr.create_manual_entry(manual_data['dimensions'])

   # Now use dim_data with verify_ui.py or dashboard_generator.py
   ```

3. Or paste it directly into the Streamlit UI when OCR fails
    """)

def create_sample_from_pdf_description():
    """
    Creates sample data based on typical Chinese QC inspection report format.
    """
    print("\n" + "="*70)
    print("SAMPLE: Multi-Location QC Report")
    print("="*70)

    # Typical 3-location inspection report
    sample_data = {
        "dimensions": [
            {
                "location": "1",
                "name": "检验位置1 Position 1",
                "usl": 27.90,
                "lsl": 27.80,
                "measurements": [27.85 + (i*0.001) for i in range(50)]  # Example: 50 measurements
            },
            {
                "location": "11",
                "name": "Φ检验位置11 Position 11",
                "usl": 6.10,
                "lsl": 5.90,
                "measurements": [6.00 + (i*0.0005) for i in range(50)]
            },
            {
                "location": "13",
                "name": "检验位置13 Position 13",
                "usl": 73.20,
                "lsl": 73.05,
                "measurements": [73.12 + (i*0.0008) for i in range(50)]
            }
        ]
    }

    print("\n📊 Sample multi-location data:")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))

    print("\n" + "="*70)
    print("TESTING THE SAMPLE DATA")
    print("="*70)

    # Test with SPC engine
    ocr = OCRService()
    dim_data = ocr.create_manual_entry(sample_data['dimensions'])

    for i, dim in enumerate(dim_data):
        print(f"\nDimension {i+1}:")
        print(f"  Name: {dim['header']['dimension_name']}")
        print(f"  USL: {dim['header']['usl']}, LSL: {dim['header']['lsl']}")
        print(f"  Measurements: {len(dim['measurements'])} points")

        # Calculate SPC stats
        engine = SPCEngine(usl=dim['header']['usl'], lsl=dim['header']['lsl'])
        stats = engine.calculate_stats(dim['measurements'])

        print(f"  Mean: {stats['mean']:.4f}")
        print(f"  Cpk: {stats['cpk']:.3f} ({stats['cpk_status']})")

if __name__ == "__main__":
    create_manual_qc_data()
    print("\n" + "="*70 + "\n")
    create_sample_from_pdf_description()
