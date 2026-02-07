#!/usr/bin/env python3
"""Debug test with real IQC table structure to identify the bug."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

def test_real_iqc_structure():
    """
    Test with the EXACT table structure from the real IQC report.

    The actual table has:
    - Header row: 检验位置 | 1 | 11 | 13
    - Spec row: **检验标准** | 27.80+0.10-0.00(mm) | Φ6.00±0.10(mm) | 73.20+0.00-0.15(mm)
    - Data rows: 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK

    Expected: spec_col_indices = [1, 2, 3]
    Data structure: [seq, val1, status1, val2, status2, val3, status3]
    """
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
    print(f"DEBUG: Real IQC Table Structure Test")
    print(f"{'='*60}\n")

    print(f"Number of dimensions extracted: {len(dimensions)}")
    print(f"Expected: 3 dimensions\n")

    for i, dim in enumerate(dimensions):
        print(f"Dimension {i+1}:")
        print(f"  Position: {dim['position']}")
        print(f"  Spec: {dim['spec']}")
        print(f"  Measurements: {dim['measurements'][:3]}... (showing first 3)")
        print(f"  Count: {len(dim['measurements'])} measurements")
        print()

    # Expected structure analysis
    print(f"\n{'='*60}")
    print(f"EXPECTED STRUCTURE:")
    print(f"{'='*60}")
    print(f"Spec row columns: [检验标准, 27.80+, Φ6.00±, 73.20+]")
    print(f"Spec column indices: [1, 2, 3]")
    print(f"\nData row columns: [1, 27.85, OK, 6.02, OK, 73.14, OK]")
    print(f"Data column indices: [0, 1, 2, 3, 4, 5, 6]")
    print(f"\nMapping needed:")
    print(f"  Spec at col 1 → Data at col 1 (value: 27.85)")
    print(f"  Spec at col 2 → Data at col 3 (value: 6.02)")
    print(f"  Spec at col 3 → Data at col 5 (value: 73.14)")
    print(f"\nPattern: data_col = spec_col * 2 - 1")
    print(f"  Spec 1: 1*2-1 = 1 ✓")
    print(f"  Spec 2: 2*2-1 = 3 ✓")
    print(f"  Spec 3: 3*2-1 = 5 ✓")
    print(f"{'='*60}\n")

    # Assertions
    assert len(dimensions) == 3, f"Expected 3 dimensions, got {len(dimensions)}"
    assert len(dimensions[0]['measurements']) == 3, "First dimension should have 3 measurements"

    print("✅ All assertions passed!")

if __name__ == "__main__":
    test_real_iqc_structure()
