#!/usr/bin/env python3
"""Debug test to check dimension data types."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

def test_dimension_types():
    """Test that all dimensions have the correct structure."""

    markdown = """
    | 检验位置 | 1 | 11 | 13 |
    |----------|---|----|----|
    | **检验标准** | 27.80+0.10-0.00 | Φ6.00±0.10 | 73.20+0.00-0.15 |

    | 结果序号 | 测试结果(1) | 判定 | 测试结果(11) | 判定 | 测试结果(13) | 判定 |
    |----------|-------------|------|--------------|------|--------------|------|
    | 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
    | 2 | 27.84 | OK | 6.02 | OK | 73.12 | OK |
    | 3 | 27.81 | OK | 6.01 | OK | 73.15 | OK |
    | 4 | 27.82 | OK | 6.01 | OK | 73.12 | OK |
    | 5 | 27.85 | OK | 6.06 | OK | 73.10 | OK |
    """

    dimensions = parse_html_tables_for_dimensions(markdown)

    print(f"Total dimensions: {len(dimensions)}")
    print()

    for i, dim in enumerate(dimensions):
        print(f"Dimension {i}:")
        print(f"  Type: {type(dim)}")
        print(f"  Is Dict: {isinstance(dim, dict)}")

        if isinstance(dim, dict):
            print(f"  Keys: {list(dim.keys())}")
            print(f"  Position: {dim.get('position')} (type: {type(dim.get('position')).__name__})")
            print(f"  Spec: {dim.get('spec')} (type: {type(dim.get('spec')).__name__})")
            print(f"  Measurements: {dim.get('measurements')} (type: {type(dim.get('measurements')).__name__})")
            if isinstance(dim.get('measurements'), list):
                print(f"  Measurements length: {len(dim.get('measurements'))}")
                print(f"  First measurement type: {type(dim.get('measurements')[0]).__name__ if dim.get('measurements') else 'N/A'}")
        else:
            print(f"  Value: {dim}")
            print(f"  This is NOT a dict! This is the bug!")

        print()

    # Check if all dimensions are dicts
    all_dicts = all(isinstance(dim, dict) for dim in dimensions)
    print(f"All dimensions are dicts: {all_dicts}")

    if not all_dicts:
        print("❌ BUG FOUND: Not all dimensions are dicts!")
        return False

    print("✅ All dimensions have correct structure")
    return True

if __name__ == "__main__":
    test_dimension_types()
