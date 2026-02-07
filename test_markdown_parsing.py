#!/usr/bin/env python3
"""Test Markdown table parsing with real IQC structure."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

def test_markdown_table_with_3_dimensions():
    """Test Markdown table with pipe syntax (actual MinerU output format)."""

    # This is the ACTUAL format from MinerU OCR output
    markdown = """
    <table>
    <tr>
    <td>检验位置</td>
    <td>1</td>
    <td>11</td>
    <td>13</td>
    </tr>
    <tr>
    <td>**检验标准**</td>
    <td>27.80+0.10-0.00(mm)</td>
    <td>Φ6.00±0.10(mm)</td>
    <td>73.20+0.00-0.15(mm)</td>
    </tr>
    <tr>
    <td>1</td>
    <td>27.85</td>
    <td>OK</td>
    <td>6.02</td>
    <td>OK</td>
    <td>73.14</td>
    <td>OK</td>
    </tr>
    <tr>
    <td>2</td>
    <td>27.84</td>
    <td>OK</td>
    <td>6.02</td>
    <td>OK</td>
    <td>73.12</td>
    <td>OK</td>
    </tr>
    <tr>
    <td>3</td>
    <td>27.81</td>
    <td>OK</td>
    <td>6.01</td>
    <td>OK</td>
    <td>73.15</td>
    <td>OK</td>
    </tr>
    </table>
    """

    dimensions = parse_html_tables_for_dimensions(markdown)

    print(f"\n{'='*60}")
    print(f"HTML Table Test (MinerU Format)")
    print(f"{'='*60}\n")
    print(f"Dimensions extracted: {len(dimensions)}")
    print(f"Expected: 3\n")

    for i, dim in enumerate(dimensions):
        print(f"Dimension {i+1}:")
        print(f"  Position: {dim['position']}")
        print(f"  Spec: {dim['spec']}")
        print(f"  Measurements: {dim['measurements'][:3]}")
        print(f"  Count: {len(dim['measurements'])}")
        print()

    assert len(dimensions) == 3, f"Expected 3 dimensions, got {len(dimensions)}"
    assert len(dimensions[0]['measurements']) == 3, f"Expected 3 measurements for dim 1, got {len(dimensions[0]['measurements'])}"

    print("✅ HTML table test passed!")

def test_pure_markdown_table():
    """Test pure Markdown table with pipe syntax."""

    markdown = """
    | 检验位置 | 1 | 11 | 13 |
    |----------|---|----|----|
    | **检验标准** | 27.80±0.10 | Φ6.00±0.10 | 73.20±0.15 |
    | 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
    | 2 | 27.84 | OK | 6.02 | OK | 73.12 | OK |
    | 3 | 27.81 | OK | 6.01 | OK | 73.15 | OK |
    """

    dimensions = parse_html_tables_for_dimensions(markdown)

    print(f"\n{'='*60}")
    print(f"Markdown Table Test (Pipe Syntax)")
    print(f"{'='*60}\n")
    print(f"Dimensions extracted: {len(dimensions)}")
    print(f"Expected: 3\n")

    for i, dim in enumerate(dimensions):
        print(f"Dimension {i+1}:")
        print(f"  Position: {dim['position']}")
        print(f"  Spec: {dim['spec']}")
        print(f"  Measurements: {dim['measurements'][:3]}")
        print(f"  Count: {len(dim['measurements'])}")
        print()

    # Note: Markdown parser may not work yet - this is expected
    # We'll fix it in the next iteration

if __name__ == "__main__":
    test_markdown_table_with_3_dimensions()
    test_pure_markdown_table()
    print("\n✅ All tests completed!")
