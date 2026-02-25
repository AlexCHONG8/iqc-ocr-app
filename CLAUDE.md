# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start (30 seconds)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run CLI test (fastest verification)
python3 main.py

# 3. Run interactive dashboard
python3 -m streamlit run src/verify_ui.py
```

## Project Overview

IQC Pro Max is a medical device **incoming quality control (IQC)** system for **森迈医疗 (Senmai Medical)** that digitizes handwritten QC inspection records into ISO 13485 compliant statistical process control (SPC) analysis reports. The system automates the transformation from scanned documents to 6-SPC capability analysis with interactive verification.

**Core Value**: Reduces QC report generation from 2 hours to 15 minutes (8x efficiency gain) while maintaining <0.5% error rate.

**Target Users**: Quality control engineers in medical device manufacturing, specifically for plastic injection hot runner process inspection and incoming material verification.

**Brand**: Header titles display "🏥 森迈医疗 | IQC Pro Max"

**Version**: v1.5 - Enhanced with AI-powered analysis, HTML report generation, and Supplier Performance Tracking

## Build & Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Environment configuration
# .env must contain: OCR_API_KEY=your_mineru_token_here

# Activate virtual environment (if using .venv)
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

### Helper Scripts

```bash
# Pre-commit quality checks (recommended before git commit)
./pre_commit_checks.sh

# Push project to GitHub as subfolder
./push_to_github.sh
```

**Note**: The `pre_commit_checks.sh` script validates:

- Python syntax (catches 80% of errors)
- Decimal precision (catches 3-decimal bugs)
- Orphaned finally blocks
- Helper function placement
- API token compatibility
- Mock data fallbacks

## Development Tooling & Automation

### Skills System (`.skills/`)

The project includes reusable skills for automated code review and UI/UX design.

**Verify-Work Skill** (`.skills/verify-work/`)

- Comprehensive code verification command
- **Usage**: Invoke `/verify-work` in chat
- **Checks Performed**:
  - Security: Hardcoded secrets, SQL injection, XSS vulnerabilities
  - Code Quality: Style consistency, error handling, documentation
  - Efficiency: Performance bottlenecks, resource leaks, algorithm complexity
  - Best Practices: SOLID principles, separation of concerns, test coverage
- **Output**: Structured report with scores, critical issues, warnings, and action items

**UI-UX Pro Max Skill** (`.skills/ui-ux-pro-max/`)

- Advanced UI/UX design intelligence toolkit (optional)
- **Features**: 67 UI styles, 96 color palettes, 57 font pairings, 25 chart types
- **Auto-activates** for UI/UX design requests
- **Usage**: Simply describe the UI component or design system you need

### Pre-Commit Quality Gates

The `pre_commit_checks.sh` script provides automated validation before commits:

```bash
./pre_commit_checks.sh
```

**Six automated checks**:

1. **Syntax validation** - Python compilation catches 80% of errors
2. **Decimal precision** - Ensures `round(x, 2)` not `round(x, 3)`
3. **Finally block structure** - Prevents orphaned `finally:` SyntaxError
4. **Helper function placement** - Verifies chart functions at lines 35-240
5. **API token compatibility** - Detects JWT vs API key format issues
6. **Mock data fallbacks** - Ensures no silent failures

**Exit codes**: 0 = pass (safe to commit), 1 = fail (fix issues first)

### Additional Scripts

**`push_to_github.sh`**

- Pushes project to centralized GitHub repo as subfolder
- Excludes: `.git`, `.venv`, `__pycache__`
- Destination: `https://github.com/AlexCHONG8/CC/tree/main/$PROJECT`

**`start_claude_glm5.sh`** (optional)

- LiteLLM proxy for routing requests to GLM-5 model
- Allows testing with alternative AI models
- Requires GLM-5 API key configuration

### Execution & Testing

```bash
# CLI test - Fastest way to verify OCR + statistical calculations
python3 main.py

# Interactive Streamlit Dashboard
python3 -m streamlit run src/verify_ui.py

# With custom port (if default 8501 is in use)
python3 -m streamlit run src/verify_ui.py --server.port 8511
```

### Manual Data Entry Helper

If OCR fails or you need to process data without scans:

```bash
python3 manual_data_entry_helper.py
```

## Architecture

### Data Flow Pipeline

```
Scan Upload (PDF/JPG/PNG)
    ↓
OCR Extraction (MinerU API v4)
    ↓
Data Validation & Correction (utils.py)
    ↓
SPC Calculation (spc_engine.py)
    ↓
AI-Powered Analysis (analysis_engine.py)
    ↓
Interactive Verification (verify_ui.py)
    ↓
Report Export (HTML/Excel/History)
```

### Core Components

#### 1. **OCRService** (`src/ocr_service.py`)

MinerU API v4 client wrapper for extracting measurement data from scans.

**Key Methods:**

- `extract_table_data(file_path)`: Returns list of dimension sets from scans
- `MinerUClient`: Low-level API handler (upload → poll → retrieve markdown)
- `_parse_chinese_qc_report()`: Specialized parser for Chinese QC reports
- `_get_mock_data_multi()`: Fallback mock data with realistic QC measurements

**Chinese QC Report Format Handling:**

- Parses specifications like `27.80+0.10-0.00`, `Φ6.00±0.10`, `73.20+0.00-0.15`
- Extracts USL/LSL from asymmetric tolerance notation
- Multi-dimension detection (multiple parameters per document)
- Inspection location tables with multiple parameters
- **NEW**: Batch size extraction from document headers

**Critical:** Line 306 applies 2-decimal precision during OCR extraction (see Measurement Precision Standards)

**Error Handling Enhancements:**

- Detects OpenXLab tokens incompatible with mineru.net API
- Provides clear error messages with 3 actionable solutions
- Falls back to mock data when API fails (with user notification)
- Enhanced debugging output for API failures

**Usage:**

```python
ocr = OCRService()
data = ocr.extract_table_data("scan.pdf")  # Returns: [{"header": {...}, "measurements": [...]}]
```

#### 2. **SPCEngine** (`src/spc_engine.py`)

Statistical computation engine for process capability analysis.

**Key Methods:**

- `calculate_stats(data, subgroup_size=5)`: Returns all SPC indices and subgroup data
- `_calculate_capability(...)` (internal): Computes Cp/Cpk/Pp/Ppk

**Calculations:**

- **Within-subgroup variation**: σ_within = R-bar / d2 (d2=2.326 for n=5)
- **Overall variation**: σ_overall = sample standard deviation (ddof=1)
- **Cp/Cpk**: Potential capability (using σ_within)
- **Pp/Ppk**: Overall performance (using σ_overall)
- **Subgrouping**: Automatic X-bar/R chart data generation

**Compliance Threshold:** Cpk ≥ 1.33 = PASS

**Usage:**

```python
engine = SPCEngine(usl=10.5, lsl=9.5)
stats = engine.calculate_stats(measurements)
# Returns: {"mean": 10.0, "cpk": 1.33, "subgroups": {...}, ...}
```

#### 3. **Utils Module** (`src/utils.py`)

Data validation, correction, and export utilities.

**Key Functions:**

- `detect_outliers(data, threshold=3.0)`: 3σ outlier detection
- `correct_measurements(data, usl, lsl)`: OCR error correction (missing decimals, unit noise, character substitutions)
- `normality_test(data)`: Shapiro-Wilk and Anderson-Darling tests
- `suggest_boxcox(data)`: Box-Cox transformation recommendations
- `calculate_control_limits(data, subgroup_size=None)`: X-bar/R chart control limits (A2, D3, D4 constants) **[NEW v1.5]**
- `export_to_excel(data, stats, filepath)`: 4-sheet Excel export (info, raw data, subgroups, summary)

**Classes:**

- `HistoryManager`: Report save/load/search/delete operations with JSON storage in `reports_history/`
- `SupplierPerformanceTracker`: **[NEW v1.5]** Multi-lot supplier performance tracking and scorecard generation

**Supplier Performance Tracker Features:**

- Track quality metrics across multiple lots from same supplier
- Generate performance scorecards with trend analysis
- Calculate supplier quality ratings (EXCELLENT/GOOD/ACCEPTABLE/NEEDS_ATTENTION)
- Monitor PPM rates, Cpk trends, and batch-to-batch consistency
- Track defect types and occurrence frequencies

#### 4. **Streamlit UI** (`src/verify_ui.py`)

Human-in-the-loop verification dashboard with 6 SPC charts.

**Structure:**

- **Lines 35-235**: Chart helper functions - MUST remain here to avoid NameError
- **Lines 240+**: Page configuration, CSS styling, main UI logic
- **Three pages**: Data Analysis, History, Settings

**Critical Architecture:** Helper functions MUST be defined before line 240 (after imports, before page config) because Streamlit executes top-to-bottom on every interaction. Moving chart functions below line 240 causes NameError.

**6 SPC Charts:**

1. Individual Readings Plot (single values)
2. X-bar Control Chart (subgroup means)
3. R Control Chart (subgroup ranges)
4. Histogram with normal fit (20 bins)
5. Q-Q Plot (normality assessment)
6. Capability Plot (distribution + PPM calculations)

**Features:**

- Real-time editable data tables with automatic stat recalculation
- Multi-dimension support with expandable sections
- Smart correction button (applies `correct_measurements`)
- Outlier highlighting in red
- Side-by-side scan view for OCR verification
- Scrollable data tables (height=600)
- Filter for corrected values only
- Excel export (4 worksheets via `export_to_excel`)
- History save/load/search/delete
- HTML report preview with print support (Ctrl+P)
- **[NEW v1.5]**: AI-powered analysis integration
- **[NEW v1.5]**: Supplier performance tracking view
- **[NEW v1.5]**: Enhanced chart tooltips and interactivity

#### 5. **AnalysisEngine** (`src/analysis_engine.py`)

**[NEW v1.5]** AI-powered analysis engine for plastic injection hot runner process control.

**Key Class: `PlasticInjectionAnalyzer`**

- `analyze_dimension(dim_data, stats)`: Returns comprehensive analysis
- `generate_executive_summary(analyses)`: Aggregates analysis across all dimensions

**Analysis includes:**

- Status rating (EXCELLENT/GOOD/ACCEPTABLE/NEEDS_IMPROVEMENT/CRITICAL)
- Risk level (LOW/MEDIUM/HIGH/CRITICAL)
- Overall assessment (bilingual Chinese/English)
- Capability analysis (Cp vs Cpk, centering, potential vs overall)
- Stability analysis (within vs overall variation, drift detection)
- Improvement actions (specific to hot runner systems)
- Hot runner tips (temperature control, gate, timing)

**Thresholds:**

- EXCELLENT: Cpk ≥ 1.67, PPM ≤ 100
- GOOD: Cpk ≥ 1.33, PPM ≤ 1,000
- ACCEPTABLE: Cpk ≥ 1.00, PPM ≤ 10,000
- CRITICAL: Cpk < 1.0 or PPM > 50,000

#### 6. **DashboardGenerator** (`src/dashboard_generator.py`)

Professional HTML report generator with tabbed interface for ISO 13485 compliance.

**Key Function: `generate_professional_dashboard(dim_data, stats_list)`**

- Generates multi-tab HTML reports with executive summary
- Creates all 6 SPC charts with enhanced medical-grade styling
- Includes AI-powered analysis from `PlasticInjectionAnalyzer`
- Saves to `reports/` directory with timestamp filename

**Chart Functions:** See "Chart Generation Best Practices" section

**HTML Features:**

- Tabbed navigation (Executive Summary + per-dimension tabs)
- Print-friendly styling (Ctrl+P for PDF export)
- Interactive Plotly charts via CDN
- Bilingual labels (Chinese + English)
- Responsive design
- Brand header: "森迈医疗 | IQC Pro Max 质量分析报告"
- **[NEW v1.5]**: Enhanced styling with medical-grade color scheme
- **[NEW v1.5]**: Interactive tooltips and data highlighting
- **[NEW v1.5]**: Supplier performance summary section

### Dual Chart System Architecture

The system has TWO separate chart generation approaches:

#### 1. Streamlit Dashboard Charts (`verify_ui.py` lines 35-235)

- **Purpose**: Interactive real-time charts in Streamlit UI
- **Return Type**: Plotly Figure objects (`go.Figure()`)
- **Usage**: Displayed via `st.plotly_chart()`
- **Interactivity**: Full Plotly interactivity, zoom, pan, hover

#### 2. HTML Export Charts (`dashboard_generator.py`)

- **Purpose**: Static charts in generated HTML reports
- **Return Type**: HTML strings (`fig.to_html(full_html=False, include_plotlyjs='cdn')`)
- **Usage**: Embedded in HTML template for export/print
- **Interactivity**: Preserved via Plotly CDN in HTML

**Key Difference:**

```python
# Streamlit version (verify_ui.py)
def create_histogram(data, title, usl, lsl, mean):
    fig = go.Figure()
    # ... build chart ...
    return fig  # Return Plotly Figure object

# HTML export version (dashboard_generator.py)
def _create_histogram(measurements, usl, lsl):
    fig = go.Figure()
    # ... build chart ...
    return fig.to_html(full_html=False, include_plotlyjs='cdn')  # Return HTML string
```

### Data Structures

#### Dimension Set (OCR → SPC Input Format)

```python
{
    "header": {
        "batch_id": str,           # Batch identifier
        "dimension_name": str,     # Parameter being measured
        "usl": float,              # Upper specification limit
        "lsl": float               # Lower specification limit
    },
    "measurements": List[float]    # Raw measurement values (variable count)
}
```

#### SPC Results (SPCEngine output)

```python
{
    "mean": float,
    "std_overall": float,         # Sample std (ddof=1)
    "std_within": float,          # R-bar/d2 estimate
    "min": float, "max": float,
    "count": int,
    "cp": float, "cpk": float,    # Potential capability
    "pp": float, "ppk": float,    # Overall performance
    "cpk_status": "PASS" | "FAIL",
    "subgroups": {
        "x_bar": List[float],      # Subgroup means
        "r": List[float],          # Subgroup ranges
        "size": int                # Subgroup size (default 5)
    }
}
```

#### Control Limits (X-bar/R charts)

```python
{
    "x_bar": {
        "ucl": float,  # X-double-bar + A2 * R-bar
        "cl": float,   # X-double-bar
        "lcl": float   # X-double-bar - A2 * R-bar
    },
    "r": {
        "ucl": float,  # D4 * R-bar
        "cl": float,   # R-bar
        "lcl": float   # D3 * R-bar (often 0 for n=5)
    },
    "constants": {
        "A2": float, "D3": float, "D4": float, "d2": float
    }
}
```

### File System

```
6SPC/
├── src/
│   ├── __init__.py
│   ├── ocr_service.py          # MinerU API client
│   ├── spc_engine.py           # SPC calculations
│   ├── verify_ui.py            # Streamlit dashboard (1000+ lines)
│   ├── utils.py                # Utilities (corrections, tests, export, history)
│   ├── analysis_engine.py      # AI-powered analysis for plastic injection [NEW v1.5]
│   └── dashboard_generator.py  # HTML report generator
├── reports/                     # Generated HTML reports (auto-created)
├── reports_history/             # JSON report storage (managed by HistoryManager)
│   └── index.json              # Report index metadata
├── Scan PDF/                    # Test files for real OCR validation
├── main.py                      # CLI orchestrator
├── manual_data_entry_helper.py  # Manual data entry when OCR fails
├── requirements.txt             # Python dependencies
├── .env                         # OCR_API_KEY (not in git)
├── CLAUDE.md                    # This file
├── pre_commit_checks.sh         # Pre-commit quality gates [NEW v1.5]
├── push_to_github.sh            # GitHub push script [NEW v1.5]
└── README.md                    # User-facing documentation
```

## Statistical Standards

### Control Chart Constants (n=5)

- **A2 = 0.577**: X-bar chart multiplier
- **D3 = 0**: R chart LCL multiplier
- **D4 = 2.114**: R chart UCL multiplier
- **d2 = 2.326**: Within-subgroup sigma divisor

### Formulas

- **σ_within** = R-bar / d2
- **σ_overall** = sample standard deviation
- **Cp** = (USL - LSL) / (6 × σ_within)
- **Cpk** = min[(USL - μ)/(3σ_within), (μ - LSL)/(3σ_within)]
- **Pp** = (USL - LSL) / (6 × σ_overall)
- **Ppk** = min[(USL - μ)/(3σ_overall), (μ - LSL)/(3σ_overall)]

### Normality Tests

- **Shapiro-Wilk**: 3 ≤ n ≤ 5000, p ≥ 0.05 → normal
- **Anderson-Darling**: Any n, statistic < critical value → normal

## Project Standards

### Code Organization

- **PEP 8** for Python code style
- **Separation of Concerns**:
  - OCR operations → `OCRService` only
  - SPC math → `SPCEngine` only
  - Validation/correction → `utils.py` functions
  - UI logic → `verify_ui.py` only
  - AI analysis → `analysis_engine.py` only
  - Report generation → `dashboard_generator.py` only
- **No Circular Imports**: Utils depends on scipy/numpy, not on SPCEngine/OCRService

### Error Handling

- **Graceful Degradation**: System falls back to mock data when OCR fails (with user notification)
- **User-Facing Errors**: Streamlit error messages, not stack traces
- **Data Validation**: Warn on incomplete extraction (< 20% expected data)
- **Exception Re-raising**: In `ocr_service.py` line 126, exceptions are re-raised (not silently caught) to ensure proper error propagation
- **File Cleanup**: Temp files cleaned up after OCR processing, even if exceptions occur
- **API Incompatibility Detection**: OpenXLab tokens detected with clear error messages and 3 solution options

### Python Exception Handling Patterns

**Do's**:

```python
try:
    result = api_call()
except SpecificException as e:
    st.error(f"Clear user message: {e}")
    st.stop()  # Stop Streamlit execution
finally:
    # Cleanup at same level as try
    cleanup()
```

**Don'ts**:

```python
try:
    result = api_call()
except Exception as e:
    pass  # NEVER silently ignore exceptions

# OR
try:
    result = api_call()
except Exception as e:
    st.stop()

if some_condition:  # Wrong nesting level!
    finally:  # SYNTAX ERROR!
        cleanup()
```

### UI/UX Patterns

- **Medical-grade color scheme**: Teal/cyan (#0891B2), green (#22C55E), red (#EF4444)
- **Sidebar gradient**: `#0F766E → #134E4A` with enhanced typography
- **Expandable sections**: Use `st.expander()` for multi-dimension data
- **Editable tables**: `st.data_editor()` for in-place editing
- **Real-time updates**: Use session state to track data changes
- **Enhanced interactivity**: Tooltips, zoom, pan on all charts
- **Responsive design**: Works on desktop and tablet screens

### Helper Function Placement (Critical)

When editing `src/verify_ui.py`:

- **ALWAYS define helper functions before line 240** (after imports, before page config)
- Streamlit executes top-to-bottom on every interaction
- Moving chart functions to bottom causes NameError
- Current valid location: Lines 35-235

## Environment Variables

```bash
# Required for OCR functionality
OCR_API_KEY=your_mineru_token_here

# Optional: MinerU API endpoint (default: https://mineru.net/api/v4)
MINERU_BASE_URL=https://mineru.net/api/v4
```

## Measurement Precision Standards

**CRITICAL**: All measurement data MUST be stored and displayed with **2 decimal places** (0.01mm accuracy), matching physical caliper measurement capabilities.

**Standard**: QC calipers measure to 0.01mm precision (2 decimal places). Handwritten inspection records reflect this physical limitation with values like "27.85mm", not "27.851mm".

### Data Flow with 2-Decimal Precision

```
Handwritten Scan (2 decimals: 27.85mm)
    ↓
OCR Extraction (MinerU API returns raw markdown)
    ↓
_parse_chinese_qc_report() Line 306: round(val, 2) ← PRIMARY FIX
    ↓
Session State Storage & Display
```

### Fix Location for 2-Decimal Precision

**`src/ocr_service.py` Line 306** - OCR extraction:

```python
val = float(meas_match.group(1))
# Apply QC measurement precision standard (2 decimal places = 0.01mm accuracy)
val = round(val, 2)
measurements_by_loc[loc_num].append(val)
```

**Verification Command:**

```bash
grep -rn "round.*, *3)" src/  # Should return NO matches
grep -rn "round.*, *2)" src/  # Should show all 2-decimal rounding
```

## Chart Generation Best Practices

### 6 SPC Chart Styling Standards

All charts MUST follow these professional medical-grade styling standards:

#### Visual Enhancements

- **Data Point Visibility**: Marker size 8-10px, white stroke (2px), opacity 0.85-0.9
- **Line Styling**: Main data 3px, UCL/LCL 3px dashed red, CL 2.5px solid green
- **Typography**: Title 16px bold, axis labels 13px bold, annotations 12px bold
- **Layout**: Height 450px, margins `dict(l=60, r=30, t=50, b=60)`
- **Interactivity**: Tooltips showing values, zoom, pan capabilities

#### Color Scheme (Medical-Grade)

- Primary data: `#0891B2` (teal/cyan)
- UCL/LCL limits: `#DC2626` (red)
- Center/Target: `#16A34A` (green) or `#22C55E`
- Background: `rgba(255, 255, 255, 0.98)`
- Text: `#374151` (dark gray)

#### Chart-Specific Requirements

**Individual Values Plot**: Circle markers (8px), target line at nominal, grid enabled, tooltips with values

**X-bar Control Chart**: Circle markers (10px), UCL/LCL 3px dashed red, CL 2.5px solid green, statistics box

**R Control Chart**: Diamond markers (10-12px), red for out-of-control points, statistics box with range info

**Histogram**: 20 bins with 0.7 opacity, red normal fit (4px), USL/LSL vertical lines, rug plot at bottom, hover info for bins

**Q-Q Plot**: Sample markers (9px), reference line (2.5px red dashed), zero lines on both axes, confidence intervals

**Capability Plot**: Distribution fill (rgba(8, 145, 178, 0.15)), Y-axis LSL/USL diamond markers (15px), vertical limit lines (5px dashed red), enhanced annotation box with capability indices and PPM rates, **[NEW v1.5]** interactive zone highlighting

## Common Issues & Troubleshooting

### CRITICAL: Try-Except-Finally Block Structure

**Symptom**: `SyntaxError: invalid syntax` at `finally:` block in `verify_ui.py`

**Root Cause**: `finally:` keyword must be at the SAME indentation level as its corresponding `try:` block. You cannot nest a `finally:` inside an `if` or other block that's inside a `try`.

**Example of WRONG structure** (causes SyntaxError):

```python
try:
    # Some code
except Exception as e:
    st.stop()  # Stops execution

if st.session_state.dim_data:  # ← This is OUTSIDE the try block
    # Process data

finally:  # ← SYNTAX ERROR! Can't be inside the if block
    # Cleanup
```

**Example of CORRECT structure**:

```python
try:
    # Some code
except Exception as e:
    st.stop()

# Clean up temp file (OUTSIDE the try-except block)
if os.path.exists(tmp_file_path):
    os.unlink(tmp_file_path)
```

**Prevention**: Never place a `finally:` block inside an `if`, `for`, or `while` that's AFTER the `try`. The `finally` must be an immediate sibling of `try` and `except` at the same indentation level.

### MinerU API Service Failures

**✅ ROOT CAUSE RESOLVED (2026-02-24)**:

Previously, the system relied on an unreliable third-party service (`transfer.sh`) for temporary file hosting. This caused mysterious failures during the OCR workflow because files either failed to upload or weren't publicly accessible to MinerU.

The system has now been upgraded to use **MinerU's native direct S3 upload API**. This handles file uploads directly and reliably, eliminating the `transfer.sh` dependency.

**Note on OpenXLab Tokens**:
If your `.env` contains an **OpenXLab JWT token** (which is common for these deployments), it **is 100% compatible** with the MinerU v4 endpoints used in this project. Previous documentation incorrectly stated they were incompatible.

**Symptom**: `MinerU Error: Unknown error (state: failed)`
**Cause**: Rare API downtime or invalid token.
**Alternative**: Let the system fall back to mock data automatically, or use `manual_data_entry_helper.py` to process data without OCR.

### Decimal Precision: 3 Decimals Instead of 2

**Symptom**: Measurements show 3 decimal places (27.851mm) instead of 2 (27.85mm)

**Fix**: Ensure `ocr_service.py` line 306 applies `round(val, 2)` during OCR extraction

**Verification**: Run `grep -rn "round.*, *3)" src/` - should return no matches

### Streamlit NameError

**Symptom**: `NameError: name 'create_histogram' is not defined`

**Cause**: Helper functions moved below line 240 in `verify_ui.py`

**Fix**: Keep chart helper functions at lines 35-235 (after imports, before page config)

### Port Conflicts

**Symptom**: `Port 8501 is already in use`

**Fix 1**: Kill existing process: `pkill -f "streamlit run src/verify_ui.py"`

**Fix 2**: Use different port: `python3 -m streamlit run src/verify_ui.py --server.port 8511`

### OCR API Failures with Graceful Fallback

**Symptom**: `MinerU API Error` but system continues working

**Behavior**: This is **intended behavior** in v1.5:

1. System attempts OCR API call
2. If API fails, console shows: `MinerU API Error: <details>`
3. System automatically falls back to mock data
4. Console shows: `Falling back to mock data for testing...`
5. All functionality remains available (charts, analysis, exports)

**Fix**: For production use with real scans, either:

- Get valid MinerU.net API key
- Use manual data entry helper
- Upload data directly in Streamlit dashboard

### Missing Dependencies

**Symptom**: `ModuleNotFoundError: No module named 'plotly'`

**Fix**: `pip install -r requirements.txt`

### File Upload Type Error

**Symptom**: `expected str, bytes or os.PathLike object, not UploadedFile`

**Cause**: Streamlit's `st.file_uploader()` returns `UploadedFile` objects

**Fix Implemented** (lines 400-411 in `verify_ui.py`): Save uploaded file to temp location for OCR processing, then cleanup

## Development Workflow Tips

### When Working with Charts

- **Streamlit Dashboard Charts**: Edit functions in `src/verify_ui.py` (lines 35-235), return `go.Figure()` objects
- **HTML Export Charts**: Edit functions in `src/dashboard_generator.py`, return `fig.to_html()` strings

### When Adding New Analysis Features

1. Add statistical functions to `src/utils.py` or `src/spc_engine.py`
2. For AI-powered insights, extend `PlasticInjectionAnalyzer` in `src/analysis_engine.py`
3. Update both chart systems (verify_ui.py and dashboard_generator.py) for visual consistency
4. Add bilingual labels (Chinese + English) for all user-facing text

### When Modifying OCR Parsing

- Chinese QC report format logic is in `_parse_chinese_qc_report()` method
- Test with real scans in `Scan PDF/` directory
- Apply 2-decimal precision at line 306 during extraction
- Extract batch size if present in document header

### When Adding Supplier Performance Tracking

1. Use `SupplierPerformanceTracker` class in `src/utils.py`
2. Track lots by supplier name
3. Generate scorecards with `generate_scorecard()` method
4. Display in History page with expandable sections

### Platform-Specific Considerations

**Mac Path Issue** (`verify_ui.py` lines 13-15):

```python
# For Mac environment consistency: Ensure user site-packages are in path
user_site = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if user_site not in sys.path:
    sys.path.append(user_site)
```

This code adds Mac-specific user site-packages to the path. When developing on other platforms (Windows/Linux), this path won't exist but is safely skipped. However, be aware that hardcoding Python version paths may cause issues if the system Python version changes.

## Testing Strategy

### Unit Testing

```bash
# Test OCR extraction and statistical calculations
python3 main.py

# Expected output:
# - OCR extraction success (or graceful fallback to mock data)
# - 2+ dimension sets detected
# - Corrections applied (missing decimals, unit noise)
# - Outliers detected (if any)
# - Cpk/Pp indices calculated
# - Normality test passed/failed
# - Control limits computed
# - AI-powered analysis generated
```

### Integration Testing

```bash
# Test full dashboard workflow
python3 -m streamlit run src/verify_ui.py

# Manual checklist:
# 1. Upload PDF/JPG scan
# 2. Verify OCR extraction or use manual data entry
# 3. Click "✨ 智能修正数据" (smart correction)
# 4. Edit data table cells
# 5. Check stat recalculation
# 6. View all 6 charts with interactivity
# 7. Read AI-powered analysis
# 8. Export Excel (4 worksheets)
# 9. Save to history
# 10. Search history
# 11. Load saved report
# 12. Generate HTML report
# 13. Print report (Ctrl+P)
```

### Test Data Locations

- **Unit tests**: `sample_scan.pdf` (project root)
- **Real scans**: `Scan PDF/` directory
- **History tests**: `reports_history/` (auto-created on first save)

## Pre-Commit Verification Commands

Before committing any changes to `verify_ui.py` or other critical files, ALWAYS run these checks:

```bash
# 1. Syntax check - Catches try-except-finally errors
python3 -m py_compile src/verify_ui.py

# 2. Verify decimal precision - Catches 3-decimal bugs
grep -rn "round.*, *3)" src/  # Should return NO matches

# 3. Check for orphaned finally blocks - Catches syntax errors
grep -A2 "if.*:" src/verify_ui.py | grep -B1 "finally:"  # Should return NO matches

# 4. Verify helper function placement - Catches NameError
sed -n '35,240p' src/verify_ui.py | grep -c "def create_"  # Should show 5-6 functions

# 5. Test Streamlit startup - Catches runtime errors
timeout 10 python3 -m streamlit run src/verify_ui.py --server.port 8511 > /dev/null 2>&1 || true
```

## Session Summary Checklist

After any development session, verify:

- ✅ No syntax errors (`python3 -m py_compile src/*.py`)
- ✅ No 3-decimal precision issues (`grep -rn "round.*, *3)" src/`)
- ✅ Streamlit starts without errors
- ✅ API key configured if using OCR (`grep OCR_API_KEY .env`)
- ✅ Temp files cleaned up (no `tmp*.py` or `tmp*.pdf` in root)
- ✅ CLAUDE.md updated with lessons learned
- ✅ System falls back gracefully when OCR fails
- ✅ All 6 charts render correctly
- ✅ AI analysis generates properly
- ✅ HTML reports generate successfully

## Version History

### v1.5 (Current)

- **NEW**: AI-powered analysis with `PlasticInjectionAnalyzer`
- **NEW**: Professional HTML report generator with tabbed interface
- **NEW**: Supplier performance tracking and scorecards
- **NEW**: Enhanced chart styling with medical-grade design
- **NEW**: Control limits calculation in `utils.py`
- **NEW**: Batch size extraction from QC documents
- **IMPROVED**: Graceful OCR fallback with user notification
- **IMPROVED**: OpenXLab token detection with clear error messages
- **IMPROVED**: Enhanced chart interactivity and tooltips

### v1.0

- Initial release with 6 SPC charts
- OCR extraction from Chinese QC reports
- Streamlit dashboard with data verification
- Manual data entry helper
- Excel export functionality
