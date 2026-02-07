#!/usr/bin/env python3
"""Test with the real IQC file that revealed the split-table bug."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

def test_real_iqc_file():
    """Test with the actual file that showed only 2 dimensions."""

    real_file = "/Users/alexchong/AI/MinerU/output/20260122_111541.md"

    try:
        with open(real_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        print(f"Testing real IQC file: {real_file}")
        print(f"File size: {len(markdown_text)} characters\n")

        # Parse dimensions
        dimensions = parse_html_tables_for_dimensions(markdown_text)

        print("=" * 60)
        print(f"✅ SUCCESS: Extracted {len(dimensions)} dimensions")
        print("=" * 60)

        for i, dim in enumerate(dimensions):
            print(f"\nDimension {i+1}:")
            print(f"  Position: {dim['position']}")
            print(f"  Spec: {dim['spec']}")
            print(f"  Measurements: {len(dim['measurements'])} values")
            print(f"  First 3: {dim['measurements'][:3]}")

        print("\n" + "=" * 60)

        # Verify we got all 3 dimensions
        assert len(dimensions) == 3, f"Expected 3 dimensions, got {len(dimensions)}"

        # Verify each dimension has measurements
        for i, dim in enumerate(dimensions):
            assert len(dim['measurements']) >= 5, f"Dimension {i+1} has only {len(dim['measurements'])} measurements"

        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Real IQC file now correctly extracts all 3 dimensions!")
        print("=" * 60)

        return True

    except FileNotFoundError:
        print(f"❌ Error: File not found: {real_file}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_iqc_file()
    sys.exit(0 if success else 1)
