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
import PyPDF2

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import existing SPC analysis module using dynamic import (directory has hyphen)
import importlib.util
iqc_stats_path = Path(__file__).parent / "iqc-report" / "scripts" / "iqc_stats.py"
spec = importlib.util.spec_from_file_location("iqc_stats", iqc_stats_path)
iqc_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iqc_stats)

# Make functions available directly
calculate_subgroups = iqc_stats.calculate_subgroups
calculate_process_capability = iqc_stats.calculate_process_capability
calculate_control_limits = iqc_stats.calculate_control_limits
parse_dimension_from_data = iqc_stats.parse_dimension_from_data
generate_iqc_data = iqc_stats.generate_iqc_data
generate_html_report = iqc_stats.generate_html_report

# =============================================================================
# CONFIGURATION
# =============================================================================

# Page configuration
st.set_page_config(
    page_title="Summed Medtech - IQC OCR + SPC Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a5f;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background: #dcfce7;
        border: 1px solid #16a34a;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background: #ffedd5;
        border: 1px solid #ea580c;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background: #dbeafe;
        border: 1px solid #2563eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #2563eb;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'ocr_results' not in st.session_state:
        st.session_state.ocr_results = None
    if 'iqc_data' not in st.session_state:
        st.session_state.iqc_data = None
    if 'report_generated' not in st.session_state:
        st.session_state.report_generated = False
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = ""

init_session_state()

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
                'md_url': first_result.get('full_zip_url'),
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
            st.error(f"Failed to download markdown: {e}")
            return ""

# =============================================================================
# DATA EXTRACTION FROM OCR RESULTS
# =============================================================================

def parse_html_tables_for_dimensions(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse HTML tables from MinerU.net OCR output to extract dimension data.

    Expected format:
    <table>
      <tr><td>检验位置</td><td>1</td><td>11</td><td>13</td></tr>
      <tr><td>检验标准</td><td>27.80+0.10-0.00</td><td>Φ6.00±0.10</td><td>73.20+0.00-0.15</td></tr>
      <tr><td>1</td><td>27.85</td><td>6.02</td><td>73.14</td></tr>
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

        if len(rows) < 3:
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
        # First row should have "检验位置" (Inspection Position)
        if not table_data or not any('检验位置' in cell or '位置' in cell for cell in table_data[0]):
            continue

        # Second row should have "检验标准" (Inspection Standard) with specs
        spec_row_idx = None
        for i, row in enumerate(table_data):
            if any('检验标准' in cell or '标准' in cell for cell in row):
                spec_row_idx = i
                break

        if spec_row_idx is None:
            continue

        # Extract position names and specs
        spec_row = table_data[spec_row_idx]
        positions = []
        specs = []

        # Skip first column (it's the label "检验标准")
        for i in range(1, len(spec_row)):
            cell = spec_row[i]
            # Check if it looks like a spec (contains numbers and ±, +, -)
            if re.search(r'[\d.]+[+\-±]', cell):
                # This is a spec - extract it
                spec_match = re.search(r'[\d.]+[+\-]?[\d.]*[+\-±]?[\d.]*', cell)
                if spec_match:
                    specs.append(spec_match.group(0))
                    # Generate position name
                    positions.append(f"位置 {len(positions) + 1}")

        # Now extract measurements from data rows
        # Data rows start after the spec row
        measurement_sets = {i: [] for i in range(len(specs))}

        for row_idx in range(spec_row_idx + 1, len(table_data)):
            row = table_data[row_idx]

            # Skip if this is a header row or summary row
            if len(row) < 2:
                continue

            # Check if first cell is a number (sequence number)
            first_cell = row[0] if row else ""
            if not first_cell.isdigit():
                continue

            # Extract measurements for each position
            # Position i's measurements are in column (i * 2 + 1) because each position has 2 columns (value + OK)
            for i in range(len(specs)):
                col_idx = i * 2 + 1  # Each position has value + OK columns
                if col_idx < len(row):
                    val_str = row[col_idx]
                    # Try to parse as float
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
                    'position': positions[i] if i < len(positions) else f'位置 {i+1}',
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
                st.warning(f"Warning: Could not process dimension {dim_data.get('position', 'Unknown')}: {e}")

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
        st.error(f"❌ Error extracting IQC data: {e}")
        return None

# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render application header."""
    st.markdown('<div class="main-header">🏢 Summed Medtech - IQC OCR + SPC Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Incoming Quality Control with Statistical Process Control | Internal Use Only</div>', unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar():
    """Render sidebar with settings and info."""
    with st.sidebar:
        st.markdown("## 🏢 Summed Medtech")
        st.markdown("**Internal Quality Control System**")
        st.markdown("---")
        st.markdown("> ⚠️ **INTERNAL USE ONLY**")
        st.markdown("> Confidential and proprietary")
        st.markdown("> For authorized personnel only")

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This application processes handwritten inspection reports with OCR and generates ISO 13485 compliant statistical analysis reports.

        **Features:**
        - PDF OCR recognition (109 languages)
        - 6SPC statistical analysis
        - Interactive control charts
        - Process capability indices (Cp, Cpk, Pp, Ppk)
        """)

        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Upload a scanned PDF report
        2. Wait for OCR processing
        3. Review extracted data
        4. Generate and download report
        """)

        st.markdown("---")
        st.markdown("### 🔧 System Status")
        api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))
        if api_key:
            st.markdown("✅ MinerU.net API: Connected")
        else:
            st.markdown("⚠️ MinerU.net API: Not configured")

def render_password_protection():
    """Render password protection for team access."""
    if not st.session_state.authenticated:
        st.markdown("<h3 style='text-align: center;'>🔐 Team Access</h3>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            password = st.text_input("Enter Access Password", type="password", key="password_input")

            if st.button("Login", use_container_width=True):
                # Check password (you can change this)
                correct_password = os.getenv("APP_PASSWORD", "iqc2024")

                if password == correct_password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect password")

        st.markdown("<br><br><p style='text-align: center; color: #64748b;'>Contact administrator for access</p>", unsafe_allow_html=True)
        return False

    return True

def render_upload_section():
    """Render PDF upload section."""
    st.markdown("### 📤 Upload Inspection Report")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        uploaded_file = st.file_uploader(
            "Select a PDF file",
            type=['pdf'],
            label_visibility="collapsed",
            help="Upload scanned inspection report (max 200MB)"
        )

        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.success(f"✅ File uploaded: {uploaded_file.name}")

            # Show file info
            with st.expander("📄 File Information"):
                st.json({
                    "Name": uploaded_file.name,
                    "Size": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
                    "Type": uploaded_file.type
                })

    return st.session_state.uploaded_file

def render_processing_section(uploaded_file):
    """Render OCR processing section."""
    st.markdown("### ⚙️ OCR Processing")

    if not uploaded_file:
        st.info("👆 Please upload a PDF file first.")
        return None

    # Get API key from Streamlit secrets or environment
    api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))

    if not api_key:
        st.error("""
        ❌ MinerU.net API key not configured.

        Please add `MINERU_API_KEY` to `.streamlit/secrets.toml` or Streamlit Cloud settings.

        **Get your API key at:** https://mineru.net
        """)
        return None

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 Start OCR Processing", type="primary", use_container_width=True, disabled=st.session_state.get('processing', False)):
            st.session_state.processing = True

            with st.spinner("🔄 Uploading and processing PDF... This may take 1-2 minutes."):
                try:
                    # Initialize client
                    client = MinerUClient(api_key)

                    # Upload PDF
                    pdf_bytes = uploaded_file.read()
                    upload_result = client.upload_pdf(pdf_bytes, uploaded_file.name)

                    if not upload_result.get('success'):
                        st.error(f"❌ Upload failed: {upload_result.get('error')}")
                        st.session_state.processing = False
                        return None

                    batch_id = upload_result.get('batch_id')
                    st.info(f"✅ PDF uploaded. Batch ID: {batch_id}")

                    # Create progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Wait for completion
                    max_wait = 300  # 5 minutes
                    waited = 0
                    check_interval = 5

                    while waited < max_wait:
                        time.sleep(check_interval)
                        waited += check_interval

                        progress = min(waited / 120, 0.9)  # Assume 2 minutes is 90%
                        progress_bar.progress(progress)
                        status_text.text(f"Processing... ({waited}s elapsed)")

                        result = client.check_task_status(batch_id)

                        if result.get('success'):
                            state = result.get('state')
                            if state == 'done':
                                progress_bar.progress(1.0)
                                status_text.text("✅ Processing complete!")

                                md_url = result.get('md_url')
                                markdown_text = client.download_markdown(md_url)

                                st.session_state.ocr_results = markdown_text

                                st.success("✅ OCR processing completed successfully!")
                                st.session_state.processing = False
                                break
                            elif state == 'failed':
                                st.error(f"❌ Processing failed: {result.get('err_msg', 'Unknown error')}")
                                st.session_state.processing = False
                                break
                        else:
                            st.warning(f"⚠️ Checking status...")

                    if waited >= max_wait:
                        st.warning("⏱️ Processing is taking longer than expected. Please check back later.")
                        st.session_state.processing = False

                except Exception as e:
                    st.error(f"❌ Error during processing: {e}")
                    st.session_state.processing = False

        # Show results if available
        if st.session_state.ocr_results:
            with st.expander("📝 OCR Results (Markdown)", expanded=False):
                st.text(st.session_state.ocr_results[:2000] + "..." if len(st.session_state.ocr_results) > 2000 else st.session_state.ocr_results)

            return st.session_state.ocr_results

    return st.session_state.ocr_results

def render_data_extraction_section(ocr_text):
    """Render data extraction and validation section."""
    st.markdown("### 🔍 Extract & Validate Data")

    if not ocr_text:
        st.info("⏳ Complete OCR processing first to extract data.")
        return None

    if st.button("🔍 Extract IQC Data", type="secondary", use_container_width=True):
        with st.spinner("🔄 Extracting measurement data and calculating statistics..."):
            iqc_data = extract_iqc_data_from_markdown(ocr_text)

            if iqc_data:
                st.session_state.iqc_data = iqc_data
                st.success("✅ Data extracted successfully!")

    # Display extracted data
    if st.session_state.iqc_data:
        data = st.session_state.iqc_data

        # Show metadata
        cols = st.columns(5)
        with cols[0]:
            st.metric("Material", data['meta']['material_name'][:20])
        with cols[1]:
            st.metric("Code", data['meta']['material_code'])
        with cols[2]:
            st.metric("Batch", data['meta']['batch_no'])
        with cols[3]:
            st.metric("Supplier", data['meta']['supplier'][:15])
        with cols[4]:
            st.metric("Date", data['meta']['date'])

        st.markdown("---")

        # Show dimensions
        st.markdown("#### 📏 Extracted Dimensions")

        for dim in data['dimensions']:
            with st.expander(f"🔬 {dim['name']} - Spec: {dim['spec']}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Cp", f"{dim['cp']:.3f}",
                             delta_color="normal" if dim['cpk'] >= 1.33 else "inverse")
                with col2:
                    st.metric("Cpk", f"{dim['cpk']:.3f}",
                             delta_color="normal" if dim['cpk'] >= 1.33 else "inverse")
                with col3:
                    st.metric("Mean", f"{dim['mean']:.4f}")
                with col4:
                    st.metric("Std Dev", f"{dim['std_dev_overall']:.5f}")

                st.markdown(f"**Status:** {dim['conclusion']}")
                st.markdown(f"**Suggestion:** {dim['suggestion']}")

                st.markdown("**Measurements:**")
                st.dataframe(
                    {'Value': dim['measurements']},
                    use_container_width=True,
                    height=150
                )

        return st.session_state.iqc_data

    return None

def render_report_section(iqc_data):
    """Render report generation section."""
    st.markdown("### 📊 Generate Report")

    if not iqc_data:
        st.info("👆 Extract data first to generate a report.")
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Report options
        report_format = st.radio(
            "Report Format",
            ["HTML (Interactive)", "PDF (Static)"],
            horizontal=True
        )

        if st.button("📄 Generate Report", type="primary", use_container_width=True):
            with st.spinner("🔄 Generating report..."):
                try:
                    # Use existing template and function
                    template_path = Path(__file__).parent / "iqc-report" / "assets" / "iqc_template.html"

                    # Read template
                    html_content = template_path.read_text(encoding="utf-8")

                    # Inject data
                    data_json = json.dumps(iqc_data, ensure_ascii=False, indent=8)
                    html_content = html_content.replace("const iqcData = {};", f"const iqcData = {data_json};")

                    # Save to temp file
                    report_filename = f"IQC_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

                    if report_format == "HTML (Interactive)":
                        # Provide HTML download
                        st.session_state.report_generated = True
                        st.session_state.report_content = html_content
                        st.session_state.report_filename = report_filename

                        st.success("✅ Report generated successfully!")

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

                    else:
                        st.info("📝 PDF generation requires additional setup. Download HTML and open in browser, then use 'Print to PDF'.")

                except Exception as e:
                    st.error(f"❌ Error generating report: {e}")

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    # Render UI components
    render_header()
    render_sidebar()

    # Password protection (can be disabled for public access)
    # if not render_password_protection():
    #     return

    # Main workflow
    uploaded_file = render_upload_section()

    if uploaded_file:
        ocr_text = render_processing_section(uploaded_file)

        if ocr_text:
            iqc_data = render_data_extraction_section(ocr_text)

            if iqc_data:
                render_report_section(iqc_data)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #64748b; font-size: 0.9rem;'>
    <p><strong>© Summed Medtech</strong> - Internal Quality Control System</p>
    <p>⚠️ <strong>INTERNAL USE ONLY</strong> - Confidential and Proprietary</p>
    <p>🔧 Powered by <a href='https://mineru.net' target='_blank'>MinerU.net</a> | ISO 13485 Compliant</p>
    <p>💡 <strong>Tip:</strong> For best results, use clear, high-resolution scans of inspection reports.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
