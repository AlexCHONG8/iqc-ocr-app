# Fix OCR Extraction and Add PDF Export - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix OCR data extraction to correctly identify all 3 point measurements (currently only 2) and convert HTML report export to PDF format.

**Architecture:**
- **Bug Fix**: The `spec_col_idx` variable is captured but ignored, causing incorrect column mapping between specs and measurement data
- **PDF Export**: Use WeasyPrint library to convert HTML reports to PDF with proper Chinese font support

**Tech Stack:** Python 3.10+, unittest (TDD), WeasyPrint (PDF generation), Streamlit

---

## Root Cause Analysis

### Bug #1: Incorrect Column Mapping in OCR Extraction

**Location:** `/Users/alexchong/AI/MinerU/app.py:634-637`

**Current Code:**
```python
for i, spec_col_idx in enumerate(spec_col_indices):
    # Calculate the data column index based on spec position
    # spec at column j corresponds to data at column 1 + j*2
    data_col_idx = 1 + i * 2  # BUG: Uses i instead of spec_col_idx
```

**Problem:** The variable `spec_col_idx` is captured but never used. The code assumes a fixed pattern `1 + i * 2` which doesn't account for:
- Empty columns in the spec row
- Non-contiguous spec columns
- Actual table structure from OCR

**Expected Behavior:** Use the actual column index from `spec_col_indices` to calculate the data column position.

---

## Task 1: Write Failing Test for Column Mapping Bug

**Files:**
- Create: `/Users/alexchong/AI/MinerU/test_ocr_extraction.py`

**Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for OCR table extraction - Column mapping bug fix."""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import parse_html_tables_for_dimensions

class TestOCRColumnMapping(unittest.TestCase):
    """Test that spec columns are correctly mapped to data columns."""

    def test_three_measurements_with_noncontiguous_specs(self):
        """
        Should extract all 3 measurements when spec columns are non-contiguous.

        Table structure (simulating OCR output):
        | 序号 | 位置1 |   | 位置2 | 位置3 |
        | 检验标准 | 27.85±0.5 |   | 15.2±0.3 | 8.0±0.2 |
        | 1 | 27.85 | OK | 15.3 | OK | 8.1 | OK |
        | 2 | 27.90 | OK | 15.1 | OK | 8.0 | OK |
        | 3 | 27.80 | OK | 15.2 | OK | 7.9 | OK |
        | 4 | 27.85 | OK | 15.3 | OK | 8.0 | OK |
        | 5 | 27.88 | OK | 15.2 | OK | 8.1 | OK |
        """
        markdown = """
        <table>
        <tr>
        <td>序号</td>
        <td>位置1</td>
        <td></td>
        <td>位置2</td>
        <td>位置3</td>
        </tr>
        <tr>
        <td>检验标准</td>
        <td>27.85±0.5</td>
        <td></td>
        <td>15.2±0.3</td>
        <td>8.0±0.2</td>
        </tr>
        <tr>
        <td>1</td>
        <td>27.85</td>
        <td>OK</td>
        <td>15.3</td>
        <td>8.1</td>
        </tr>
        <tr>
        <td>2</td>
        <td>27.90</td>
        <td>OK</td>
        <td>15.1</td>
        <td>8.0</td>
        </tr>
        <tr>
        <td>3</td>
        <td>27.80</td>
        <td>OK</td>
        <td>15.2</td>
        <td>7.9</td>
        </tr>
        <tr>
        <td>4</td>
        <td>27.85</td>
        <td>OK</td>
        <td>15.3</td>
        <td>8.0</td>
        </tr>
        <tr>
        <td>5</td>
        <td>27.88</td>
        <td>OK</td>
        <td>15.2</td>
        <td>8.1</td>
        </tr>
        </table>
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        # Should find 3 dimensions
        self.assertEqual(len(dimensions), 3,
                        f"Expected 3 dimensions, got {len(dimensions)}")

        # Verify first dimension (位置1)
        self.assertEqual(dimensions[0]['position'], '位置 1')
        self.assertEqual(dimensions[0]['spec'], '27.85±0.5')
        self.assertEqual(len(dimensions[0]['measurements']), 5)
        self.assertAlmostEqual(dimensions[0]['measurements'][0], 27.85, places=1)

        # Verify second dimension (位置2)
        self.assertEqual(dimensions[1]['position'], '位置 2')
        self.assertEqual(dimensions[1]['spec'], '15.2±0.3')
        self.assertEqual(len(dimensions[1]['measurements']), 5)
        self.assertAlmostEqual(dimensions[1]['measurements'][0], 15.3, places=1)

        # Verify third dimension (位置3)
        self.assertEqual(dimensions[2]['position'], '位置 3')
        self.assertEqual(dimensions[2]['spec'], '8.0±0.2')
        self.assertEqual(len(dimensions[2]['measurements']), 5)
        self.assertAlmostEqual(dimensions[2]['measurements'][0], 8.1, places=1)

    def test_spec_column_with_gap(self):
        """
        Should correctly map data columns when there's a gap in spec columns.

        This tests the actual bug: spec at column 1, 3, 4 should map to
        data at corresponding positions, not use 1+i*2 pattern.
        """
        markdown = """
        <table>
        <tr><td>检验标准</td><td>10±1</td><td></td><td>20±2</td><td>30±3</td></tr>
        <tr><td>1</td><td>10.5</td><td>OK</td><td>20.3</td><td>30.1</td></tr>
        <tr><td>2</td><td>10.2</td><td>OK</td><td>20.1</td><td>30.2</td></tr>
        <tr><td>3</td><td>10.3</td><td>OK</td><td>20.2</td><td>30.0</td></tr>
        <tr><td>4</td><td>10.1</td><td>OK</td><td>20.4</td><td>30.3</td></tr>
        <tr><td>5</td><td>10.4</td><td>OK</td><td>20.0</td><td>30.1</td></tr>
        </table>
        """

        dimensions = parse_html_tables_for_dimensions(markdown)

        # Should find 3 dimensions
        self.assertEqual(len(dimensions), 3,
                        "Should extract all 3 dimensions despite column gap")

        # Each should have 5 measurements
        for i, dim in enumerate(dimensions):
            self.assertEqual(len(dim['measurements']), 5,
                           f"Dimension {i+1} should have 5 measurements")

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/alexchong/AI/MinerU
python test_ocr_extraction.py
```

**Expected:** FAIL - Test should fail because current code only extracts 2 dimensions instead of 3

**Step 3: Write minimal implementation**

Edit `/Users/alexchong/AI/MinerU/app.py` lines 634-637:

```python
# BEFORE (buggy):
for i, spec_col_idx in enumerate(spec_col_indices):
    data_col_idx = 1 + i * 2  # Wrong: ignores actual column position

# AFTER (fixed):
for i, spec_col_idx in enumerate(spec_col_indices):
    # Map spec column to data row using the same relative position
    # Data rows have same column structure as spec row
    # spec_col_idx is the actual column in the spec row
    # Need to find the corresponding data column
    # The spec row structure is: [label, spec1, status1, spec2, status2, ...]
    # The data row structure is: [seq, val1, status1, val2, status2, ...]
    # So if spec is at column j, data is at column j
    data_col_idx = spec_col_idx
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/alexchong/AI/MinerU
python test_ocr_extraction.py
```

**Expected:** PASS - All 3 dimensions should be extracted correctly

**Step 5: Commit**

```bash
git add test_ocr_extraction.py app.py
git commit -m "fix: correct OCR column mapping to extract all 3 measurements

- Use spec_col_idx instead of 1+i*2 pattern
- Fixes bug where non-contiguous spec columns caused missing measurements
- Add TDD tests for column mapping scenarios"
```

---

## Task 2: Add PDF Export Functionality (TDD)

**Files:**
- Modify: `/Users/alexchong/AI/MinerU/app.py` (add PDF conversion)
- Create: `/Users/alexchong/AI/MinerU/test_pdf_export.py`
- Modify: `/Users/alexchong/AI/MinerU/requirements.txt` (add WeasyPrint)

**Step 1: Write the failing test**

Create `/Users/alexchong/AI/MinerU/test_pdf_export.py`:

```python
#!/usr/bin/env python3
"""Tests for PDF export functionality."""

import unittest
import tempfile
import os
from pathlib import Path

class TestPDFExport(unittest.TestCase):
    """Test HTML to PDF conversion."""

    def test_html_to_pdf_creates_file(self):
        """Should create a PDF file from HTML content."""
        # This will fail until we implement the function
        from app import convert_html_to_pdf

        html_content = """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body><h1>测试 PDF</h1><p>中文内容测试</p></body>
        </html>
        """

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name

        try:
            result = convert_html_to_pdf(html_content, output_path)
            self.assertTrue(result, "Should return True on success")
            self.assertTrue(os.path.exists(output_path), "PDF file should exist")
            self.assertGreater(os.path.getsize(output_path), 1000,
                             "PDF should have content")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_html_to_pdf_handles_chinese(self):
        """Should correctly render Chinese characters in PDF."""
        from app import convert_html_to_pdf

        html_content = """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body>
            <h1>检验位置测试结果</h1>
            <table>
                <tr><th>位置</th><th>测量值</th></tr>
                <tr><td>位置1</td><td>27.85</td></tr>
                <tr><td>位置2</td><td>15.20</td></tr>
                <tr><td>位置3</td><td>8.05</td></tr>
            </table>
        </body>
        </html>
        """

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = f.name

        try:
            result = convert_html_to_pdf(html_content, output_path)
            self.assertTrue(result)
            # Verify file is valid PDF (starts with %PDF)
            with open(output_path, 'rb') as f:
                header = f.read(4)
                self.assertEqual(header, b'%PDF', "Should be valid PDF file")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_html_to_pdf_handles_errors(self):
        """Should return False on conversion failure."""
        from app import convert_html_to_pdf

        # Invalid HTML
        result = convert_html_to_pdf("", "/invalid/path/test.pdf")
        self.assertFalse(result, "Should return False for invalid input")

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/alexchong/AI/MinerU
python test_pdf_export.py
```

**Expected:** FAIL with "ImportError: cannot import name 'convert_html_to_pdf'"

**Step 3: Add WeasyPrint to requirements**

Edit `/Users/alexchong/AI/MinerU/requirements.txt`:

```txt
# Existing dependencies...
streamlit>=1.28.0
requests>=2.31.0

# Add PDF generation
weasyprint>=60.0
```

**Step 4: Install WeasyPrint**

```bash
pip install weasyprint
```

**Step 5: Write minimal implementation**

Add to `/Users/alexchong/AI/MinerU/app.py`:

```python
def convert_html_to_pdf(html_content: str, output_path: str) -> bool:
    """
    Convert HTML content to PDF using WeasyPrint.

    Args:
        html_content: HTML string to convert
        output_path: Where to save the PDF file

    Returns:
        True if successful, False otherwise
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        # Configure font for Chinese character support
        font_config = FontConfiguration()

        # Create HTML object
        html_obj = HTML(string=html_content, encoding='utf-8')

        # Add default CSS for better rendering
        css = CSS(string='''
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: "PingFang SC", "Microsoft YaHei", "SimSun", sans-serif;
                font-size: 10pt;
            }
            table {
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 4px;
            }
        ''', font_config=font_config)

        # Render to PDF
        html_obj.write_pdf(
            output_path,
            stylesheets=[css],
            font_config=font_config
        )

        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"PDF conversion failed: {e}")
        return False
```

**Step 6: Update report download to use PDF**

Find the download section in `/Users/alexchong/AI/MinerU/app.py` (around line 800+) and modify:

```python
# Find the existing HTML download button
# Replace with PDF generation

# Generate PDF
pdf_filename = f"IQC_Report_{iqc_data['material_name']}_{iqc_data['batch_no']}.pdf"
with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
    pdf_path = tmp_file.name

if convert_html_to_pdf(html_report, pdf_path):
    with open(pdf_path, 'rb') as f:
        st.download_button(
            label="📥 Download PDF Report",
            data=f,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary"
        )
    os.unlink(pdf_path)
else:
    st.error("❌ Failed to generate PDF. Downloading HTML instead.")
    # Fallback to HTML download
    st.download_button(
        label="📥 Download HTML Report",
        data=html_report,
        file_name=html_filename,
        mime="text/html"
    )
```

**Step 7: Run test to verify it passes**

```bash
cd /Users/alexchong/AI/MinerU
python test_pdf_export.py
```

**Expected:** PASS - All tests should pass

**Step 8: Commit**

```bash
git add test_pdf_export.py app.py requirements.txt
git commit -m "feat: add PDF export with Chinese font support

- Implement convert_html_to_pdf() using WeasyPrint
- Add TDD tests for PDF generation
- Update download button to export PDF instead of HTML
- Support Chinese characters with proper font configuration"
```

---

## Task 3: End-to-End Testing

**Files:**
- Test: Manual testing in Streamlit

**Step 1: Run the app locally**

```bash
cd /Users/alexchong/AI/MinerU
streamlit run app.py
```

**Step 2: Upload a test PDF with 3 measurement points**

**Step 3: Verify extraction shows all 3 positions**

**Step 4: Verify PDF download generates valid PDF with Chinese characters**

**Step 5: Check that all measurements are present in the PDF**

---

## Task 4: Documentation Update

**Files:**
- Modify: `/Users/alexchong/AI/MinerU/docs/plans/2026-02-07-fix-md-link-retrieval.md` (update existing plan)
- Or: Create `/Users/alexchong/AI/MinerU/docs/plans/2026-02-07-fix-ocr-extraction-and-pdf-export.md` (this file)

**Add summary of changes:**

```markdown
## Completed Tasks

### Bug Fix: OCR Column Mapping (2026-02-07)
- **Issue**: Only 2 of 3 measurements extracted
- **Root Cause**: `spec_col_idx` variable captured but not used
- **Fix**: Use actual column index instead of `1+i*2` pattern
- **Test**: `test_ocr_extraction.py` with TDD approach

### Feature: PDF Export (2026-02-07)
- **Added**: WeasyPrint library for HTML to PDF conversion
- **Feature**: Chinese font support using system fonts
- **Test**: `test_pdf_export.py` with TDD approach
- **UI**: Changed download button from HTML to PDF
```

---

## Verification Checklist

Before marking work complete:

- [ ] TDD test for OCR extraction fails before fix
- [ ] OCR extraction fix passes all tests
- [ ] All 3 measurements correctly extracted from test data
- [ ] TDD test for PDF export fails before implementation
- [ ] PDF export implementation passes all tests
- [ ] PDF renders Chinese characters correctly
- [ ] Manual E2E test with real PDF shows 3 measurements
- [ ] PDF download produces valid PDF file
- [ ] All existing tests still pass
- [ ] No regression in existing functionality

---

## Next Steps (After This Plan)

1. Deploy to Streamlit Cloud
2. Configure MINERU_API_KEY in secrets
3. Share app URL with team
4. Collect feedback on PDF export and OCR accuracy
