# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **IQC (Incoming Quality Control) OCR + SPC Analysis** web application that processes handwritten inspection reports through OCR and generates ISO 13485 compliant statistical process control reports.

**Tech Stack:**
- **Frontend**: Streamlit web application (`app.py`)
- **OCR API**: MinerU.net (cloud-based PDF to Markdown conversion)
- **Statistical Analysis**: 6SPC calculations (Cp, Cpk, Pp, Ppk, Xbar-R charts)
- **Output**: HTML reports with Chart.js visualizations
- **Testing**: Python unittest framework

**Key Features:**
- Multi-language OCR support (109 languages including Chinese handwriting)
- Automatic extraction of measurement data from OCR-generated Markdown tables
- Statistical process control (SPC) with process capability indices
- PDF upload interface with real-time processing feedback
- Team access with optional password protection

## Development Commands

### Running the Application

```bash
# Local development
streamlit run app.py

# Install dependencies
pip install -r requirements.txt

# Run specific test
python test_ocr_extraction.py
python test_mineru_client.py
python test_pdf_export.py

# Run all tests
python -m unittest discover -s . -p "test_*.py"
```

### Deployment

```bash
# Deploy to Streamlit Cloud
# 1. Push code to GitHub
git push origin main

# 2. Configure secrets in Streamlit Cloud:
#    - MINERU_API_KEY (required)
#    - APP_PASSWORD (optional)
```

### MinerU API Testing

```bash
# List recent conversion tasks
python mineru_cloud_simple.py list

# Download markdown from a specific task
python mineru_cloud_simple.py download 1
```

## Architecture

### Core Components

**1. MinerUClient Class (`app.py:294-533`)**
- Manages PDF upload to MinerU.net API
- Polls task status during OCR processing
- Downloads converted markdown/text from CDN
- Handles ZIP extraction and error recovery
- Uses API key from environment variable `MINERU_API_KEY`

**2. OCR Table Parsing (`app.py:535-658`)**
- `parse_html_tables_for_dimensions()`: Extracts measurement tables from HTML tables in OCR output
- Critical: Column mapping logic (line 634-637) - must use actual column indices, not pattern-based indexing
- Handles Chinese inspection records with multiple measurement positions
- Parses specification strings (e.g., "27.85±0.5") to extract nominal, USL, LSL

**3. IQC Data Extraction (`app.py:659-750`)**
- `extract_iqc_data_from_markdown()`: Orchestrates full parsing workflow
- Extracts metadata: material name, batch number, inspection date, operator
- Returns structured data for statistical analysis

**4. Statistical Analysis (`iqc-report/scripts/iqc_stats.py`)**
- `calculate_subgroups()`: Divides measurements into subgroups (default n=5)
- `calculate_process_capability()`: Computes Cp, Cpk, Pp, Ppk indices
- `calculate_control_limits()`: Xbar-R chart control limits (A2, D3, D4 constants)
- `generate_iqc_data()`: Master function producing complete IQC dataset
- `generate_html_report()`: Embeds data in HTML template with Chart.js

**5. Streamlit UI (`app.py:751-1322`)**
- `render_header()`: Clinical precision branding with custom CSS
- `render_sidebar()`: Configuration and settings panel
- `render_upload_section()`: File upload interface (max 200MB)
- `render_processing_section()`: OCR progress with status polling
- `render_data_extraction_section()`: Manual data review/editing
- `render_report_section()`: Statistical charts and PDF/HTML export
- `main()`: Application entry point with session state management

### Data Flow

```
PDF Upload → MinerU.net API → Poll Task Status → Download Markdown
→ Parse HTML Tables → Extract Measurements → Calculate 6SPC Metrics
→ Generate HTML Report → Display Charts → Export PDF/HTML
```

### Key Integration Points

**MinerU.net API:**
- Base URL: `https://mineru.net/api/v4/`
- Endpoints: `/tasks` (list, status), `/file_upload` (upload PDF)
- Response fields: `task_id`, `state`, `full_md_link`, `full_zip_url`
- Use `full_md_link` if available, fallback to extracting ZIP from `full_zip_url`

**HTML Template:**
- Location: `iqc-report/assets/iqc_template.html`
- Uses Chart.js for interactive visualizations
- Embedded CSS for print-optimized layout
- Chinese font support: "PingFang SC", "Microsoft YaHei", "SimSun"

## Important Implementation Notes

### Column Mapping Bug (FIXED - 2026-02-07)
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

**Test Coverage:** `test_ocr_extraction.py` validates 3-column extraction with gaps.

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

### Testing Patterns
Tests use Python's built-in `unittest` framework. Key test files:
- `test_ocr_extraction.py`: Column mapping edge cases
- `test_mineru_client.py`: API interaction mocking
- `test_pdf_export.py`: PDF generation with Chinese font support

Run TDD workflow:
```bash
# 1. Write failing test
# 2. Verify it fails
python test_ocr_extraction.py
# 3. Implement fix
# 4. Verify it passes
python test_ocr_extraction.py
# 5. Commit
```

## Environment Variables

**Required:**
- `MINERU_API_KEY`: MinerU.net API key (Bearer token)

**Optional:**
- `APP_PASSWORD`: Team access password for web interface

## File Organization

```
MinerU/
├── app.py                        # Main Streamlit application (1357 lines)
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .streamlit/config.toml        # Streamlit configuration
├── mineru_cloud_simple.py        # Command-line API client
├── iqc-report/                   # Statistical analysis module
│   ├── scripts/
│   │   ├── iqc_stats.py         # 6SPC calculation functions
│   │   └── md_to_iqc.py         # Markdown to report converter
│   ├── assets/
│   │   └── iqc_template.html    # HTML report template
│   └── SKILL.md                  # Module documentation
├── mineru-pdf-converter/        # PDF conversion skill
│   ├── scripts/
│   └── SKILL.md
├── test_*.py                     # Unit tests
└── docs/plans/                   # Implementation plans
```

## Common Tasks

### Adding New Statistical Metrics
1. Add calculation function to `iqc-report/scripts/iqc_stats.py`
2. Update `generate_iqc_data()` to include new metric
3. Modify `iqc_template.html` to display metric
4. Add test coverage

### Debugging OCR Extraction
1. Add markdown sample to `test_ocr_extraction.py`
2. Print intermediate parsing results
3. Verify HTML table structure from MinerU output
4. Check column indexing logic at `app.py:634-637`

### Updating MinerU API Integration
1. Test API changes in `mineru_cloud_simple.py` first
2. Update `MinerUClient` class methods
3. Add error handling for new response fields
4. Update tests in `test_mineru_client.py`

## Dependencies

**Core:**
- `streamlit>=1.28.0`: Web framework
- `requests>=2.31.0`: HTTP client for API calls
- `pandas>=2.0.0`, `numpy>=1.24.0`: Data processing

**PDF Processing:**
- `PyPDF2>=3.0.0`, `pypdf>=3.17.0`: PDF manipulation
- `weasyprint>=60.0`: HTML to PDF conversion (optional)

**Testing:**
- Built-in `unittest` (no pytest required)

## Deployment Notes

**Streamlit Cloud Configuration:**
- Max upload size: 200MB (configured in `.streamlit/config.toml`)
- Secrets: Set `MINERU_API_KEY` in app settings
- Python version: 3.8+
- Free tier sufficient for basic usage

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
- Include detailed tracebacks for debugging

**Git Commits:**
- Use conventional commit format: `fix:`, `feat:`, `docs:`
- Reference issue numbers in commit messages
- Include TDD test references when applicable
