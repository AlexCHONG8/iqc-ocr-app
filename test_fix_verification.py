#!/usr/bin/env python3
"""Test HTML table parsing with enough data rows."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

def test_html_table_3_dimensions():
    """Test HTML table with 3 dimensions and 5+ data rows."""

    # Need at least 5 data rows for SPC analysis
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
    <tr><td>1</td><td>27.85</td><td>OK</td><td>6.02</td><td>OK</td><td>73.14</td><td>OK</td></tr>
    <tr><td>2</td><td>27.84</td><td>OK</td><td>6.02</td><td>OK</td><td>73.12</td><td>OK</td></tr>
    <tr><td>3</td><td>27.81</td><td>OK</td><td>6.01</td><td>OK</td><td>73.15</td><td>OK</td></tr>
    <tr><td>4</td><td>27.82</td><td>OK</td><td>6.01</td><td>OK</td><td>73.12</td><td>OK</td></tr>
    <tr><td>5</td><td>27.85</td><td>OK</td><td>6.06</td><td>OK</td><td>73.10</td><td>OK</td></tr>
    </table>
    """

    dimensions = parse_html_tables_for_dimensions(markdown)

    print(f"\n{'='*60}")
    print(f"Test Result: HTML Table with 3 Dimensions")
    print(f"{'='*60}\n")

    print(f"✅ Dimensions extracted: {len(dimensions)}")
    print(f"Expected: 3\n")

    for i, dim in enumerate(dimensions):
        print(f"Dimension {i+1}:")
        print(f"  Position: {dim['position']}")
        print(f"  Spec: {dim['spec']}")
        print(f"  Measurements: {dim['measurements'][:3]}... (showing first 3)")
        print(f"  Total measurements: {len(dim['measurements'])}")
        print()

    assert len(dimensions) == 3, f"Expected 3 dimensions, got {len(dimensions)}"
    assert len(dimensions[0]['measurements']) == 5, f"Expected 5 measurements, got {len(dimensions[0]['measurements'])}"

    # Verify the actual values
    assert abs(dimensions[0]['measurements'][0] - 27.85) < 0.01, "First measurement should be 27.85"
    assert abs(dimensions[1]['measurements'][0] - 6.02) < 0.01, "Second measurement should be 6.02"
    assert abs(dimensions[2]['measurements'][0] - 73.14) < 0.01, "Third measurement should be 73.14"

    print("✅ All assertions passed!")
    print("✅ All 3 dimensions correctly extracted with proper column mapping!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_html_table_3_dimensions()
