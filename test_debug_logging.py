#!/usr/bin/env python3
"""Test with debug logging enabled to find the root cause."""

import sys
import os
import logging
sys.path.insert(0, os.path.dirname(__file__))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from app import parse_html_tables_for_dimensions

def test_with_real_file():
    """Test with the real IQC file and enable debug logging."""

    # Read the real IQC file
    real_file = "/Users/alexchong/AI/MinerU/output/20260122_111541.md"
    with open(real_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    print("=" * 60)
    print("Testing with real IQC file - DEBUG LOGGING ENABLED")
    print("=" * 60)
    print()

    # Parse dimensions
    dimensions = parse_html_tables_for_dimensions(markdown_text)

    print()
    print("=" * 60)
    print(f"Result: {len(dimensions)} dimensions extracted")
    print("=" * 60)

    for i, dim in enumerate(dimensions):
        print(f"\nDimension {i}:")
        print(f"  Type: {type(dim).__name__}")
        if isinstance(dim, dict):
            print(f"  Position: {dim.get('position')}")
            print(f"  Spec: {dim.get('spec')}")
            print(f"  Measurements: {len(dim.get('measurements', []))} values")
        else:
            print(f"  Value: {dim}")
            print(f"  ❌ NOT A DICT - THIS IS THE BUG!")

if __name__ == "__main__":
    test_with_real_file()
