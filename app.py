#!/usr/bin/env python3
"""
IQC OCR + SPC Analysis Web Application
A Streamlit app for processing handwritten PDFs with OCR and generating ISO 13485 compliant reports.

Features:
- PDF upload interface
- OCR processing via MinerU.net API
- 6SPC statistical analysis
- HTML report generation
- Team access with password protection
"""

import os
import sys
import json
import time
import re
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import streamlit as st
import requests

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Dynamic import for hyphenated directory
import importlib.util
iqc_stats_path = Path(__file__).parent / "iqc-report" / "scripts" / "iqc_stats.py"
spec = importlib.util.spec_from_file_location("iqc_stats", iqc_stats_path)
iqc_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iqc_stats)

calculate_subgroups = iqc_stats.calculate_subgroups
calculate_process_capability = iqc_stats.calculate_process_capability
calculate_control_limits = iqc_stats.calculate_control_limits
parse_dimension_from_data = iqc_stats.parse_dimension_from_data
generate_iqc_data = iqc_stats.generate_iqc_data
generate_html_report = iqc_stats.generate_html_report

# =============================================================================
# CONFIGURATION & STYLING
# =============================================================================

st.set_page_config(
    page_title="Summed Medtech IQC",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clinical Precision Interface - Professional Medical Aesthetic
st.markdown("""
<style>
    /* IMPORT PROFESSIONAL FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* BASE STYLES */
    .main {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* HEADER STYLES */
    .clinical-header {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 50%, #14b8a6 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .clinical-header h1 {
        font-size: 1.75rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.025em;
    }

    .clinical-header .subtitle {
        font-size: 0.875rem;
        opacity: 0.9;
        margin-top: 0.5rem;
        font-weight: 400;
    }

    .clinical-header .badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 0.75rem;
        backdrop-filter: blur(8px);
    }

    /* STATUS CARDS */
    .status-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    }

    .status-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .status-card.success { border-left: 4px solid #10b981; }
    .status-card.warning { border-left: 4px solid #f59e0b; }
    .status-card.error { border-left: 4px solid #ef4444; }
    .status-card.info { border-left: 4px solid #3b82f6; }

    /* PROGRESS STEPS */
    .progress-step {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid #e5e7eb;
    }

    .progress-step.active {
        background: #ecfdf5;
        border-color: #10b981;
    }

    .progress-step.completed {
        background: #f0fdf4;
        border-color: #22c55e;
    }

    .progress-step-icon {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.875rem;
        margin-right: 0.75rem;
        flex-shrink: 0;
    }

    .progress-step.active .progress-step-icon {
        background: #10b981;
        color: white;
    }

    .progress-step.completed .progress-step-icon {
        background: #22c55e;
        color: white;
    }

    /* METRIC DISPLAY */
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 600;
        letter-spacing: -0.05em;
    }

    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    /* CODE PREVIEW */
    .code-preview {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        background: #1e293b;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        overflow-x: auto;
        line-height: 1.6;
        border: 1px solid #334155;
    }

    /* DEBUG PANEL */
    .debug-panel {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1rem 0;
    }

    .debug-panel h4 {
        color: #991b1b;
        margin-top: 0;
        font-size: 0.875rem;
        font-weight: 600;
    }

    /* FOOTER */
    .clinical-footer {
        text-align: center;
        color: #64748b;
        font-size: 0.8rem;
        padding: 2rem 1rem;
        border-top: 1px solid #e5e7eb;
        margin-top: 3rem;
    }

    /* HIDE STREAMLIT ELEMENTS */
    .stDeployButton { display: none; }

    /* CUSTOM BUTTONS */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DEMO DATA
# =============================================================================

DEMO_DATA = {
    'meta': {
        'material_name': '推杆 (Push Rod)',
        'material_code': '1M131AISI1011000',
        'batch_no': 'JSR25121502',
        'supplier': '思纳福 (Sinoflow)',
        'date': '2025-12-15'
    },
    'dimensions': [
        {
            'name': '位置 1 - 长度',
            'spec': '27.80+0.10-0.00',
            'nominal': 27.80,
            'usl': 27.90,
            'lsl': 27.80,
            'mean': 27.8314,
            'std_dev_overall': 0.02195,
            'cp': 0.759,
            'cpk': 0.477,
            'pp': 0.760,
            'ppk': 0.480,
            'conclusion': '合格-过程不稳 (Cpk: 0.48)',
            'suggestion': '【红色警示】过程能力不足 (Cpk<1.0)。建议：1.检查设备精度；2.反馈供方调整工艺；3.增加抽样频次。',
            'measurements': [27.85, 27.84, 27.81, 27.82, 27.85, 27.84, 27.82, 27.85, 27.81, 27.84] * 5
        },
        {
            'name': '位置 2 - 直径',
            'spec': 'Φ6.00±0.10',
            'nominal': 6.00,
            'usl': 6.10,
            'lsl': 5.90,
            'mean': 6.0262,
            'std_dev_overall': 0.02415,
            'cp': 1.38,
            'cpk': 1.02,
            'pp': 1.38,
            'ppk': 1.02,
            'conclusion': '合格-过程能力尚可 (Cpk: 1.02)',
            'suggestion': '过程能力尚可，但仍有改进空间。建议持续监控过程表现。',
            'measurements': [6.02, 6.02, 6.01, 6.01, 6.06, 6.02, 6.04, 6.02, 6.03, 6.03] * 5
        }
    ]
}

# =============================================================================
# MINERU.NET API CLIENT
# =============================================================================

class MinerUClient:
    """Client for MinerU.net OCR API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize client with API key from parameter."""
        self.api_key = api_key or ""
        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }

    def upload_pdf(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Upload PDF to MinerU.net for OCR processing.

        Uses two-step process per official API:
        1. POST to /api/v4/file-urls/batch to get upload URLs
        2. PUT file to the returned upload URL (no Content-Type header!)

        Returns batch_id for later status checking.
        """
        # Step 1: Get upload URLs using correct API format
        batch_url = f"{self.base_url}/file-urls/batch"
        batch_data = {
            "files": [{"name": filename}],
            "model_version": "vlm"
        }

        try:
            # Step 1: Get upload URL
            batch_response = requests.post(batch_url, headers=self.headers, json=batch_data, timeout=30)
            batch_response.raise_for_status()
            batch_result = batch_response.json()

            if batch_result.get('code') != 0:
                return {'success': False, 'error': batch_result.get('msg', 'Failed to get upload URL')}

            # Extract batch_id and upload URLs from response
            data = batch_result.get('data', {})
            batch_id = data.get('batch_id')
            file_urls = data.get('file_urls', [])

            if not file_urls:
                return {'success': False, 'error': 'No upload URL returned'}

            upload_url = file_urls[0]  # First file's upload URL

            # Step 2: Upload file to the provided URL
            # IMPORTANT: Do NOT set Content-Type header per API docs
            upload_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            upload_response = requests.put(upload_url, headers=upload_headers, data=pdf_bytes, timeout=120)
            upload_response.raise_for_status()

            return {
                'success': True,
                'batch_id': batch_id,
                'message': 'PDF uploaded successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_task_status(self, batch_id: str) -> Dict[str, Any]:
        """Check the status of a batch OCR task using /api/v4/extract-results/batch/{batch_id} endpoint.

        For batch uploads, use batch_id instead of task_id.
        """
        status_url = f"{self.base_url}/extract-results/batch/{batch_id}"
        try:
            response = requests.get(status_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != 0:
                return {'success': False, 'error': result.get('msg')}

            data = result.get('data', {})
            extract_result = data.get('extract_result', [])

            if not extract_result:
                return {'success': False, 'error': 'No extract result found'}

            # Get first file's result (we only upload one file at a time)
            first_result = extract_result[0]

            return {
                'success': True,
                'state': first_result.get('state'),
                'md_url': first_result.get('full_md_link'),  # Use markdown link, not ZIP
                'err_msg': first_result.get('err_msg')
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def wait_for_completion(self, batch_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for OCR batch task to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.check_task_status(batch_id)

            if not status.get('success'):
                return status

            state = status.get('state')
            if state == 'done':
                return {'success': True, 'md_url': status.get('md_url')}
            elif state == 'failed':
                return {'success': False, 'error': status.get('err_msg', 'Processing failed')}

            time.sleep(5)

        return {'success': False, 'error': 'Timeout waiting for processing'}

    def download_markdown(self, md_url: str) -> str:
        """Download OCR results as markdown text."""
        try:
            response = requests.get(md_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            return ""

# =============================================================================
# DATA EXTRACTION FROM OCR RESULTS
# =============================================================================

def parse_html_tables_for_dimensions(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse HTML tables from MinerU.net OCR output to extract dimension data.

    Expected format from MinerU.net:
    <table>
      <tr><td>检验位置</td><td colspan="2">1</td><td colspan="2">11</td><td colspan="2">13</td></tr>
      <tr><td>检验标准</td><td colspan="2">27.80+0.10-0.00(mm)</td>...</tr>
      <tr><td>结果序号</td><td>测试结果</td><td>结果判定</td><td>测试结果</td>...</tr>
      <tr><td>1</td><td>27.85</td><td>☑OK</td><td>6.02</td>...</tr>
      ...
    </table>
    """
    dimensions = []

    # Find all table tags and their content
    table_pattern = r'<table>(.*?)</table>'
    tables = re.findall(table_pattern, markdown_text, re.DOTALL)

    for table_content in tables:
        # Split table into rows
        row_pattern = r'<tr>(.*?)</tr>'
        rows = re.findall(row_pattern, table_content, re.DOTALL)

        if len(rows) < 4:
            continue

        # Extract cells from each row
        table_data = []
        for row in rows:
            # Extract all <td>...</td> cells
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            # Clean cell content (remove HTML tags and extra whitespace)
            clean_cells = []
            for cell in cells:
                clean = re.sub(r'<[^>]+>', '', cell)  # Remove HTML tags
                clean = clean.strip()
                clean_cells.append(clean)
            table_data.append(clean_cells)

        # Look for inspection table pattern
        # Find the row with "检验位置" (Inspection Position)
        position_row_idx = None
        spec_row_idx = None

        for i, row in enumerate(table_data):
            if not row:
                continue
            # Check for position row
            if any('检验位置' in cell or '位置' in cell for cell in row):
                position_row_idx = i
            # Check for spec row (must come after position row)
            elif any('检验标准' in cell or '标准' in cell for cell in row):
                spec_row_idx = i
                break

        if spec_row_idx is None:
            continue

        # Extract specs from the spec row
        spec_row = table_data[spec_row_idx]
        specs = []
        spec_col_indices = []  # Track which columns have specs

        # Skip first column (it's the label "检验标准")
        for i in range(1, len(spec_row)):
            cell = spec_row[i]
            # Check if it looks like a spec (contains numbers and ±, +, -)
            if re.search(r'[\d.]+[+\-±]', cell):
                spec_match = re.search(r'[\d.]+[+\-]?[\d.]*[+\-±]?[\d.]*', cell)
                if spec_match:
                    specs.append(spec_match.group(0))
                    spec_col_indices.append(i)

        if not specs:
            continue

        # Find the data rows - start from the row after spec row
        # Look for rows where first cell is a sequence number (1, 2, 3, ...)
        # Note: The table may have multiple sections with repeated spec headers
        measurement_sets = {i: [] for i in range(len(specs))}

        for row_idx in range(spec_row_idx + 1, len(table_data)):
            row = table_data[row_idx]

            if len(row) < 2:
                continue

            # Check if first cell is a number (sequence number) - this indicates a data row
            first_cell = row[0] if row else ""
            if not first_cell.isdigit():
                # Skip rows that aren't data rows (like repeated headers)
                continue

            # Now extract measurements
            # Each spec has corresponding columns in the data row
            # The structure is: seq, pos1_val, pos1_status, pos2_val, pos2_status, ...
            # So for spec i (0-indexed), the value is at column 1 + i*2
            for i, spec_col_idx in enumerate(spec_col_indices):
                # Calculate the data column index based on spec position
                # spec at column j corresponds to data at column 1 + j*2
                data_col_idx = 1 + i * 2

                if data_col_idx < len(row):
                    val_str = row[data_col_idx]
                    try:
                        val = float(val_str)
                        measurement_sets[i].append(val)
                    except ValueError:
                        pass

        # Create dimension entries
        for i in range(len(specs)):
            measurements = measurement_sets[i]
            if len(measurements) >= 5:  # Need at least 5 for SPC
                dimensions.append({
                    'position': f'位置 {i+1}',
                    'spec': specs[i],
                    'measurements': measurements
                })

    return dimensions

def extract_iqc_data_from_markdown(markdown_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract IQC data from OCR markdown output.

    This function parses HTML tables from MinerU.net OCR output to extract:
    - Material information (name, code, batch, supplier, date)
    - Dimension measurements with specs
    - Specification limits
    """
    try:
        lines = markdown_text.split('\n')

        # Default metadata
        meta = {
            'material_name': 'Unknown Material',
            'material_code': 'N/A',
            'batch_no': 'N/A',
            'supplier': 'Unknown',
            'date': datetime.now().strftime('%Y-%m-%d')
        }

        # Extract metadata patterns
        for line in lines:
            # Material name patterns
            if re.search(r'(物料|产品|零件|名称|Material)', line, re.IGNORECASE):
                match = re.search(r'[:：]\s*(.+?)(?:\s|$|<)', line)
                if match:
                    meta['material_name'] = match.group(1).strip()

            # Material code patterns
            elif re.search(r'(编码|代号|图号|Code)', line, re.IGNORECASE):
                match = re.search(r'[:：]\s*([A-Z0-9\-]+)', line)
                if match:
                    meta['material_code'] = match.group(1).strip()

            # Batch number patterns
            elif re.search(r'(批号|批次|Batch|Lot)', line, re.IGNORECASE):
                match = re.search(r'[:：]\s*(\S+)', line)
                if match:
                    meta['batch_no'] = match.group(1).strip()

            # Supplier patterns
            elif re.search(r'(供应商|厂家|Supplier)', line, re.IGNORECASE):
                match = re.search(r'[:：]\s*(.+?)(?:\s|$|<)', line)
                if match:
                    meta['supplier'] = match.group(1).strip()

            # Date patterns
            elif re.search(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})', line):
                match = re.search(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})', line)
                if match:
                    meta['date'] = match.group(1).replace('/', '-').replace('.', '-')

        # Extract dimension data from HTML tables
        dimensions = parse_html_tables_for_dimensions(markdown_text)

        # Calculate statistics for each dimension
        dimensions_data = []
        for dim_data in dimensions:
            try:
                dim_result = parse_dimension_from_data(
                    dim_data['position'],
                    dim_data['spec'],
                    dim_data['measurements']
                )
                dimensions_data.append(dim_result)
            except Exception as e:
                import traceback
                st.warning(f"Warning: Could not process dimension {dim_data.get('position', 'Unknown')}: {e}")
                with st.expander("🔍 Full Error Details"):
                    st.code(traceback.format_exc(), language="python")

        if not dimensions_data:
            st.error("❌ No valid dimension data could be extracted. Please check the PDF format.")
            return None

        return generate_iqc_data(
            meta['material_name'],
            meta['material_code'],
            meta['batch_no'],
            meta['supplier'],
            meta['date'],
            dimensions_data
        )
    except Exception as e:
        st.error(f"❌ Error extracting data: {e}")
        return None

# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render professional header with Summed Medtech branding."""
    st.markdown("""
    <div class="clinical-header">
        <h1>⚕️ Summed Medtech - IQC Analysis</h1>
        <div class="subtitle">Incoming Quality Control with Statistical Process Control</div>
        <div class="badge">INTERNAL USE ONLY</div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar with app info and controls."""
    with st.sidebar:
        st.markdown("## 🏢 Summed Medtech")

        st.markdown("**Internal Quality Control System**")

        st.markdown("---")

        st.markdown("### 📋 App Status")

        # Demo mode toggle - uses key="demo_mode" to auto-manage session_state
        st.checkbox("🎯 Demo Mode",
                   help="Use sample data for testing without OCR processing",
                   value=False,
                   key="demo_mode")

        # Debug mode toggle - uses key="debug_mode" to auto-manage session_state
        st.checkbox("🔍 Debug Mode",
                   help="Show OCR raw results and extraction details",
                   value=False,
                   key="debug_mode")

        st.markdown("---")

        st.markdown("### 📖 Workflow Steps")
        st.markdown("""
        1. 📤 Upload PDF report
        2. 🚀 Start OCR processing
        3. 🔍 Extract dimension data
        4. 📊 Review statistics
        5. 📄 Generate report
        """)

        st.markdown("---")

        st.markdown("> ⚠️ **INTERNAL USE ONLY**")
        st.markdown("> Confidential and proprietary")

        st.markdown("---")

        st.markdown("### 🔗 Quick Links")
        st.markdown("- [MinerU.net](https://mineru.net)")
        st.markdown("- [API Docs](https://mineru.net/doc/docs/)")

        st.markdown("---")

        st.markdown(f"<small>© {datetime.now().year} Summed Medtech</small>",
                   unsafe_allow_html=True)

def render_upload_section():
    """Render PDF upload section with visual feedback."""
    st.markdown("### 📤 Upload Inspection Report")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        uploaded_file = st.file_uploader(
            "Select a PDF file",
            type=['pdf'],
            label_visibility="visible",
            help="Upload scanned inspection report (max 200MB)",
            accept_multiple_files=False
        )

        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file

            # Success feedback
            st.markdown(f"""
            <div class="status-card success">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.5rem;">✅</span>
                    <div>
                        <div style="font-weight: 600; color: #065f46;">File Ready</div>
                        <div style="font-size: 0.875rem; color: #047857;">{uploaded_file.name}</div>
                        <div style="font-size: 0.75rem; color: #64748b;">{uploaded_file.size / 1024 / 1024:.2f} MB</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    return uploaded_file if not st.session_state.get('demo_mode', False) else "DEMO_MODE"

def render_processing_section(uploaded_file):
    """Render OCR processing section with step-by-step progress."""
    st.markdown("### ⚙️ OCR Processing")

    if uploaded_file == "DEMO_MODE":
        st.info("🎯 Demo Mode: Using sample data - no PDF processing needed")
        st.session_state.ocr_results = "DEMO_MODE"
        return "DEMO_MODE"

    if not uploaded_file:
        st.markdown("""
        <div class="status-card info">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">📁</span>
                <div>
                    <div style="font-weight: 500; color: #1e40af;">Upload PDF First</div>
                    <div style="font-size: 0.875rem; color: #64748b;">Select a PDF inspection report to begin processing</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None

    # API Key check
    api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))

    if not api_key:
        st.markdown(f"""
        <div class="status-card error">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">🔑</span>
                <div>
                    <div style="font-weight: 600; color: #991b1b;">API Key Not Configured</div>
                    <div style="font-size: 0.875rem; color: #7f1d1d;">
                        Add <code>MINERU_API_KEY</code> to Streamlit Cloud secrets<br/>
                        <a href="https://mineru.net" target="_blank">Get API Key →</a>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 Start OCR Processing", type="primary", use_container_width=True,
                   disabled=st.session_state.get('processing', False)):
            st.session_state.processing = True

            # Progress steps container
            progress_container = st.container()

            with progress_container:
                st.markdown("""
                <div class="progress-step active">
                    <div class="progress-step-icon">1</div>
                    <div>
                        <div style="font-weight: 600;">Uploading PDF...</div>
                        <div style="font-size: 0.875rem; color: #64748b;">Sending to MinerU.net OCR service</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            try:
                client = MinerUClient(api_key)
                pdf_bytes = uploaded_file.read()

                # Upload
                with st.spinner("Uploading PDF..."):
                    upload_result = client.upload_pdf(pdf_bytes, uploaded_file.name)

                if not upload_result.get('success'):
                    st.markdown(f"""
                    <div class="status-card error">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">❌</span>
                            <div>
                                <div style="font-weight: 600; color: #991b1b;">Upload Failed</div>
                                <div style="font-size: 0.875rem; color: #7f1d1d;">{upload_result.get('error', 'Unknown error')}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.session_state.processing = False
                    return None

                batch_id = upload_result.get('batch_id')

                with progress_container:
                    st.markdown("""
                    <div class="progress-step completed">
                        <div class="progress-step-icon">✓</div>
                        <div>
                            <div style="font-weight: 600;">PDF Uploaded</div>
                            <div style="font-size: 0.875rem; color: #059669;">Batch ID: {batch_id[:12]}...</div>
                        </div>
                    </div>
                    <div class="progress-step active">
                        <div class="progress-step-icon">2</div>
                        <div>
                            <div style="font-weight: 600;">Processing...</div>
                            <div style="font-size: 0.875rem; color: #64748b;">Extracting text & tables (1-2 min)</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Wait for completion with progress
                progress_bar = st.progress(0)
                status_text = st.empty()

                result = client.wait_for_completion(batch_id, timeout=300)

                if result.get('success'):
                    progress_bar.progress(1.0)
                    status_text.text("✅ Processing complete!")

                    # Download markdown
                    md_url = result.get('md_url')
                    markdown_text = client.download_markdown(md_url)

                    if markdown_text:
                        st.session_state.ocr_results = markdown_text

                        with progress_container:
                            st.markdown("""
                            <div class="progress-step completed">
                                <div class="progress-step-icon">✓</div>
                                <div>
                                    <div style="font-weight: 600;">Processing Complete</div>
                                    <div style="font-size: 0.875rem; color: #059669;">OCR extraction successful</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                        # Debug mode: Show raw OCR results
                        if st.session_state.get('debug_mode', False):
                            with st.expander("🔍 Raw OCR Results (Debug)", expanded=False):
                                st.markdown("#### 📝 Extracted Markdown Preview")
                                st.markdown(f"*First 2000 characters:*")
                                st.code(markdown_text[:2000], language="markdown")
                                st.markdown(f"*Total length: {len(markdown_text)} characters*")

                    else:
                        st.error("Failed to download OCR results")
                        st.session_state.processing = False
                        return None
                else:
                    st.markdown(f"""
                    <div class="status-card error">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">⚠️</span>
                            <div>
                                <div style="font-weight: 600; color: #991b1b;">Processing Failed</div>
                                <div style="font-size: 0.875rem; color: #7f1d1d;">{result.get('error', 'Unknown error')}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.session_state.processing = False
                    return None

            except Exception as e:
                import traceback
                error_details = str(e) + "\n\n" + traceback.format_exc()
                st.markdown(f"""
                <div class="status-card error">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.5rem;">⚠️</span>
                        <div>
                            <div style="font-weight: 600; color: #991b1b;">Processing Error</div>
                            <div style="font-size: 0.875rem; color: #7f1d1d;"><pre style="white-space: pre-wrap; font-size: 0.75rem;">{error_details[:2000]}</pre></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.processing = False
                return None

            st.session_state.processing = False

    # Show results if available
    if st.session_state.get('ocr_results') and st.session_state.ocr_results != "DEMO_MODE":
        st.markdown("""
        <div class="status-card success">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">✅</span>
                <div>
                    <div style="font-weight: 600; color: #065f46;">OCR Complete</div>
                    <div style="font-size: 0.875rem; color: #047857;">Ready to extract dimension data</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    return st.session_state.get('ocr_results')

def render_data_extraction_section(ocr_text):
    """Render data extraction section with debugging and validation."""
    st.markdown("### 🔍 Extract & Validate Data")

    if not ocr_text:
        st.markdown("""
        <div class="status-card info">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">⏳</span>
                <div>
                    <div style="font-weight: 500; color: #1e40af;">Waiting for OCR Results</div>
                    <div style="font-size: 0.875rem; color: #64748b;">Complete OCR processing first to extract data</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None

    if ocr_text == "DEMO_MODE":
        st.session_state.iqc_data = DEMO_DATA
        return DEMO_DATA

    # Debug mode: Show parsing analysis
    if st.session_state.get('debug_mode', False):
        with st.expander("🔍 Debug: OCR Analysis", expanded=False):
            st.markdown("#### 📊 Parsing Diagnostics")

            # Count tables found
            table_count = len(re.findall(r'<table>', ocr_text))
            st.metric("Tables Found", table_count)

            # Look for dimension table
            has_position_table = bool(re.search(r'检验位置', ocr_text))
            has_spec_table = bool(re.search(r'检验标准', ocr_text))
            st.metric("Has Position Table", "✓" if has_position_table else "✗")
            st.metric("Has Spec Table", "✓" if has_spec_table else "✗")

            # Sample raw text
            st.markdown("#### 📝 Sample Raw Text (First 500 chars)")
            st.code(ocr_text[:500], language="text")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        extract_button = st.button("🔍 Extract IQC Data", type="primary", use_container_width=True)

    if extract_button or st.session_state.get('iqc_data'):
        if not st.session_state.get('iqc_data'):
            with st.spinner("🔄 Extracting measurement data and calculating statistics..."):
                iqc_data = extract_iqc_data_from_markdown(ocr_text)

                if iqc_data:
                    st.session_state.iqc_data = iqc_data

                    st.markdown("""
                    <div class="status-card success">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">✅</span>
                            <div>
                                <div style="font-weight: 600; color: #065f46;">Data Extracted Successfully</div>
                                <div style="font-size: 0.875rem; color: #047857;">{len(iqc_data['dimensions'])} dimension(s) found</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Show detailed error guidance
                    st.markdown("""
                    <div class="debug-panel">
                        <h4>🔍 Extraction Failed - Troubleshooting Guide</h4>

                        <div style="font-size: 0.875rem; color: #7f1d1d;">
                            <strong>Possible issues:</strong>
                            <ol style="margin: 0.5rem 0; padding-left: 1.25rem;">
                                <li>PDF format doesn't match expected template</li>
                                <li>OCR didn't capture dimension tables correctly</li>
                                <li>Table structure is different from expected format</li>
                            </ol>
                        </div>

                        <div style="margin-top: 1rem; font-size: 0.875rem;">
                            <strong>📝 Try these steps:</strong>
                            <ol style="margin: 0.5rem 0; padding-left: 1.25rem;">
                                <li>Enable <strong>Debug Mode</strong> in sidebar to see OCR results</li>
                                <li>Check if the PDF has dimension measurement tables</li>
                                <li>Ensure PDF is clear and high-resolution</li>
                                <li>Try with a different inspection report format</li>
                            </ol>
                        </div>

                        <div style="margin-top: 1rem;">
                            <st>💡 <strong>Tip:</strong> Use Demo Mode above to test the app with sample data.</st>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Display extracted data
        if st.session_state.get('iqc_data'):
            data = st.session_state.iqc_data

            # Metadata
            st.markdown("#### 📋 Material Information")

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Material", data['meta']['material_name'][:15])
            with col2:
                st.metric("Code", data['meta']['material_code'])
            with col3:
                st.metric("Batch", data['meta']['batch_no'])
            with col4:
                st.metric("Supplier", data['meta']['supplier'][:12])
            with col5:
                st.metric("Date", data['meta']['date'])

            st.markdown("---")

            # Dimensions
            st.markdown("#### 📏 SPC Analysis Results")

            for dim in data['dimensions']:
                # Color code based on Cpk
                cpk = dim['cpk']
                if cpk >= 1.33:
                    status_color = "#10b981"  # Green
                    status_icon = "✅"
                elif cpk >= 1.0:
                    status_color = "#f59e0b"  # Yellow
                    status_icon = "⚠️"
                else:
                    status_color = "#ef4444"  # Red
                    status_icon = "❌"

                with st.expander(f"{status_icon} {dim['name']} - {dim['spec']}", expanded=False):
                    # Metrics row
                    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)

                    with mcol1:
                        st.markdown(f"<div class='metric-label'>Cp</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-value' style='color: {status_color};'>{dim['cp']:.3f}</div>", unsafe_allow_html=True)

                    with mcol2:
                        st.markdown(f"<div class='metric-label'>Cpk</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-value' style='color: {status_color};'>{dim['cpk']:.3f}</div>", unsafe_allow_html=True)

                    with mcol3:
                        st.markdown(f"<div class='metric-label'>Mean</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-value'>{dim['mean']:.4f}</div>", unsafe_allow_html=True)

                    with mcol4:
                        st.markdown(f"<div class='metric-label'>Std Dev</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-value'>{dim['std_dev_overall']:.5f}</div>", unsafe_allow_html=True)

                    with mcol5:
                        st.markdown(f"<div class='metric-label'>Samples</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='metric-value'>{len(dim['measurements'])}</div>", unsafe_allow_html=True)

                    st.markdown("---")

                    # Conclusion
                    st.markdown(f"**Status:** {dim['conclusion']}")

                    # Suggestion
                    if "不足" in dim['suggestion'] or "红色" in dim['suggestion']:
                        st.markdown(f"<span style='color: #dc2626;'>**Recommendation:** {dim['suggestion']}</span>", unsafe_allow_html=True)
                    elif "尚可" in dim['suggestion']:
                        st.markdown(f"<span style='color: #d97706;'>**Recommendation:** {dim['suggestion']}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Recommendation:** {dim['suggestion']}")

                    # Measurements
                    with st.expander("📊 View All Measurements", expanded=False):
                        st.dataframe(
                            {'Value': dim['measurements']},
                            use_container_width=True,
                            height=200
                        )

            return st.session_state.iqc_data

    return None

def render_report_section(iqc_data):
    """Render report generation section."""
    st.markdown("### 📊 Generate Report")

    if not iqc_data:
        st.markdown("""
        <div class="status-card info">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">📋</span>
                <div>
                    <div style="font-weight: 500; color: #1e40af;">Extract Data First</div>
                    <div style="font-size: 0.875rem; color: #64748b;">Generate SPC report after extracting dimension data</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        report_format = st.radio(
            "Format",
            ["HTML (Interactive)", "PDF (via Browser Print)"],
            horizontal=True
        )

        if st.button("📄 Generate Report", type="primary", use_container_width=True):
            with st.spinner("🔄 Generating report..."):
                try:
                    template_path = Path(__file__).parent / "iqc-report" / "assets" / "iqc_template.html"

                    if not template_path.exists():
                        st.error(f"Template not found at: {template_path}")
                        return

                    html_content = template_path.read_text(encoding='utf-8')
                    data_json = json.dumps(iqc_data, ensure_ascii=False, indent=8)
                    html_content = html_content.replace("const iqcData = {};", f"const iqcData = {data_json};")

                    report_filename = f"IQC_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    st.session_state.report_generated = True
                    st.session_state.report_content = html_content
                    st.session_state.report_filename = report_filename

                    st.markdown("""
                    <div class="status-card success">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">✅</span>
                            <div>
                                <div style="font-weight: 600; color: #065f46;">Report Generated Successfully</div>
                                <div style="font-size: 0.875rem; color: #047857;">Ready to download</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Download button
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=html_content.encode('utf-8'),
                        file_name=report_filename,
                        mime='text/html',
                        use_container_width=True
                    )

                    # Preview
                    st.markdown("#### 📋 Report Preview")
                    st.components.v1.html(html_content, height=800, scrolling=True)

                except Exception as e:
                    st.markdown(f"""
                    <div class="status-card error">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">❌</span>
                            <div>
                                <div style="font-weight: 600; color: #991b1b;">Report Generation Failed</div>
                                <div style="font-size: 0.875rem; color: #7f1d1d;">{str(e)}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    # Reset session state for demo mode changes
    if 'demo_mode' not in st.session_state:
        st.session_state.demo_mode = False
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False

    render_header()
    render_sidebar()

    # Main workflow
    uploaded_file = render_upload_section()

    if uploaded_file:
        ocr_text = render_processing_section(uploaded_file)

        if ocr_text:
            iqc_data = render_data_extraction_section(ocr_text)

            if iqc_data:
                render_report_section(iqc_data)

    # Footer
    st.markdown("""
    <div class="clinical-footer">
        <p><strong>© Summed Medtech</strong> - Internal Quality Control System</p>
        <p>⚠️ <strong>INTERNAL USE ONLY</strong> - Confidential and Proprietary</p>
        <p>🔧 Powered by <a href="https://mineru.net" target="_blank" style="color: #0d9488;">MinerU.net</a> | ISO 13485 Compliant</p>
        <p style="margin-top: 0.5rem; font-size: 0.75rem;">💡 For best results: Use clear, high-resolution scans of inspection reports</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
