# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **IQC (Incoming Quality Control) OCR + SPC Analysis** web application that processes handwritten inspection reports through OCR and generates ISO 13485 compliant statistical process control reports.

**Tech Stack:**
- **Frontend**: Streamlit web application (`app.py` - 2100+ lines)
- **OCR API**: MinerU.net (cloud-based PDF to Markdown conversion)
- **Statistical Analysis**: 6SPC calculations (Cp, Cpk, Pp, Ppk, Xbar-R charts)
- **Output**: HTML reports with Chart.js visualizations
- **Testing**: Python unittest framework

**Key Features:**
- Multi-language OCR support (109 languages including Chinese handwriting)
- Automatic extraction of measurement data from OCR-generated tables
- Supports both single-table and split-table OCR formats
- Statistical process control (SPC) with process capability indices
- PDF upload interface with real-time processing feedback
- Team access with optional password protection
- Comprehensive error handling and deployment diagnostics

## Development Commands

### Running the Application

```bash
# Local development
streamlit run app.py

# Install dependencies
pip install -r requirements.txt

# Run diagnostic tool (checks API key and connectivity)
python diagnose_api.py

# Run specific test
python -m unittest tests.test_split_table_format
python -m unittest tests.test_mineru_client

# Run all tests
python -m unittest discover -s tests -p "test_*.py"
```

### Deployment

```bash
# Deploy to Streamlit Cloud
# 1. Push code to GitHub
git push origin main

# 2. Configure secrets in Streamlit Cloud:
#    - MINERU_API_KEY (required, JWT token format)
#    - APP_PASSWORD (optional)
#
#    API key format: Should start with "eyJ" and be 300+ characters
#    Example: MINERU_API_KEY=eyJ0eXAiOiJKV1Q...
```

## Architecture

### Core Components

**1. MinerUClient Class (`app.py:298-537`)**
- Manages PDF upload to MinerU.net API
- Two-step upload process: POST for batch URL → PUT file to upload URL
- Polls task status during OCR processing
- Downloads converted markdown from CDN
- Handles ZIP extraction and error recovery
- Uses API key from environment variable `MINERU_API_KEY`
- **Critical**: When uploading, do NOT set Content-Type header for PUT request

**2. OCR Table Parsing (`app.py:539-1062`)**
This is the most complex part of the system, handling multiple OCR output formats:

- `parse_html_tables_for_dimensions()`: Main entry point for table parsing
- `fuzzy_extract_measurements()`: Fallback parser using regex patterns
- Supports BOTH HTML `<table>` and Markdown pipe `|` tables
- Supports BOTH single-table (specs+data) and split-table formats
- **Critical**: Column mapping must use actual column indices, not pattern-based indexing
- Handles Chinese inspection records with multiple measurement positions
- Parses specification strings (e.g., "27.85±0.5", "Φ6.00±0.10", "73.20+0.15-0.00")

Key helper functions:
- `_detect_table_type()`: Classify tables as SPECS_ONLY, DATA_TABLE, or COMPLETE
- `_parse_html_table_tags()`: Extract HTML tables from OCR output
- `_parse_markdown_tables()`: Extract Markdown pipe `|` tables
- `_extract_specs_from_table()`: Parse specs from specs-only tables
- `_extract_data_with_specs()`: Combine pending specs with data table
- `_extract_dimensions_from_table_data()`: Parse complete single-table format

**3. IQC Data Extraction (`app.py:1064-1323`)**
- `extract_iqc_data_from_markdown()`: Orchestrates full parsing workflow
- Extracts metadata: material name, batch number, inspection date, operator
- Returns structured data for statistical analysis
- **Critical**: Applies aggressive type filtering to prevent float contamination

**4. Statistical Analysis (`iqc-report/scripts/iqc_stats.py`)**
- `calculate_subgroups()`: Divides measurements into subgroups (default n=5)
- `calculate_process_capability()`: Computes Cp, Cpk, Pp, Ppk indices
- `calculate_control_limits()`: Xbar-R chart control limits (A2, D3, D4 constants)
- `generate_iqc_data()`: Master function producing complete IQC dataset
- `generate_html_report()`: Embeds data in HTML template with Chart.js
- **Note**: Dynamically imported due to hyphenated directory name

**5. Streamlit UI (`app.py:1324-2074`)**
- `render_header()`: Clinical precision branding with custom CSS
- `render_sidebar()`: Configuration and deployment health check panel
- `render_upload_section()`: File upload interface (max 200MB)
- `render_processing_section()`: OCR progress with status polling and error handling
- `render_data_extraction_section()`: Manual data review/editing
- `render_report_section()`: Statistical charts and PDF/HTML export
- `main()`: Application entry point with session state management

### Data Flow

```
PDF Upload → MinerU.net API → Poll Task Status → Download Markdown
→ Parse HTML/Markdown Tables → Extract Measurements → Calculate 6SPC Metrics
→ Generate HTML Report → Display Charts → Export PDF/HTML
```

### Key Integration Points

**MinerU.net API:**
- Base URL: `https://mineru.net/api/v4/`
- Two-step upload process:
  1. POST `/file-urls/batch` to get upload URLs and batch_id
  2. PUT file to the returned upload URL (no Content-Type header!)
- Status endpoint: GET `/tasks` to check processing status
- Response fields: `batch_id`, `state`, `full_md_link`, `full_zip_url`
- Use `full_md_link` if available, fallback to extracting ZIP from `full_zip_url`
- API key passed via Bearer token in Authorization header
- Accepts both JWT tokens ("eyJ...") and API keys ("sk-...")

**HTML Template:**
- Location: `iqc-report/assets/iqc_template.html`
- Uses Chart.js for interactive visualizations
- Embedded CSS for print-optimized layout
- Chinese font support: "PingFang SC", "Microsoft YaHei", "SimSun"

## Important Implementation Notes

### OCR Table Format Variations

The OCR table parser must handle multiple formats from MinerU.net:

**Format 1: Single Complete Table (specs + data together)**
```markdown
| 检验位置 | 1 | 11 | 13 |
| **检验标准** | 27.80±0.10 | Φ6.00±0.10 | 73.20±0.15 |
| 结果序号 | 测试结果(1) | 判定 | 测试结果(11) | 判定 | 测试结果(13) | 判定 |
| 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
```
- Detected as `COMPLETE` table type
- Parsed by `_extract_dimensions_from_table_data()`

**Format 2: Split Tables (specs separate from data)**
```markdown
# Table 1 (SPECS_ONLY)
| 检验位置 | 1 | 11 | 13 |
| **检验标准** | 27.80±0.10 | Φ6.00±0.10 | 73.20±0.15 |

# Table 2 (DATA_TABLE)
| 结果序号 | 测试结果(1) | 判定 | 测试结果(11) | 判定 | 测试结果(13) | 判定 |
| 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
```
- Table 1 detected as `SPECS_ONLY` → specs stored in `pending_specs`
- Table 2 detected as `DATA_TABLE` → combined with `pending_specs`
- Parsed by `_extract_data_with_specs()`

**Format 3: HTML Tables**
- Same logical structures as above, but using `<table>`, `<tr>`, `<td>` tags
- Parsed by `_parse_html_table_tags()` before type detection

**Critical Implementation Requirements:**
- Process tables sequentially with state tracking (`pending_specs`)
- Support both HTML and Markdown syntax in same parser
- Maintain backward compatibility with single-table format
- Handle position names like "1", "11", "13" (can be multi-digit)
- Parse specs like "27.85±0.5", "Φ6.00±0.10", "73.20+0.15-0.00"

### Recent Critical Bug Fixes

#### ✅ Split-Table Format Support (FIXED - 2026-02-07)
**Location:** `app.py:539-1062`

**Issue:** MinerU OCR outputs specs and data in TWO SEPARATE TABLES, but the parser expected them in one table.

**Root Cause:** The table parser only handled single-table format (specs + data together).

**Fix Applied:** Implemented multi-table format support with state tracking:
- Added table type detection system (`_detect_table_type()`)
- Added specs-only extraction (`_extract_specs_from_table()`)
- Added pending specs + data combination (`_extract_data_with_specs()`)
- Added HTML and Markdown table parsers
- Modified main parser to process tables sequentially with `pending_specs` state

**Test Coverage:** `tests/test_split_table_format.py` - TDD tests for split-table format (both Markdown and HTML)

**Impact:** Both single-table and split-table formats are now supported, with backward compatibility.

#### ✅ Column Mapping Bug (FIXED - 2026-02-07)
**Location:** `app.py:636`

**Issue:** The code previously used `data_col_idx = 1 + i * 2` which failed for non-contiguous spec columns.

**Root Cause:** Pattern-based calculation ignored actual column positions when tables had empty cells or gaps.

**Fix Applied:** Changed to use actual column index:
```python
# WRONG: Assumes fixed pattern
for i, spec_col_idx in enumerate(spec_col_indices):
    data_col_idx = 1 + i * 2  # Ignores actual column position

# CORRECT: Uses actual column mapping (FIXED)
for i, spec_col_idx in enumerate(spec_col_indices):
    data_col_idx = spec_col_idx  # Maps spec column to corresponding data column
```

**Test Coverage:** `tests/test_ocr_extraction.py` validates 3-column extraction with gaps.

**Impact:** All measurement points (not just 2) are now correctly extracted from tables with non-contiguous spec columns.

### Dynamic Module Loading

The `iqc-report` directory has a hyphen in the name, requiring dynamic import:

```python
iqc_stats_path = Path(__file__).parent / "iqc-report" / "scripts" / "iqc_stats.py"
spec = importlib.util.spec_from_file_location("iqc_stats", iqc_stats_path)
iqc_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iqc_stats)
```

### Session State Management

Streamlit's `st.session_state` requires careful handling for widget compatibility:
- Initialize state variables with `st.session_state.get('key', default)`
- Radio button compatibility: Use `index` parameter, not `default`
- Uploaded file: `.name` is a property, not method (use `uploaded_file.name` not `uploaded_file.name()`)
- Always clean up session state between file uploads to prevent stale data

### Type Safety in Dimensions Processing

**Critical:** The dimension extraction functions must return `List[Dict[str, Any]]` with strict type validation:
- Aggressive filtering at `app.py:596-605` removes non-dict items before adding to dimensions list
- All dimension dictionaries must have required keys: `position_name`, `nominal`, `usl`, `lsl`, `measurements`
- Float contamination (e.g., dimension = float instead of dict) causes downstream failures
- Always validate types after extraction: `isinstance(dim, dict)` before accessing keys

**Dimension Data Structure:**
```python
{
    "position_name": "1",           # Measurement position (string)
    "nominal": 27.85,               # Target value (float)
    "usl": 27.95,                   # Upper specification limit (float)
    "lsl": 27.75,                   # Lower specification limit (float)
    "measurements": [27.85, 27.83, ...],  # List of measurement values (List[float])
    "unit": "mm",                   # Optional unit (string)
}
```

**Common Pitfalls:**
- Forgetting to filter non-dict items before extending dimensions list
- Returning raw float values instead of wrapping in dimension dict
- Missing required keys in dimension dict
- Type mixing: `measurements` must be List[float], not List[str]

### Error Handling and Diagnostics

**Deployment Health Check:**
- Located in sidebar (`render_sidebar()`)
- Shows API key status: Configured/Short/Missing
- Displays environment info (Streamlit version, upload limits)
- Real-time session status indicators

**Error Categorization:**
- Upload Errors: Timeout (network/service), 401/Auth (API key), Connection (service down)
- Processing Errors: Timeout (too large/complex PDF), Failed (corrupt/unsupported PDF)
- Each error type has specific troubleshooting steps and user-friendly messages

**Diagnostic Tool (`diagnose_api.py`):**
- Tests API key validity and format
- Checks API connectivity
- Validates deployment configuration
- Provides actionable fix suggestions
- Run before deployment to verify setup

### Testing Patterns

Tests use Python's built-in `unittest` framework. Key test files:
- `tests/test_split_table_format.py`: Split-table format (HTML and Markdown)
- `tests/test_ocr_extraction.py`: Column mapping edge cases
- `tests/test_real_iqc_file.py`: End-to-end validation with actual IQC file
- `tests/test_mineru_client.py`: API interaction mocking
- `tests/test_debug_*.py`: Various debugging test files for specific issues

**TDD Workflow:**
```bash
# 1. Write failing test
# 2. Verify it fails
python -m unittest tests.test_ocr_extraction
# 3. Implement fix
# 4. Verify it passes
python -m unittest tests.test_ocr_extraction
# 5. Commit
```

## Environment Variables

**Required:**
- `MINERU_API_KEY`: MinerU.net API key (Bearer token, JWT format starting with "eyJ")
  - Should be 300+ characters long
  - Supports both JWT tokens ("eyJ0eXAi...") and API keys ("sk-...")
  - Get from: https://mineru.net dashboard

**Optional:**
- `APP_PASSWORD`: Team access password for web interface

## File Organization

```
MinerU/
├── app.py                        # Main Streamlit application (2100+ lines)
├── app_enhanced.py               # Enhanced error handling module
├── diagnose_api.py               # Diagnostic and testing tool
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .streamlit/config.toml        # Streamlit configuration
├── iqc-report/                   # Statistical analysis module
│   ├── scripts/
│   │   └── iqc_stats.py         # 6SPC calculation functions
│   └── assets/
│       └── iqc_template.html    # HTML report template
├── tests/                        # Unit tests
│   ├── test_split_table_format.py
│   ├── test_ocr_extraction.py
│   ├── test_mineru_client.py
│   └── test_debug_*.py
└── docs/
    ├── DEPLOYMENT_GUIDE.md
    └── plans/                    # Implementation plans and bug analyses
```

## Common Tasks

### Debugging OCR Extraction Issues

1. Add markdown sample to appropriate test file in `tests/`
2. Print intermediate parsing results with `logging.debug()`
3. Verify HTML/Markdown table structure from MinerU output
4. Check column indexing logic (use actual column indices, not patterns)
5. Use `tests/test_split_table_format.py` as a template for new test cases
6. Run `python diagnose_api.py` to verify API configuration

### Adding Support for New Table Formats

1. Create test case in `tests/` with sample table data
2. Add table type detection logic in `_detect_table_type()`
3. Implement extraction function following naming pattern: `_extract_*_from_table()`
4. Add processing logic to `parse_html_tables_for_dimensions()`
5. Verify backward compatibility with existing formats

### Updating MinerU API Integration

1. Test API changes in diagnostic tool first (`diagnose_api.py`)
2. Update `MinerUClient` class methods in `app.py:298-537`
3. Add error handling for new response fields
4. Update tests in `tests/test_mineru_client.py`
5. Verify two-step upload process: batch URL → PUT file (no Content-Type header)

### Improving Error Messages

1. Identify error location in `app.py` (typically in `render_processing_section()`)
2. Categorize error type (Upload/Processing, Timeout/Auth/etc)
3. Add specific troubleshooting steps
4. Test with `diagnose_api.py` to verify error detection
5. Update `DEPLOYMENT_FIXES.md` with new error patterns

## Dependencies

**Core:**
- `streamlit>=1.28.0`: Web framework
- `requests>=2.31.0`: HTTP client for API calls
- `pandas>=2.0.0`, `numpy>=1.24.0`: Data processing
- `python-dotenv>=1.0.0`: Environment variable management

**PDF Processing:**
- `PyPDF2>=3.0.0`, `pypdf>=3.17.0`: PDF manipulation

**Testing:**
- Built-in `unittest` (no pytest required)

## Deployment Notes

**Streamlit Cloud Configuration:**
- Max upload size: 200MB (configured in `.streamlit/config.toml`)
- Secrets: Set `MINERU_API_KEY` in app settings
- Python version: 3.8+
- Free tier sufficient for basic usage
- Supports both public and private repositories

**Pre-Deployment Checklist:**
- [ ] Run `python diagnose_api.py` and verify all checks pass
- [ ] API key is 300+ characters and starts with "eyJ"
- [ ] Test app locally with `streamlit run app.py`
- [ ] Verify sidebar health check shows "✅ API Key: Configured"
- [ ] Check error messages are user-friendly
- [ ] Commit all changes with conventional commit format

**Local Development:**
- Create `.env` file from `.env.example`
- Set `MINERU_API_KEY` environment variable
- Optionally set `APP_PASSWORD` for testing authentication

## Code Conventions

**Style:**
- PEP 8 for Python code formatting
- Type hints for function signatures
- Docstrings for all public functions
- Chinese comments acceptable for domain-specific logic

**Error Handling:**
- Use try-except blocks with specific exception types
- Log errors with `logging.getLogger(__name__)`
- Display user-friendly errors in Streamlit UI
- Categorize errors by type for better troubleshooting
- Include detailed tracebacks in debug mode

**Git Commits:**
- Use conventional commit format: `fix:`, `feat:`, `docs:`
- Reference issue numbers in commit messages
- Include TDD test references when applicable
- Example: `fix: Add split-table format support with pending specs state tracking`

## Recent Major Enhancements

### 2026-02-08: Deployment Diagnostics
- Enhanced API key validation (supports JWT and API key formats)
- Added categorized error messages with troubleshooting steps
- Added deployment health check in sidebar
- Added diagnostic tool for pre-deployment testing
- Improved error visibility and user guidance

### 2026-02-07: Split-Table Format Support
- Implemented multi-table format detection and processing
- Added state tracking for pending specifications
- Enhanced HTML and Markdown table parsing
- Backward compatible with single-table format
- Fixed column mapping for non-contiguous spec columns

For detailed information about recent fixes, see `DEPLOYMENT_FIXES.md`.
