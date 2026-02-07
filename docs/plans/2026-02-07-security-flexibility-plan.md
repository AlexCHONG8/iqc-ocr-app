# Security & Flexibility Enhancement Plan

> **For Claude:** Use this plan to implement security (file auto-deletion) and validate flexibility (variable dimensions) features.

**Created:** 2026-02-07
**Status:** Ready for Implementation
**Priority:** High (Security) + Medium (Validation)

---

## Executive Summary

**Good News:** The app **already supports flexible dimensions** (1-7+ measurement points)! The column detection logic uses dynamic arrays (`spec_col_indices`) that automatically detect ANY number of spec columns.

**Security Gap:** Uploaded files persist in Streamlit session storage and are never deleted, creating a privacy risk for inspection reports.

**What This Plan Addresses:**
1. ✅ **Security**: Auto-delete uploaded files after processing and when new files are uploaded
2. ✅ **Validation**: Confirm and test that 1-7+ dimensions work correctly
3. ✅ **User Experience**: Clear feedback about file handling and security

---

## Part 1: Security - File Auto-Deletion

### Current Issue

**Location:** `app.py:817-842` (upload section) and `app.py:910` (file processing)

**Problem:**
- Uploaded files are stored in `st.session_state.uploaded_file`
- PDF bytes are read and stored in memory during processing
- No cleanup occurs when:
  - Processing completes
  - User uploads a new file
  - User refreshes the page
  - Session ends

**Risk:** Sensitive inspection reports (dimensions, measurements, supplier data) remain accessible in session storage.

### Solution Design

#### 1.1 Immediate File Deletion After Processing

**Location:** `app.py:1040-1052` (after OCR completes)

**Implementation:**
```python
# After OCR processing completes, immediately delete file
if 'uploaded_file' in st.session_state:
    del st.session_state.uploaded_file

# Also clear PDF bytes from memory if stored
if 'pdf_bytes' in st.session_state:
    del st.session_state.pdf_bytes
```

#### 1.2 New Upload Cleanup

**Location:** `app.py:825` (when new file is uploaded)

**Implementation:**
```python
if uploaded_file:
    # Delete previous file if exists
    if 'uploaded_file' in st.session_state and 'file_path' in st.session_state:
        try:
            previous_file = Path(st.session_state.file_path)
            if previous_file.exists():
                previous_file.unlink()
                logger.info(f"Deleted previous file: {previous_file}")
        except Exception as e:
            logger.warning(f"Could not delete previous file: {e}")

    # Store new file
    st.session_state.uploaded_file = uploaded_file
```

#### 1.3 Session Reset on New Upload

**Location:** `app.py:825-840`

**Implementation:**
```python
if uploaded_file:
    # If user uploads a new file, clear all previous data
    if st.session_state.get('current_file_name') != uploaded_file.name:
        # Clear session state keys
        keys_to_clear = ['ocr_results', 'iqc_data', 'processing_complete']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        # Show security message
        st.info("🔒 Previous data cleared. Processing new file securely.")

    st.session_state.uploaded_file = uploaded_file
    st.session_state.current_file_name = uploaded_file.name
```

#### 1.4 Temporary File Handling

**Location:** `app.py:910-914` (MinerUClient.upload_pdf)

**Current Code:**
```python
pdf_bytes = uploaded_file.read()
upload_result = client.upload_pdf(pdf_bytes, uploaded_file.name)
```

**Enhanced Code:**
```python
# Use tempfile for automatic cleanup
import tempfile

try:
    # Create temporary file that auto-deletes
    with tempfile.NamedTemporaryFile(mode='wb', delete=True, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file.flush()

        # Read back for upload
        with open(tmp_file.name, 'rb') as f:
            pdf_bytes = f.read()

        upload_result = client.upload_pdf(pdf_bytes, uploaded_file.name)

finally:
    # Explicitly clear from memory
    del pdf_bytes
    if 'uploaded_file' in st.session_state:
        # Don't delete the object yet, but mark for cleanup
        st.session_state.file_pending_deletion = True
```

---

## Part 2: Flexibility - Variable Dimensions Validation

### Current State Analysis

**Good News:** The app is **already flexible** for 1-7+ dimensions!

**Evidence:**

1. **Dynamic Detection** (`app.py:598-608`):
```python
spec_col_indices = []  # Track which columns have specs

# Detects ALL spec columns dynamically (no hardcoded limit)
for i in range(1, len(spec_row)):
    if re.search(r'[\d.]+[+\-±]', cell):
        specs.append(spec_match.group(0))
        spec_col_indices.append(i)  # Appends to array - no size limit!
```

2. **Flexible Extraction** (`app.py:634-636`):
```python
# Loops through ALL detected spec columns
for i, spec_col_idx in enumerate(spec_col_indices):
    data_col_idx = spec_col_idx  # Works for ANY count
```

3. **Report Generation** (`iqc_template.html:167-190`):
```javascript
// forEach handles ANY number of dimensions
iqcData.dimensions.forEach((dim, idx) => {
    // Create charts for each dimension
});
```

### What Needs Validation

#### 2.1 Test Cases for Variable Dimensions

**Create:** `/Users/alexchong/AI/MinerU/test_variable_dimensions.py`

```python
#!/usr/bin/env python3
"""Tests for variable dimension count (1-7+ measurement points)."""

import unittest
from app import parse_html_tables_for_dimensions

class TestVariableDimensions(unittest.TestCase):
    """Test extraction with varying numbers of measurement points."""

    def test_single_dimension(self):
        """Should extract 1 measurement point."""
        markdown = """
        <table>
        <tr><td>检验标准</td><td>10±1</td></tr>
        <tr><td>1</td><td>10.5</td></tr>
        <tr><td>2</td><td>10.2</td></tr>
        </table>
        """
        dimensions = parse_html_tables_for_dimensions(markdown)
        self.assertEqual(len(dimensions), 1)

    def test_six_dimensions(self):
        """Should extract 6 measurement points."""
        markdown = """
        <table>
        <tr><td>检验标准</td><td>10±1</td><td>20±2</td><td>30±3</td><td>40±4</td><td>50±5</td><td>60±6</td></tr>
        <tr><td>1</td><td>10.5</td><td>20.3</td><td>30.1</td><td>40.2</td><td>50.1</td><td>60.4</td></tr>
        <tr><td>2</td><td>10.2</td><td>20.1</td><td>30.2</td><td>40.1</td><td>50.3</td><td>60.1</td></tr>
        </table>
        """
        dimensions = parse_html_tables_for_dimensions(markdown)
        self.assertEqual(len(dimensions), 6)

    def test_seven_dimensions(self):
        """Should extract 7 measurement points (edge case)."""
        markdown = """
        <table>
        <tr><td>检验标准</td><td>10±1</td><td>20±2</td><td>30±3</td><td>40±4</td><td>50±5</td><td>60±6</td><td>70±7</td></tr>
        <tr><td>1</td><td>10.5</td><td>20.3</td><td>30.1</td><td>40.2</td><td>50.1</td><td>60.4</td><td>70.2</td></tr>
        </table>
        """
        dimensions = parse_html_tables_for_dimensions(markdown)
        self.assertEqual(len(dimensions), 7)

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

#### 2.2 Report Layout Validation

**Issue:** HTML template uses 3-column grid layout (`grid-template-columns: repeat(3, 1fr)`)

**For 1-2 dimensions:** Works fine
**For 3 dimensions:** Perfect layout
**For 4-6 dimensions:** Acceptable (scrolling)
**For 7+ dimensions:** May need vertical scrolling optimization

**Recommendation:** Test with real 6-dimension PDF to ensure layout is usable.

#### 2.3 UI Improvements

**Location:** `app.py:1236-1320` (render_report_section)

**Add dimension count indicator:**
```python
# Show how many dimensions were detected
st.markdown(f"""
<div class="status-card success">
    <div>✅ Detected <strong>{len(iqc_data['dimensions'])}</strong> measurement points</div>
    <div style="font-size: 0.875rem; color: #64748b; margin-top: 4px;">
        All dimensions extracted successfully
    </div>
</div>
""", unsafe_allow_html=True)
```

---

## Part 3: Implementation Tasks

### Task 1: File Cleanup Implementation (High Priority)

**Files:**
- Modify: `app.py` (4 locations)
- Create: `test_file_cleanup.py` (TDD tests)

**Steps:**
1. Write TDD test for file deletion
2. Implement immediate cleanup after OCR
3. Implement new upload cleanup
4. Implement session reset on new file
5. Add logging for security audit

**Estimated Complexity:** Medium (2-3 hours)

### Task 2: Variable Dimensions Validation (Medium Priority)

**Files:**
- Create: `test_variable_dimensions.py`
- Modify: `app.py` (add dimension count indicator)

**Steps:**
1. Write TDD tests for 1, 3, 6, 7 dimensions
2. Run tests to confirm flexibility
3. Add dimension count indicator to UI
4. Test with real 6-dimension PDF

**Estimated Complexity:** Low (1 hour) - mostly validation

### Task 3: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Add:**
- Security & privacy section
- Variable dimensions capability
- File handling explanation

---

## Part 4: Testing Checklist

### Security Testing

- [ ] Upload file → Process → Verify file deleted from session
- [ ] Upload file A → Process → Upload file B → Verify A data cleared
- [ ] Check browser console for file references
- [ ] Verify no temp files remain after session
- [ ] Test with large files (50MB+)
- [ ] Test session timeout scenarios

### Flexibility Testing

- [ ] Test 1 dimension extraction
- [ ] Test 2 dimension extraction
- [ ] Test 3 dimension extraction (current baseline)
- [ ] Test 6 dimension extraction
- [ ] Test 7 dimension extraction
- [ ] Verify report generates correctly for all cases
- [ ] Verify charts render for all dimensions
- [ ] Verify statistical calculations work for all counts

### Integration Testing

- [ ] Upload 6-dimension PDF → Process → Verify all 6 extracted
- [ ] Upload 1-dimension PDF → Process → Verify single dimension works
- [ ] Verify file cleanup after each test
- [ ] Check memory usage doesn't grow with multiple uploads

---

## Part 5: Deployment Considerations

### Streamlit Cloud Specifics

**Session Storage:**
- Streamlit sessions persist for ~30 minutes of inactivity
- Files stored in `st.session_state` remain until session timeout
- Manual deletion required for immediate cleanup

**Temporary Files:**
- Streamlit Cloud filesystem is ephemeral
- Temp files auto-deleted on redeployment
- No persistent storage available

**Best Practices:**
1. Always delete files immediately after processing
2. Use `tempfile.NamedTemporaryFile(delete=True)`
3. Clear session state keys explicitly
4. Add security notices to UI

### Security Communication

**Add to App UI:**
```python
st.info("""
🔒 **Privacy & Security**
- Files are processed and immediately deleted
- No data stored on servers after processing
- Each new upload clears previous data
""")
```

---

## Part 6: Code Examples

### Complete File Cleanup Function

```python
def cleanup_uploaded_files():
    """
    Clean up all uploaded files and session data.

    Call this when:
    - New file is uploaded
    - Processing completes
    - User clicks "Clear Data"
    """
    import logging
    logger = logging.getLogger(__name__)

    # Clear uploaded file reference
    if 'uploaded_file' in st.session_state:
        del st.session_state.uploaded_file
        logger.info("Cleared uploaded_file from session")

    # Clear processing results
    keys_to_clear = [
        'ocr_results',
        'iqc_data',
        'pdf_bytes',
        'processing_complete',
        'file_pending_deletion'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            logger.debug(f"Cleared {key} from session")

    logger.info("File cleanup completed")
```

### Usage in Upload Section

```python
if uploaded_file:
    # New file detected - cleanup previous data
    if st.session_state.get('current_file_name') != uploaded_file.name:
        cleanup_uploaded_files()
        st.success("🔒 Previous data cleared securely")

    # Store new file
    st.session_state.uploaded_file = uploaded_file
    st.session_state.current_file_name = uploaded_file.name
```

---

## Part 7: Success Metrics

### Security Metrics

- ✅ Files deleted within 1 second of processing completion
- ✅ No files accessible after new upload
- ✅ Session state cleared between uploads
- ✅ Zero files remaining in temp storage

### Flexibility Metrics

- ✅ 1-7 dimensions tested and working
- ✅ Reports generate correctly for all dimension counts
- ✅ Charts render for any number of dimensions
- ✅ No hardcoded limits in code

### User Experience Metrics

- ✅ Clear feedback about data security
- ✅ Dimension count displayed to user
- ✅ Smooth transitions between uploads
- ✅ No performance degradation with multiple uploads

---

## Next Steps

1. **Immediate**: Implement file cleanup (Task 1)
2. **Short-term**: Validate variable dimensions (Task 2)
3. **Documentation**: Update README and CLAUDE.md (Task 3)
4. **Testing**: Run full test suite with 1-7 dimension samples
5. **Deploy**: Push to Streamlit Cloud and verify security measures

---

**Dependencies:**
- Python `tempfile` module (built-in)
- No additional packages required

**Risks:**
- Low: File cleanup logic is straightforward
- Low: Flexibility already exists, just needs validation
- Medium: Streamlit session management quirks

**Mitigation:**
- Comprehensive TDD test coverage
- Manual testing on Streamlit Cloud
- User acceptance testing with real inspection reports
