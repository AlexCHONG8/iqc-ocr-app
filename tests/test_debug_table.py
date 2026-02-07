#!/usr/bin/env python3
"""Debug table parsing to see what's happening."""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(__file__))

def debug_table_parsing():
    """Debug the table parsing step by step."""

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
    </table>
    """

    print("Step 1: Extract tables")
    table_pattern = r'<table>(.*?)</table>'
    tables = re.findall(table_pattern, markdown, re.DOTALL)
    print(f"Found {len(tables)} table(s)")

    print("\nStep 2: Extract rows")
    table_content = tables[0]
    row_pattern = r'<tr>(.*?)</tr>'
    rows = re.findall(row_pattern, table_content, re.DOTALL)
    print(f"Found {len(rows)} rows")

    print("\nStep 3: Extract cells from each row")
    table_data = []
    for row_idx, row in enumerate(rows):
        cell_pattern = r'<td[^>]*>(.*?)</td>'
        cells = re.findall(cell_pattern, row, re.DOTALL)
        clean_cells = []
        for cell in cells:
            clean = re.sub(r'<[^>]+>', '', cell)
            clean = clean.strip()
            clean_cells.append(clean)
        table_data.append(clean_cells)
        print(f"Row {row_idx}: {clean_cells}")

    print("\nStep 4: Look for spec row")
    spec_row_idx = None
    for i, row in enumerate(table_data):
        if not row:
            continue
        print(f"  Checking row {i}: {row}")
        if any('检验标准' in cell or '标准' in cell for cell in row):
            print(f"    → Found spec row at index {i}")
            spec_row_idx = i
            break

    if spec_row_idx is None:
        print("ERROR: No spec row found!")
        return

    print("\nStep 5: Extract specs")
    spec_row = table_data[spec_row_idx]
    print(f"Spec row: {spec_row}")

    specs = []
    spec_col_indices = []
    for i in range(1, len(spec_row)):
        cell = spec_row[i]
        print(f"  Column {i}: '{cell}'")
        if re.search(r'[\d.]+[+\-±]', cell):
            spec_match = re.search(r'[\d.]+[+\-]?[\d.]*[+\-±]?[\d.]*', cell)
            if spec_match:
                print(f"    → Spec found: {spec_match.group(0)} at column {i}")
                specs.append(spec_match.group(0))
                spec_col_indices.append(i)

    print(f"\nTotal specs: {specs}")
    print(f"Spec column indices: {spec_col_indices}")

    print("\nStep 6: Extract data with column mapping")
    print(f"Formula: data_col_idx = spec_col_idx * 2 - 1")
    for i, spec_col_idx in enumerate(spec_col_indices):
        data_col_idx = spec_col_idx * 2 - 1
        print(f"  Spec {i+1} at column {spec_col_idx} → Data at column {data_col_idx}")

if __name__ == "__main__":
    debug_table_parsing()
