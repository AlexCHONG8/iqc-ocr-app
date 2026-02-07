# ROOT CAUSE IDENTIFIED: Markdown vs HTML Table Format Mismatch

> **CRITICAL BUG FOUND**: The parser expects HTML `<table>` tags but MinerU outputs Markdown tables with pipe syntax!

**Date:** 2026-02-07
**Status:** Root Cause Identified
**Severity:** HIGH - All table parsing is failing

---

## The Problem

### What the Code Expects

**Location:** `app.py:535-574` (`parse_html_tables_for_dimensions`)

The function is named `parse_html_tables` and expects:
```html
<table>
  <tr><td>检验位置</td><td>1</td><td>11</td></tr>
  <tr><td>检验标准</td><td>27.80±0.10</td><td>6.00±0.10</td></tr>
  <tr><td>1</td><td>27.85</td><td>6.02</td></tr>
</table>
```

Uses regex: `r'<table>(.*?)</table>'` to find tables

### What MinerU Actually Outputs

**Format:** Markdown tables with pipe `|` syntax

```markdown
| 检验位置 | 1 | 11 | 13 |
|----------|---|----|----|
| **检验标准** | 27.80+0.10-0.00(mm) | Φ6.00±0.10(mm) | 73.20+0.00-0.15(mm) |
| 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
| 2 | 27.84 | OK | 6.02 | OK | 73.12 | OK |
```

**OR** sometimes HTML tables in markdown (depends on PDF structure and OCR settings)

---

## Root Cause Analysis

### Issue 1: Format Mismatch

The code uses HTML regex patterns:
```python
table_pattern = r'<table>(.*?)</table>'
row_pattern = r'<tr>(.*?)</tr>'
cell_pattern = r'<td[^>]*>(.*?)</td>'
```

But MinerU outputs Markdown tables:
```
| col1 | col2 | col3 |
|-----|------|------|
```

### Issue 2: Column Mapping Logic Wrong (Secondary Bug)

Even when HTML tables exist, the column mapping assumes:
- Spec row and data row have SAME column structure
- Code: `data_col_idx = spec_col_idx`

But actual structure is:
- Spec row: `[label, spec1, spec2, spec3]`
- Data row: `[seq, val1, status1, val2, status2, val3, status3]`

Correct mapping should be: `data_col_idx = 1 + spec_col_idx * 2`

---

## The Fix Strategy

### Option A: Add Markdown Table Parser (RECOMMENDED)

Create a dual-parser that handles BOTH formats:

```python
def parse_tables_from_markdown(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse both Markdown and HTML tables from OCR output.
    """
    # First try HTML tables (existing logic)
    html_tables = parse_html_tables(markdown_text)

    # Then try Markdown tables (new logic)
    md_tables = parse_markdown_tables(markdown_text)

    # Return combined results
    return html_tables + md_tables

def parse_markdown_tables(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse Markdown tables with pipe syntax.

    Format:
    | header1 | header2 | header3 |
    |---------|---------|---------|
    | row1col1| row1col2| row1col3|
    """
    import re

    tables = []

    # Find markdown table blocks
    # Match lines with |...| pattern
    lines = markdown_text.split('\n')
    i = 0

    while i < len(lines):
        # Find potential table start (line with | separator)
        if '|' not in lines[i]:
            i += 1
            continue

        # Collect table rows
        table_rows = []
        while i < len(lines) and '|' in lines[i]:
            # Remove leading/trailing whitespace and |
            row = lines[i].strip()
            if row.startswith('|'):
                row = row[1:]  # Remove leading |
            if row.endswith('|'):
                row = row[:-1]  # Remove trailing |

            # Split by | and clean cells
            cells = [cell.strip() for cell in row.split('|')]
            if cells:  # Only add non-empty rows
                table_rows.append(cells)
            i += 1

        # Need at least 4 rows: position, spec, header, data
        if len(table_rows) >= 4:
            # Extract dimensions from table
            dimensions = extract_dimensions_from_table(table_rows)
            tables.extend(dimensions)

    return tables
```

### Option B: Convert Markdown to HTML First

Use a markdown library to convert to HTML, then use existing parser:

```python
import markdown

def parse_html_tables_for_dimensions(markdown_text: str) -> List[Dict[str, Any]]:
    # Convert markdown to HTML
    html = markdown.markdown(markdown_text)

    # Use existing HTML parser
    return parse_html_table_tags(html)
```

**Pros:** Reuses existing logic
**Cons:** Requires adding `markdown` library dependency

---

## Implementation Plan (TDD Approach)

### Phase 1: Markdown Table Parser Tests

**Create:** `test_markdown_table_parsing.py`

```python
#!/usr/bin/env python3
"""Tests for Markdown table parsing."""

import unittest
from app import parse_tables_from_markdown

class TestMarkdownTableParsing(unittest.TestCase):
    """Test Markdown table extraction."""

    def test_markdown_table_with_3_dimensions(self):
        """Should parse Markdown table with pipe syntax."""
        markdown = """
        | 检验位置 | 1 | 11 | 13 |
        |----------|---|----|----|
        | **检验标准** | 27.80±0.10 | Φ6.00±0.10 | 73.20±0.15 |
        | 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
        | 2 | 27.84 | OK | 6.02 | OK | 73.12 | OK |
        """

        dimensions = parse_tables_from_markdown(markdown)
        self.assertEqual(len(dimensions), 3)

    def test_mixed_markdown_and_html_tables(self):
        """Should handle both formats in same document."""
        markdown = """
        <table>
        <tr><td>检验位置</td><td>1</td></tr>
        <tr><td>检验标准</td><td>10±1</td></tr>
        <tr><td>1</td><td>10.5</td></tr>
        </table>

        | 检验位置 | 2 |
        | **检验标准** | 20±2 |
        | 1 | 20.3 |
        """

        dimensions = parse_tables_from_markdown(markdown)
        self.assertEqual(len(dimensions), 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

### Phase 2: Implement Markdown Parser

**Location:** `app.py:535` (add new function)

**Steps:**
1. Write failing test (confirm it fails)
2. Implement `parse_markdown_tables()`
3. Implement `parse_tables_from_markdown()` wrapper
4. Fix column mapping logic
5. Run tests to confirm passing

### Phase 3: Fix Column Mapping

**Current (WRONG):**
```python
data_col_idx = spec_col_idx  # Assumes same structure
```

**Correct:**
```python
# Data row has pattern: [seq, val1, status1, val2, status2, ...]
# Spec row has pattern: [label, spec1, spec2, spec3, ...]
# So spec at column i maps to data at column 1 + i*2

data_col_idx = 1 + spec_col_idx * 2
```

Wait, that's not quite right either. Let me think...

Actually, looking at the real structure:
- Spec row columns: [0]=label, [1]=spec1, [2]=spec2, [3]=spec3
- Data row columns: [0]=seq, [1]=val1, [2]=status1, [3]=val2, [4]=status2, [5]=val3, [6]=status3

So spec at column 1 → data at column 1 (first value)
Spec at column 2 → data at column 3 (second value, skipping status)
Spec at column 3 → data at column 5 (third value, skipping status)

Pattern: `data_col_idx = 1 + (spec_col_idx - 1) * 2`
Or: `data_col_idx = spec_col_idx * 2 - 1`

Let me verify:
- Spec 1: 1*2-1 = 1 ✓
- Spec 2: 2*2-1 = 3 ✓
- Spec 3: 3*2-1 = 5 ✓

Yes! That's the correct formula.

---

## Complete Fix Code

### New Function: Parse Markdown Tables

```python
def parse_markdown_tables(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse Markdown tables with pipe | syntax.

    Handles format:
    | header1 | header2 | header3 |
    |---------|---------|---------|
    | data1   | data2   | data3   |
    """
    import re

    dimensions = []
    lines = markdown_text.split('\n')

    i = 0
    while i < len(lines):
        # Find table start (line with |)
        if '|' not in lines[i]:
            i += 1
            continue

        # Check if this looks like an inspection table
        # by looking ahead a few lines
        table_lines = []
        j = i
        while j < len(lines) and '|' in lines[j]:
            table_lines.append(lines[j])
            j += 1

        # Need minimum rows: position, separator, spec, 3+ data rows
        if len(table_lines) < 6:
            i = j
            continue

        # Parse table into cells
        table_data = []
        for line in table_lines:
            # Remove leading/trailing |
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]

            # Split by | and clean
            cells = [cell.strip() for cell in line.split('|')]
            if cells:
                table_data.append(cells)

        # Extract dimensions using same logic as HTML parser
        dims = extract_dimensions_from_table_data(table_data)
        dimensions.extend(dims)

        i = j  # Move past this table

    return dimensions
```

### Fixed Function: Correct Column Mapping

```python
def extract_dimensions_from_table_data(table_data: List[List[str]]) -> List[Dict[str, Any]]:
    """Extract dimension data from parsed table cells."""

    # ... [existing position/spec row detection logic] ...

    # NEW CORRECT LOGIC:
    # Data rows: [seq, val1, status1, val2, status2, val3, status3, ...]
    # Spec columns: [1, 2, 3] (spec1, spec2, spec3)

    measurement_sets = [[] for _ in specs]

    for row in table_data[data_start_idx:]:
        if not row or not row[0].isdigit():
            continue

        # Extract measurements using CORRECT column mapping
        for i, spec_col_idx in enumerate(spec_col_indices):
            # CORRECT FORMULA: data_col = spec_col * 2 - 1
            # Because data rows alternate: value, status, value, status, ...
            data_col_idx = spec_col_idx * 2 - 1

            if data_col_idx < len(row):
                val_str = row[data_col_idx]
                try:
                    val = float(val_str)
                    measurement_sets[i].append(val)
                except ValueError:
                    pass

    # ... [rest of dimension creation logic] ...
```

---

## Verification Steps

1. **Write TDD test** with real Markdown table format
2. **Confirm test fails** with current code
3. **Implement Markdown parser** (new function)
4. **Fix column mapping** formula
5. **Run test** to confirm it passes
6. **Test with real data** from deployed app
7. **Deploy and verify** all 3 dimensions show up

---

## Files to Modify

1. **app.py:535-650** - Add Markdown parser, fix column mapping
2. **test_markdown_table_parsing.py** - New TDD tests
3. **README.md** - Document Markdown table support
4. **CLAUDE.md** - Update architecture notes

---

## Success Criteria

- ✅ Parses Markdown tables with pipe syntax
- ✅ Parses HTML tables (backward compatible)
- ✅ Correctly maps spec columns to data columns
- ✅ Extracts all 3 (or more) dimensions
- ✅ Works with real MinerU output format
- ✅ TDD tests pass
- ✅ Real IQC report shows all measurement points

---

**Next Action:** Implement the fix following TDD methodology
