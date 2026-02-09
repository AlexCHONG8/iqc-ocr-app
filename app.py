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
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import requests

# Configure logging for debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
            'std_dev_within': 0.02195,
            'cp': 0.759,
            'cpk': 0.477,
            'pp': 0.760,
            'ppk': 0.480,
            'min_val': 27.81,
            'max_val': 27.85,
            'six_sigma_spread': 0.1317,
            'status': 'OK',
            'conclusion': '合格-过程不稳 (Cpk: 0.48)',
            'suggestion': '【红色警示】过程能力不足 (Cpk<1.0)。建议：1.检查设备精度；2.反馈供方调整工艺；3.增加抽样频次。',
            'measurements': [27.85, 27.84, 27.81, 27.82, 27.85, 27.84, 27.82, 27.85, 27.81, 27.84] * 5,
            'subgroups': [{'mean': 27.834, 'range': 0.04}, {'mean': 27.832, 'range': 0.04}, {'mean': 27.828, 'range': 0.04}, {'mean': 27.834, 'range': 0.04}, {'mean': 27.832, 'range': 0.04}, {'mean': 27.828, 'range': 0.04}, {'mean': 27.834, 'range': 0.04}, {'mean': 27.832, 'range': 0.04}, {'mean': 27.828, 'range': 0.04}, {'mean': 27.832, 'range': 0.04}],
            'x_bar_bar': 27.8314,
            'r_bar': 0.04,
            'ucl_x': 27.8545,
            'lcl_x': 27.8083,
            'ucl_r': 0.0846,
            'lcl_r': 0.0
        },
        {
            'name': '位置 2 - 直径',
            'spec': 'Φ6.00±0.10',
            'nominal': 6.00,
            'usl': 6.10,
            'lsl': 5.90,
            'mean': 6.0262,
            'std_dev_overall': 0.02415,
            'std_dev_within': 0.02415,
            'cp': 1.38,
            'cpk': 1.02,
            'pp': 1.38,
            'ppk': 1.02,
            'min_val': 6.01,
            'max_val': 6.06,
            'six_sigma_spread': 0.1449,
            'status': 'OK',
            'conclusion': '合格-过程能力尚可 (Cpk: 1.02)',
            'suggestion': '过程能力尚可，但仍有改进空间。建议持续监控过程表现。',
            'measurements': [6.02, 6.02, 6.01, 6.01, 6.06, 6.02, 6.04, 6.02, 6.03, 6.03] * 5,
            'subgroups': [{'mean': 6.024, 'range': 0.05}, {'mean': 6.022, 'range': 0.05}, {'mean': 6.028, 'range': 0.05}, {'mean': 6.024, 'range': 0.05}, {'mean': 6.022, 'range': 0.05}, {'mean': 6.028, 'range': 0.05}, {'mean': 6.024, 'range': 0.05}, {'mean': 6.022, 'range': 0.05}, {'mean': 6.028, 'range': 0.05}, {'mean': 6.028, 'range': 0.05}],
            'x_bar_bar': 6.0262,
            'r_bar': 0.05,
            'ucl_x': 6.0551,
            'lcl_x': 5.9973,
            'ucl_r': 0.1057,
            'lcl_r': 0.0
        },
        {
            'name': '位置 3 - 外径',
            'spec': '73.20+0.00-0.15',
            'nominal': 73.20,
            'usl': 73.20,
            'lsl': 73.05,
            'mean': 73.148,
            'std_dev_overall': 0.0297,
            'std_dev_within': 0.0297,
            'cp': 1.684,
            'cpk': 1.237,
            'pp': 1.685,
            'ppk': 1.238,
            'min_val': 73.09,
            'max_val': 73.20,
            'six_sigma_spread': 0.178,
            'status': 'OK',
            'conclusion': '合格-过程能力充足 (Cpk: 1.24)',
            'suggestion': '过程能力充足 (Cpk>1.33)，建议继续保持当前工艺参数。可考虑放宽检验频次以节约成本。',
            'measurements': [73.14, 73.12, 73.15, 73.12, 73.10, 73.15, 73.19, 73.19, 73.15, 73.13, 73.19, 73.18, 73.16, 73.18, 73.13, 73.10, 73.11, 73.20, 73.16, 73.16, 73.18, 73.14, 73.14, 73.19, 73.11, 73.19, 73.09, 73.16, 73.16, 73.19, 73.10, 73.19, 73.15, 73.16, 73.13, 73.18, 73.18, 73.15, 73.11, 73.11, 73.17, 73.16, 73.15, 73.15, 73.14, 73.19, 73.18, 73.15, 73.13, 73.11],
            'subgroups': [{'mean': 73.136, 'range': 0.09}, {'mean': 73.154, 'range': 0.10}, {'mean': 73.154, 'range': 0.06}, {'mean': 73.156, 'range': 0.07}, {'mean': 73.142, 'range': 0.10}, {'mean': 73.138, 'range': 0.10}, {'mean': 73.150, 'range': 0.09}, {'mean': 73.156, 'range': 0.10}, {'mean': 73.158, 'range': 0.07}, {'mean': 73.144, 'range': 0.08}],
            'x_bar_bar': 73.148,
            'r_bar': 0.086,
            'ucl_x': 73.180,
            'lcl_x': 73.116,
            'ucl_r': 0.182,
            'lcl_r': 0.0
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
        self.logger = logging.getLogger(__name__)

    def upload_pdf(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Upload PDF to MinerU.net for OCR processing.

        Uses two-step process per official API:
        1. POST to /api/v4/file-urls/batch to get upload URLs
        2. PUT file to the returned upload URL (no Content-Type header!)

        Returns batch_id for later status checking.
        """
        self.logger.info(f"Starting PDF upload: {filename}, size: {len(pdf_bytes)} bytes")
        
        # Validate API key first
        if not self.api_key:
            self.logger.error("Upload failed: No API key configured")
            return {'success': False, 'error': 'API key not configured. Please set MINERU_API_KEY in Streamlit Cloud secrets.'}
        
        # Step 1: Get upload URLs using correct API format
        batch_url = f"{self.base_url}/file-urls/batch"
        batch_data = {
            "files": [{"name": filename}],
            "model_version": "vlm"
        }

        try:
            # Step 1: Get upload URL
            self.logger.debug(f"POST {batch_url}")
            batch_response = requests.post(batch_url, headers=self.headers, json=batch_data, timeout=30)
            batch_response.raise_for_status()
            batch_result = batch_response.json()
            
            self.logger.debug(f"Batch API response: {batch_result}")

            if batch_result.get('code') != 0:
                error_msg = batch_result.get('msg', 'Failed to get upload URL')
                self.logger.error(f"Batch API error: {error_msg}")
                return {'success': False, 'error': f"API Error: {error_msg}"}

            # Extract batch_id and upload URLs from response
            data = batch_result.get('data', {})
            batch_id = data.get('batch_id')
            file_urls = data.get('file_urls', [])

            if not batch_id:
                self.logger.error("No batch_id in API response")
                return {'success': False, 'error': 'No batch_id returned from API'}

            if not file_urls:
                self.logger.error("No upload URL in API response")
                return {'success': False, 'error': 'No upload URL returned from API'}

            upload_url = file_urls[0]  # First file's upload URL
            self.logger.info(f"Got batch_id: {batch_id[:20]}..., upload URL ready")

            # Step 2: Upload file to the provided URL
            # IMPORTANT: Do NOT set Content-Type header per API docs
            upload_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            }
            
            # Adaptive timeout based on file size (at least 60s, up to 180s for large files)
            file_size_mb = len(pdf_bytes) / (1024 * 1024)
            upload_timeout = max(60, min(180, int(file_size_mb * 5)))  # 5 seconds per MB
            self.logger.debug(f"Upload timeout: {upload_timeout}s for {file_size_mb:.1f}MB file")
            
            upload_response = requests.put(upload_url, headers=upload_headers, data=pdf_bytes, timeout=upload_timeout)
            upload_response.raise_for_status()
            
            self.logger.info(f"PDF upload successful: {filename}")

            return {
                'success': True,
                'batch_id': batch_id,
                'message': 'PDF uploaded successfully'
            }
            
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Upload timeout: {e}")
            return {'success': False, 'error': f'Upload timeout. File may be too large or network is slow. Try a smaller PDF or check your connection.'}
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            return {'success': False, 'error': f'Cannot connect to MinerU.net. Please check your internet connection.'}
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            if e.response.status_code == 401:
                return {'success': False, 'error': 'Authentication failed. Please check your API key is correct and not expired.'}
            elif e.response.status_code == 413:
                return {'success': False, 'error': 'File too large. Maximum file size is 200MB.'}
            else:
                return {'success': False, 'error': f'Server error (HTTP {e.response.status_code}). Please try again later.'}
        except Exception as e:
            self.logger.error(f"Unexpected upload error: {e}")
            return {'success': False, 'error': f'Upload failed: {str(e)}'}

    def check_task_status(self, batch_id: str) -> Dict[str, Any]:
        """Check the status of a batch OCR task using /api/v4/extract-results/batch/{batch_id} endpoint.

        For batch uploads, use batch_id instead of task_id.
        """
        status_url = f"{self.base_url}/extract-results/batch/{batch_id}"
        try:
            response = requests.get(status_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            result = response.json()

            # DEBUG: Log full API response structure
            logger = logging.getLogger(__name__)
            logger.debug(f"=== Batch API Response for {batch_id} ===")
            logger.debug(f"Full response: {result}")
            logger.debug(f"Top-level keys: {list(result.keys())}")
            if 'data' in result:
                logger.debug(f"Data keys: {list(result.get('data', {}).keys())}")
                extract_result = result.get('data', {}).get('extract_result', [])
                logger.debug(f"Extract result count: {len(extract_result)}")
                if extract_result:
                    logger.debug(f"First result keys: {list(extract_result[0].keys())}")
                    logger.debug(f"First result: {extract_result[0]}")

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
                'zip_url': first_result.get('full_zip_url'),  # Also return ZIP URL for fallback
                'err_msg': first_result.get('err_msg')
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_task_from_tasks_endpoint(self, batch_id: str) -> Dict[str, Any]:
        """Get task with full_md_link using /api/v4/tasks endpoint.

        The batch endpoint doesn't return full_md_link, but tasks endpoint does.
        This method searches the tasks list for a matching batch_id.
        """
        tasks_url = f"{self.base_url}/tasks"
        try:
            response = requests.get(tasks_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != 0:
                return {'success': False, 'error': result.get('msg')}

            tasks = result.get('data', {}).get('list', [])

            # Find task where batch_id is part of task_id
            for task in tasks:
                task_id = task.get('task_id', '')
                if batch_id in task_id:
                    return {
                        'success': True,
                        'state': task.get('state'),
                        'md_url': task.get('full_md_link'),
                        'err_msg': task.get('err_msg')
                    }

            return {'success': False, 'error': 'Task not found in tasks list'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _derive_md_link_from_zip_url(self, zip_url: str) -> Optional[str]:
        """Derive full_md_link from full_zip_url.

        Pattern:
        - ZIP: https://cdn-mineru.openxlab.org.cn/pdf/2026-02-07/ID.zip
        - MD:  https://cdn-mineru.openxlab.org.cn/result/2026-02-07/ID/full.md
        """
        if not zip_url:
            return None

        # Replace /pdf/ with /result/
        # Replace .zip with /full.md
        try:
            if '/pdf/' in zip_url and zip_url.endswith('.zip'):
                md_link = zip_url.replace('/pdf/', '/result/').replace('.zip', '/full.md')
                return md_link
        except Exception:
            pass

        return None

    def wait_for_completion(self, batch_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for OCR batch task to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.check_task_status(batch_id)

            if not status.get('success'):
                return status

            state = status.get('state')
            if state == 'done':
                md_url = status.get('md_url')
                zip_url = status.get('zip_url')

                # Try tasks endpoint first for full_md_link
                if not md_url:
                    task_result = self.get_task_from_tasks_endpoint(batch_id)
                    if task_result.get('success') and task_result.get('md_url'):
                        md_url = task_result.get('md_url')

                # Use zip_url as fallback (download_markdown will extract full.md from ZIP)
                download_url = md_url or zip_url

                if download_url:
                    return {'success': True, 'md_url': download_url}
                else:
                    return {'success': False, 'error': 'Task done but no download URL available'}
            elif state == 'failed':
                return {'success': False, 'error': status.get('err_msg', 'Processing failed')}

            time.sleep(5)

        return {'success': False, 'error': 'Timeout waiting for processing'}

    def download_markdown(self, md_url: str) -> str:
        """Download OCR results as markdown text.

        Handles both direct markdown URLs and ZIP URLs (extracts full.md).
        """
        # Validate URL before making request
        if not md_url or not isinstance(md_url, str):
            return ""

        log = logging.getLogger(__name__)

        try:
            response = requests.get(md_url, timeout=30)
            response.raise_for_status()

            # If it's a ZIP file, extract full.md
            if md_url.endswith('.zip') or response.headers.get('Content-Type') == 'application/zip':
                import zipfile
                import io

                log.debug(f"Downloading ZIP file from {md_url}")
                zip_content = response.content

                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    # Look for full.md in the ZIP
                    if 'full.md' in z.namelist():
                        md_content = z.read('full.md').decode('utf-8')
                        log.debug(f"Extracted full.md from ZIP: {len(md_content)} characters")
                        return md_content
                    else:
                        log.warning(f"full.md not found in ZIP. Files: {z.namelist()}")
                        return ""

            # Otherwise, treat as direct markdown text
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            log.error(f"Error downloading markdown: {e}")
            return ""

# =============================================================================
# DATA EXTRACTION FROM OCR RESULTS
# =============================================================================

def statistical_extractor(markdown_text: str) -> List[Dict[str, Any]]:
    """
    FOOLPROOF extractor based on pure statistical analysis.
    Works with ANY format - only looks at numbers, not structure.
    
    ENHANCED: Distance-based clustering to separate multiple measurement points.

    Algorithm:
    1. Find ALL decimal numbers in text
    2. Sort and identify gaps between measurement groups
    3. Group numbers by distance clustering
    4. Calculate nominal and tolerance from statistics
    """
    try:
        # Step 1: Extract ALL numbers from the entire document
        all_numbers = []
        for match in re.finditer(r'\d+\.?\d*', markdown_text):
            try:
                num = float(match.group())
                # Filter reasonable measurement values
                if 0.01 <= num <= 1000:
                    all_numbers.append(num)
            except:
                pass

        logging.info(f"Statistical extractor: Found {len(all_numbers)} numbers in OCR text")

        if len(all_numbers) < 15:
            logging.info(f"Statistical extractor: Not enough numbers ({len(all_numbers)} < 15)")
            return []

        # ENHANCED: Distance-based clustering instead of frequency-based
        # This correctly separates 3 measurement points even if frequencies overlap
        
        # Sort all numbers
        sorted_nums = sorted(all_numbers)
        
        # Find natural gaps between measurement groups
        # A gap is defined as > 20% difference between consecutive numbers
        gaps = []
        for i in range(1, len(sorted_nums)):
            prev_val = sorted_nums[i-1]
            curr_val = sorted_nums[i]
            if prev_val > 0:
                gap_ratio = (curr_val - prev_val) / prev_val
                if gap_ratio > 0.20:  # 20% gap indicates separate measurement point
                    gaps.append((i, curr_val))
        
        logging.debug(f"Statistical extractor: Found {len(gaps)} gaps: {gaps}")
        
        # Create clusters based on gaps
        clusters = []
        rejected_clusters = []  # Track rejected clusters for debugging
        start_idx = 0
        
        for gap_idx, gap_val in gaps:
            cluster_values = sorted_nums[start_idx:gap_idx]
            if len(cluster_values) >= 3:  # ENHANCED: Lowered from 5 to 3
                cluster_center = sum(cluster_values) / len(cluster_values)
                clusters.append({
                    'center': round(cluster_center, 2),
                    'values': cluster_values,
                    'count': len(cluster_values)
                })
            else:
                rejected_clusters.append({
                    'center': round(sum(cluster_values) / len(cluster_values), 2) if cluster_values else 0,
                    'count': len(cluster_values),
                    'reason': 'too_few_points'
                })
            start_idx = gap_idx
        
        # Add final cluster
        final_cluster = sorted_nums[start_idx:]
        if len(final_cluster) >= 3:  # ENHANCED: Lowered from 5 to 3
            cluster_center = sum(final_cluster) / len(final_cluster)
            clusters.append({
                'center': round(cluster_center, 2),
                'values': final_cluster,
                'count': len(final_cluster)
            })
        else:
            rejected_clusters.append({
                'center': round(sum(final_cluster) / len(final_cluster), 2) if final_cluster else 0,
                'count': len(final_cluster),
                'reason': 'too_few_points'
            })
        
        logging.info(f"Statistical extractor: {len(clusters)} valid clusters, {len(rejected_clusters)} rejected")
        for r in rejected_clusters:
            logging.info(f"  Rejected: center={r['center']}, count={r['count']}, reason={r['reason']}")
        
        # If no gaps found but we have enough numbers, try frequency-based fallback
        if not clusters and len(all_numbers) >= 15:
            logging.info("No gaps found, trying frequency-based clustering")
            from collections import Counter
            rounded = [round(n, 1) for n in all_numbers]  # Round to 1 decimal for broader grouping
            freq = Counter(rounded)
            
            # Find top 3 most frequent values as cluster centers
            top_values = [v for v, c in freq.most_common(3) if c >= 3]
            
            for center_val in top_values:
                # Gather values within 5% of center
                cluster_values = [n for n in all_numbers 
                                if abs(n - center_val) <= center_val * 0.05]
                if len(cluster_values) >= 3:  # ENHANCED: Lowered from 5 to 3
                    clusters.append({
                        'center': center_val,
                        'values': cluster_values,
                        'count': len(cluster_values)
                    })
        
        # ENHANCED: If we have fewer than 3 clusters but enough data, try k-means style partitioning
        if len(clusters) < 3 and len(all_numbers) >= 30:
            logging.info(f"Only {len(clusters)} clusters found, trying partitioning...")
            # Sort existing clusters by center
            clusters = sorted(clusters, key=lambda x: x['center'])
            
            # If we have 2 clusters and expect 3, try to split the largest one
            if len(clusters) == 2:
                # Find the cluster with most variance (might contain 2 specs)
                largest_cluster = max(clusters, key=lambda x: max(x['values']) - min(x['values']))
                cluster_idx = clusters.index(largest_cluster)
                
                # Try to split by finding a sub-gap within this cluster
                cluster_vals = sorted(largest_cluster['values'])
                if len(cluster_vals) >= 10:
                    # Find midpoint
                    mid_idx = len(cluster_vals) // 2
                    split_val = cluster_vals[mid_idx]
                    
                    # Split into two
                    lower_vals = [v for v in cluster_vals if v <= split_val]
                    upper_vals = [v for v in cluster_vals if v > split_val]
                    
                    if len(lower_vals) >= 3 and len(upper_vals) >= 3:
                        # Replace original cluster with two new ones
                        clusters.pop(cluster_idx)
                        clusters.insert(cluster_idx, {
                            'center': round(sum(upper_vals) / len(upper_vals), 2),
                            'values': upper_vals,
                            'count': len(upper_vals)
                        })
                        clusters.insert(cluster_idx, {
                            'center': round(sum(lower_vals) / len(lower_vals), 2),
                            'values': lower_vals,
                            'count': len(lower_vals)
                        })
                        logging.info(f"Split cluster into 2: now have {len(clusters)} clusters")
        
        # Limit to top 3 clusters by count, but preserve all valid ones
        clusters = sorted(clusters, key=lambda x: x['count'], reverse=True)[:3]
        
        logging.info(f"Statistical extractor: Found {len(clusters)} clusters")
        for i, c in enumerate(clusters):
            logging.info(f"  Cluster {i+1}: center={c['center']}, count={c['count']}")

        if not clusters:
            logging.info("Statistical extractor: No clusters found")
            return []

        # Create dimensions from clusters
        dimensions = []
        for i, cluster in enumerate(clusters):
            values = cluster['values']
            
            # Calculate statistics
            nominal = round(sum(values) / len(values), 2)
            
            # Calculate tolerance from variation
            if len(values) >= 2:
                tolerance = round((max(values) - min(values)) / 2, 2)
                tolerance = max(tolerance, 0.01)
            else:
                tolerance = 0.10

            dimensions.append({
                'position': str(i + 1),
                'position_name': f"Point {i + 1}",
                'spec': f"{nominal}±{tolerance}",
                'nominal': nominal,
                'usl': round(nominal + tolerance, 2),
                'lsl': round(nominal - tolerance, 2),
                'measurements': sorted(list(set(values)))[:50]
            })
            
            logging.info(f"Statistical extractor: Created dimension {i+1} with {len(values)} measurements")

        return dimensions

    except Exception as e:
        logging.error(f"Statistical extractor error: {e}")
        return []


def fuzzy_extract_measurements(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Fallback parser using regex patterns when table parsing fails.
    Uses distance-based clustering to separate multiple measurement points.
    """
    try:
        import re
        
        logging.info("Fuzzy extractor: Starting extraction...")
        
        # Extract all decimal numbers from text
        all_numbers = []
        for match in re.finditer(r'\d+\.?\d*', markdown_text):
            try:
                num = float(match.group())
                if 0.01 <= num <= 1000:
                    all_numbers.append(num)
            except:
                pass
        
        logging.info(f"Fuzzy extractor: Found {len(all_numbers)} numbers")
        
        if len(all_numbers) < 10:
            logging.info(f"Fuzzy extractor: Not enough numbers ({len(all_numbers)} < 10)")
            return []
        
        # Use same distance-based clustering as statistical_extractor
        sorted_nums = sorted(all_numbers)
        
        # Find natural gaps (> 20% difference)
        gaps = []
        for i in range(1, len(sorted_nums)):
            prev_val = sorted_nums[i-1]
            curr_val = sorted_nums[i]
            if prev_val > 0 and (curr_val - prev_val) / prev_val > 0.20:
                gaps.append((i, curr_val))
        
        # Create clusters based on gaps
        clusters = []
        start_idx = 0
        
        for gap_idx, gap_val in gaps:
            cluster_values = sorted_nums[start_idx:gap_idx]
            if len(cluster_values) >= 3:  # ENHANCED: Lowered from 5 to 3
                center = sum(cluster_values) / len(cluster_values)
                clusters.append({
                    'center': round(center, 2),
                    'values': cluster_values
                })
            start_idx = gap_idx
        
        # Add final cluster
        final_cluster = sorted_nums[start_idx:]
        if len(final_cluster) >= 3:  # ENHANCED: Lowered from 5 to 3
            center = sum(final_cluster) / len(final_cluster)
            clusters.append({
                'center': round(center, 2),
                'values': final_cluster
            })
        
        # ENHANCED: If fewer than 3 clusters, try to split largest
        if len(clusters) < 3 and len(all_numbers) >= 30:
            clusters = sorted(clusters, key=lambda x: x['center'])
            if len(clusters) == 2:
                largest = max(clusters, key=lambda x: max(x['values']) - min(x['values']))
                idx = clusters.index(largest)
                vals = sorted(largest['values'])
                if len(vals) >= 10:
                    mid = len(vals) // 2
                    lower = [v for v in vals if v <= vals[mid]]
                    upper = [v for v in vals if v > vals[mid]]
                    if len(lower) >= 3 and len(upper) >= 3:
                        clusters.pop(idx)
                        clusters.insert(idx, {'center': round(sum(upper)/len(upper), 2), 'values': upper})
                        clusters.insert(idx, {'center': round(sum(lower)/len(lower), 2), 'values': lower})
        
        # Limit to top 3 clusters
        clusters = clusters[:3]
        
        logging.info(f"Fuzzy extractor: Found {len(clusters)} clusters")
        
        # Build dimensions from clusters
        dimensions = []
        for i, cluster in enumerate(clusters):
            values = cluster['values']
            nominal = round(sum(values) / len(values), 2)
            tol = round((max(values) - min(values)) / 2, 2)
            tol = max(tol, 0.01)
            
            dimensions.append({
                'position': f'位置 {i+1}',
                'spec': f'{nominal}±{tol}',
                'measurements': sorted(list(set(values)))[:50]
            })
            logging.info(f"Fuzzy extractor: Created dimension {i+1} with {len(values)} measurements")
        
        return dimensions
    except Exception as e:
        logging.error(f"Fuzzy extraction error: {e}")
        return []


def parse_html_tables_for_dimensions(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Parse HTML tables AND Markdown tables from MinerU.net OCR output to extract dimension data.

    NOW SUPPORTS:
    1. Single-table format (specs + data in one table)
    2. Split-table format (specs in Table 1, data in Table 2)
    3. Both HTML <table> and Markdown pipe | syntax
    """
    dimensions = []

    # Parse all tables (both HTML and Markdown)
    all_tables = []

    # HTML tables
    html_tables = _parse_html_table_tags(markdown_text)
    logging.info(f"parse_html_tables: Found {len(html_tables)} HTML tables")
    for i, t in enumerate(html_tables):
        logging.info(f"  HTML Table {i}: {len(t)} rows, first row: {t[0] if t else 'empty'}")
    all_tables.extend(html_tables)

    # Markdown tables
    md_tables = _parse_markdown_tables(markdown_text)
    logging.info(f"parse_html_tables: Found {len(md_tables)} Markdown tables")
    all_tables.extend(md_tables)

    # Process tables sequentially with state tracking
    pending_specs = None

    for table_idx, table_data in enumerate(all_tables):
        table_type = _detect_table_type(table_data)
        logging.info(f"Table {table_idx}: Type={table_type}, Rows={len(table_data)}")

        if table_type == "SPECS_ONLY":
            # Extract specs, remember for next table
            pending_specs = _extract_specs_from_table(table_data)
            logging.debug(f"Table {table_idx}: SPECS_ONLY - extracted {len(pending_specs.get('specs', [])) if pending_specs else 0} specs")

        elif table_type == "DATA_TABLE" and pending_specs:
            # Combine pending specs with this data table
            dims = _extract_data_with_specs(table_data, pending_specs)
            logging.debug(f"Table {table_idx}: DATA_TABLE - extracted {len(dims)} dimensions")

            # AGGRESSIVE: Filter out any non-dict items BEFORE adding to dimensions
            filtered_dims = []
            for i, d in enumerate(dims):
                if not isinstance(d, dict):
                    logging.error(f"❌ CRITICAL: Table {table_idx}, Dimension {i} is {type(d).__name__} not dict! Value: {d}")
                else:
                    filtered_dims.append(d)

            logging.debug(f"  After filtering: {len(filtered_dims)} valid dimensions")
            dimensions.extend(filtered_dims)
            pending_specs = None

        elif table_type == "COMPLETE":
            # Single table with everything (backward compatible)
            dims = _extract_dimensions_from_table_data(table_data)
            logging.debug(f"Table {table_idx}: COMPLETE - extracted {len(dims)} dimensions")

            # AGGRESSIVE: Filter out any non-dict items BEFORE adding to dimensions
            filtered_dims = []
            for i, d in enumerate(dims):
                if not isinstance(d, dict):
                    logging.error(f"❌ CRITICAL: Table {table_idx}, Dimension {i} is {type(d).__name__} not dict! Value: {d}")
                else:
                    filtered_dims.append(d)

            logging.debug(f"  After filtering: {len(filtered_dims)} valid dimensions")
            dimensions.extend(filtered_dims)

        else:
            logging.debug(f"Table {table_idx}: {table_type} - skipping")

    # Log final dimensions list
    logging.debug(f"Total dimensions extracted: {len(dimensions)}")
    for i, d in enumerate(dimensions):
        logging.debug(f"Final dimension {i} type: {type(d).__name__}, is_dict: {isinstance(d, dict)}")
        if isinstance(d, dict):
            logging.debug(f"  Keys: {list(d.keys())}")

    # FINAL VALIDATION: Ensure all items are dicts, filter out any contaminants
    clean_dimensions = []
    for i, d in enumerate(dimensions):
        if isinstance(d, dict) and 'position' in d and 'spec' in d and 'measurements' in d:
            clean_dimensions.append(d)
        else:
            logging.error(f"❌ FINAL FILTER: Removed invalid dimension {i}: type={type(d).__name__}, value={d}")

    logging.info(f"✅ Final clean dimensions: {len(clean_dimensions)} (filtered out {len(dimensions) - len(clean_dimensions)} invalid items)")
    return clean_dimensions


def _parse_html_table_tags(markdown_text: str) -> List[List[str]]:
    """Parse HTML <table> tags from text and return raw table data."""
    all_tables = []

    # Find all table tags and their content
    table_pattern = r'<table>(.*?)</table>'
    tables = re.findall(table_pattern, markdown_text, re.DOTALL)

    for table_content in tables:
        # Split table into rows
        row_pattern = r'<tr>(.*?)</tr>'
        rows = re.findall(row_pattern, table_content, re.DOTALL)

        if len(rows) < 2:
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

        all_tables.append(table_data)

    return all_tables


def _parse_markdown_tables(markdown_text: str) -> List[List[str]]:
    """
    Parse Markdown tables with pipe | syntax and return raw table data.

    Handles format:
      | header1 | header2 | header3 |
      |---------|---------|---------|
      | data1   | data2   | data3   |
    """
    all_tables = []
    lines = markdown_text.split('\n')

    i = 0
    while i < len(lines):
        # Find table start (line with |)
        if '|' not in lines[i]:
            i += 1
            continue

        # Collect table rows
        table_lines = []
        j = i
        while j < len(lines) and '|' in lines[j]:
            table_lines.append(lines[j])
            j += 1

        # Need minimum rows for inspection table
        if len(table_lines) < 2:
            i = j
            continue

        # Parse table into cells
        table_data = []
        for line in table_lines:
            # Skip separator rows (e.g., |---|---|---|)
            if re.match(r'^\s*\|?\s*[\-\s]+\|[\-\s|]*\|?\s*$', line):
                continue

            # Remove leading/trailing |
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]

            # Split by | and clean cells
            cells = [cell.strip() for cell in line.split('|')]
            if cells:
                table_data.append(cells)

        if table_data:
            all_tables.append(table_data)

        i = j  # Move past this table

    return all_tables


def _detect_table_type(table_data: List[List[str]]) -> str:
    """
    Detect what kind of table this is.

    Returns:
        "SPECS_ONLY" - Has specs but no data rows
        "DATA_TABLE" - Has data rows with header
        "COMPLETE" - Single table with specs and data
        "UNKNOWN" - Not an inspection table
    """
    if len(table_data) < 2:
        return "UNKNOWN"

    # Flatten all cells for easier checking
    all_cells = [cell for row in table_data for cell in row]

    has_position = any('检验位置' in cell for cell in all_cells)
    has_spec = any('检验标准' in cell for cell in all_cells)
    has_data_header = any('结果序号' in cell or '测试结果' in cell for cell in all_cells)
    has_numeric_rows = any(row and row[0].isdigit() for row in table_data)

    # Complete single table (has BOTH specs AND data) - CHECK FIRST
    if has_position and has_spec and has_data_header and has_numeric_rows and len(table_data) >= 4:
        return "COMPLETE"

    # Specs-only table (small table with position + spec, no data)
    if has_position and has_spec and not has_numeric_rows:
        return "SPECS_ONLY"

    # Data table with header (no specs, just data)
    if has_data_header and has_numeric_rows and not has_spec:
        return "DATA_TABLE"

    return "UNKNOWN"


def _extract_specs_from_table(table_data: List[List[str]]) -> Optional[Dict[str, Any]]:
    """
    Extract specs from a specs-only table.

    Returns: {
        'specs': [...],
        'spec_col_indices': [...],
        'position_names': [...]  # From header row if available
    }
    """
    # Find spec row
    spec_row_idx = None
    position_row_idx = None

    for i, row in enumerate(table_data):
        if not row:
            continue
        if any('检验位置' in cell for cell in row):
            position_row_idx = i
        elif any('检验标准' in cell for cell in row):
            spec_row_idx = i
            break

    if spec_row_idx is None:
        return None

    spec_row = table_data[spec_row_idx]
    specs = []
    spec_col_indices = []

    # Extract position names from previous row if available
    position_names = []
    if position_row_idx is not None and 0 <= position_row_idx < len(table_data):
        position_row = table_data[position_row_idx]
        if position_row:  # Make sure row is not empty
            for i in range(1, len(position_row)):
                position_names.append(position_row[i])

    # Extract specs
    for i in range(1, len(spec_row)):
        cell = spec_row[i]
        if re.search(r'[\d.]+[\+\-±]', cell):
            spec_match = re.search(r'[\d.]+[\+\-]?[\d.]*[\+\-±]?[\d.]*', cell)
            if spec_match:
                specs.append(spec_match.group(0))
                spec_col_indices.append(i)

    if not specs:
        return None

    return {
        'specs': specs,
        'spec_col_indices': spec_col_indices,
        'position_names': position_names
    }


def _extract_data_with_specs(table_data: List[List[str]], specs_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract data from data table using previously extracted specs.

    Table structure:
    Row 0: Header | 结果序号 | 测试结果(1) | 判定 | ...
    Row 1+: Data | 1 | 27.85 | OK | ...
    
    ENHANCED: Better handling of interleaved columns [seq, val, status, val, status...]
    """
    if not specs_info:
        return []

    specs = specs_info.get('specs', [])
    spec_col_indices = specs_info.get('spec_col_indices', [])
    position_names = specs_info.get('position_names', [])

    if not specs or not spec_col_indices:
        return []

    logging.debug(f"_extract_data_with_specs: Processing {len(specs)} specs at columns {spec_col_indices}")

    # Detect if this is an interleaved pattern
    is_interleaved = False
    if len(table_data) > 1:
        sample_row = table_data[1] if len(table_data) > 1 else table_data[0]
        # If row has many columns and follows [seq, val, status, val, status...] pattern
        if len(sample_row) >= 5 and sample_row[0].isdigit():
            numeric_count = 0
            for col_idx in [1, 3]:
                if col_idx < len(sample_row):
                    try:
                        float(sample_row[col_idx])
                        numeric_count += 1
                    except:
                        pass
            if numeric_count >= 1:
                is_interleaved = True
                logging.debug(f"  Detected interleaved pattern")

    # Skip header row, start from data rows
    data_start_idx = 1

    measurement_sets = {i: [] for i in range(len(specs))}

    for row_idx in range(data_start_idx, len(table_data)):
        row = table_data[row_idx]

        if len(row) < 2:
            continue

        first_cell = row[0] if row else ""
        if not first_cell.isdigit():
            continue

        # Extract measurements using multiple strategies
        for i, spec_col_idx in enumerate(spec_col_indices):
            val_found = False

            # Strategy 1: Direct column index (only for compact tables, not interleaved)
            # For interleaved tables, skip this strategy because spec_col_indices
            # don't match data table column positions
            if not is_interleaved and spec_col_idx < len(row):
                val_str = row[spec_col_idx].strip()
                try:
                    val = float(val_str)
                    measurement_sets[i].append(val)
                    val_found = True
                except ValueError:
                    pass

            # Strategy 2: Interleaved pattern for [seq, val, status, val, status...]
            # For data table: use position index i, not spec_col_idx
            # Position 0 → col 0*2+1=1, Position 1 → col 1*2+1=3, Position 2 → col 2*2+1=5
            if not val_found and is_interleaved:
                interleaved_idx = i * 2 + 1  # Use position index i: 0→1, 1→3, 2→5
                if row_idx == data_start_idx:  # Log only for first data row
                    logging.debug(f"    i={i}, spec_col_idx={spec_col_idx}, interleaved_idx={interleaved_idx}")
                if interleaved_idx < len(row):
                    val_str = row[interleaved_idx].strip()
                    if row_idx == data_start_idx:
                        logging.debug(f"    Reading column {interleaved_idx}, value={val_str}")
                    try:
                        val = float(val_str)
                        measurement_sets[i].append(val)
                        val_found = True
                    except ValueError:
                        pass

    logging.debug(f"  Measurements found per dimension: {[len(v) for v in measurement_sets.values()]}")

    # Create dimension entries
    dimensions = []
    for i in range(len(specs)):
        measurements = measurement_sets[i]
        # ENHANCED: Lowered from 5 to 3
        if len(measurements) >= 3:
            position_name = position_names[i] if i < len(position_names) else f'位置 {i+1}'
            dimensions.append({
                'position': position_name,
                'spec': specs[i],
                'measurements': measurements
            })
            logging.debug(f"  Dimension {i+1}: {len(measurements)} measurements")
        else:
            logging.warning(f"  Dimension {i+1}: Only {len(measurements)} measurements, skipping")

    return dimensions


def _extract_dimensions_from_table_data(table_data: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Extract dimension data from parsed table cells (works for both HTML and MD tables).
    
    ENHANCED: Better handling of OCR format variations and column alignment issues.

    Table structure:
    - Row 0: Position headers (检验位置 | 1 | 11 | 13)
    - Row 1: Spec row (检验标准 | 27.80±0.10 | 6.00±0.10 | 73.20±0.15)
    - Row 2+: Data rows (1 | 27.85 | OK | 6.02 | OK | 73.14 | OK)

    Data row pattern: [seq, val1, status1, val2, status2, val3, status3, ...]
    Spec columns: [1, 2, 3] (indices in spec row)
    """
    dimensions = []
    
    logging.debug(f"_extract_dimensions_from_table_data: Processing table with {len(table_data)} rows")

    # Look for inspection table pattern
    position_row_idx = None
    spec_row_idx = None

    for i, row in enumerate(table_data):
        if not row:
            continue
        row_text = ' '.join(row)
        # Check for position row - more flexible matching
        if any(keyword in row_text for keyword in ['检验位置', '位置', '检验点', '测点', 'Position']):
            position_row_idx = i
            logging.debug(f"  Found position row at index {i}: {row_text[:50]}")
        # Check for spec row (must come after position row)
        elif any(keyword in row_text for keyword in ['检验标准', '标准', '规格', 'Spec', 'Tolerance', '±', '+/-']):
            if '位置' not in row_text:  # Avoid matching position row again
                spec_row_idx = i
                logging.debug(f"  Found spec row at index {i}: {row_text[:50]}")
                break

    if spec_row_idx is None:
        logging.debug("  No spec row found, trying alternative detection...")
        # Alternative: look for any row with specs
        for i, row in enumerate(table_data):
            if not row:
                continue
            row_text = ' '.join(row)
            if re.search(r'\d+\.?\d*\s*[±\+\-]', row_text):
                spec_row_idx = i
                logging.debug(f"  Alternative spec row found at index {i}")
                break
        
        if spec_row_idx is None:
            logging.debug("  No spec row found, returning empty")
            return dimensions

    # Extract specs from the spec row
    spec_row = table_data[spec_row_idx]
    specs = []
    spec_col_indices = []

    logging.debug(f"  Processing spec row with {len(spec_row)} columns")

    # Skip first column (it's the label "检验标准")
    for i in range(1, len(spec_row)):
        cell = spec_row[i].strip()
        if not cell:
            continue
            
        # Check if it looks like a spec (contains numbers and ±, +, -)
        # ENHANCED: More flexible spec pattern matching
        if re.search(r'[\d.]+\s*[±\+\-]', cell) or re.search(r'[\d.]+\s*-\s*[\d.]+', cell):
            # Try to extract the spec value
            spec_match = re.search(r'([\d.]+)\s*([±\+\-])\s*([\d.]+)|([\d.]+)\s*-\s*([\d.]+)', cell)
            if spec_match:
                specs.append(cell)  # Keep full cell text for display
                spec_col_indices.append(i)
                logging.debug(f"    Spec {len(specs)} at col {i}: {cell}")

    if not specs:
        logging.debug("  No specs extracted from spec row")
        return dimensions

    logging.debug(f"  Found {len(specs)} specs at columns: {spec_col_indices}")

    # ENHANCED: Try multiple column mapping strategies
    measurement_sets = {i: [] for i in range(len(specs))}

    # Determine if this is an interleaved table pattern
    # HTML table: [seq, val1, status1, val2, status2, val3, status3]
    # Find first DATA row (skip header rows) to determine pattern
    sample_row_idx = spec_row_idx + 1
    is_interleaved = False
    sample_row = None

    # Look for first row where first cell is a digit (actual data row, not header)
    while sample_row_idx < len(table_data):
        candidate_row = table_data[sample_row_idx]
        if candidate_row and candidate_row[0].isdigit():
            sample_row = candidate_row
            break
        sample_row_idx += 1

    if sample_row and len(sample_row) >= 7:
        # Check if odd columns (1, 3, 5...) are numeric values
        numeric_count = 0
        for col_idx in [1, 3, 5]:
            if col_idx < len(sample_row):
                try:
                    float(sample_row[col_idx])
                    numeric_count += 1
                except:
                    pass
        # If at least 2 of the odd columns are numeric, it's interleaved
        if numeric_count >= 2:
            is_interleaved = True
            logging.debug(f"  Detected interleaved table pattern (row len={len(sample_row)})")
    
    strategies_tried = []
    
    for row_idx in range(spec_row_idx + 1, len(table_data)):
        row = table_data[row_idx]

        if len(row) < 2:
            continue

        # Check if first cell is a number (sequence number)
        first_cell = row[0] if row else ""
        if not first_cell.isdigit():
            continue

        # Try multiple strategies for data extraction
        for i, spec_col_idx in enumerate(spec_col_indices):
            val_found = False

            # Strategy 1: Direct index (same as spec column) - only for compact tables
            # For interleaved tables, skip this strategy because spec_col_indices
            # don't match data table column positions
            if not is_interleaved and spec_col_idx < len(row):
                val_str = row[spec_col_idx].strip()
                try:
                    val = float(val_str)
                    measurement_sets[i].append(val)
                    val_found = True
                    if row_idx == spec_row_idx + 1:
                        strategies_tried.append(f"direct_col_{spec_col_idx}")
                except ValueError:
                    pass
            
            # Strategy 2: Interleaved pattern (val at position index * 2 + 1)
            # spec_col_indices from specs table are [1, 2, 3] but data table has columns [1, 3, 5]
            # Formula: i * 2 + 1 converts position index to actual data column indices
            # Position 0 → col 0*2+1=1, Position 1 → col 1*2+1=3, Position 2 → col 2*2+1=5
            if not val_found and is_interleaved:
                interleaved_idx = i * 2 + 1  # Use position index i: 0→1, 1→3, 2→5
                if interleaved_idx < len(row):
                    val_str = row[interleaved_idx].strip()
                    try:
                        val = float(val_str)
                        measurement_sets[i].append(val)
                        val_found = True
                        if row_idx == spec_row_idx + 1:
                            strategies_tried.append(f"interleaved_{interleaved_idx}")
                    except ValueError:
                        pass
            
            # Strategy 3: Next column (for compact tables)
            if not val_found:
                next_idx = spec_col_idx + 1
                if next_idx < len(row):
                    val_str = row[next_idx].strip()
                    try:
                        val = float(val_str)
                        measurement_sets[i].append(val)
                        val_found = True
                        if row_idx == spec_row_idx + 1:
                            strategies_tried.append(f"next_col_{next_idx}")
                    except ValueError:
                        pass

    logging.debug(f"  Is interleaved pattern: {is_interleaved}")
    logging.debug(f"  Strategies tried: {set(strategies_tried)}")
    logging.debug(f"  Measurements found per dimension: {[len(v) for v in measurement_sets.values()]}")

    # Create dimension entries
    for i in range(len(specs)):
        measurements = measurement_sets[i]
        # ENHANCED: Lowered from 5 to 3 for better compatibility
        if len(measurements) >= 3:
            dimensions.append({
                'position': f'位置 {i+1}',
                'spec': specs[i],
                'measurements': measurements
            })
            logging.debug(f"  Dimension {i+1}: {len(measurements)} measurements")
        else:
            logging.warning(f"  Dimension {i+1}: Only {len(measurements)} measurements, skipping")

    logging.debug(f"  Total dimensions extracted: {len(dimensions)}")
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

        # Extract dimension data - TRY TABLE PARSING FIRST (better for structured HTML tables)
        logging.info("Extracting dimensions from OCR text...")
        
        # First try table-based parsing (better for HTML tables with clear structure)
        dimensions_from_tables = parse_html_tables_for_dimensions(markdown_text)
        if dimensions_from_tables and len(dimensions_from_tables) >= 3:
            logging.info(f"Table parsing found {len(dimensions_from_tables)} dimensions, using those")
            dimensions = dimensions_from_tables
        elif dimensions_from_tables and len(dimensions_from_tables) >= 1:
            # Table parsing found some dimensions but less than 3
            logging.info(f"Table parsing found {len(dimensions_from_tables)} dimensions, trying statistical extractor for more...")
            dimensions = dimensions_from_tables
            # Try to add more dimensions from statistical extractor
            stat_dimensions = statistical_extractor(markdown_text)
            # Merge unique dimensions (avoid duplicates)
            existing_centers = [d['nominal'] if 'nominal' in d else sum(d['measurements'])/len(d['measurements']) 
                               for d in dimensions if d.get('measurements')]
            for stat_dim in stat_dimensions:
                if stat_dim.get('measurements'):
                    stat_center = sum(stat_dim['measurements']) / len(stat_dim['measurements'])
                    # Check if this dimension is new (not close to existing)
                    is_new = all(abs(stat_center - existing) > 1.0 for existing in existing_centers)
                    if is_new:
                        dimensions.append(stat_dim)
                        existing_centers.append(stat_center)
                        logging.info(f"Added dimension from statistical extractor: center={stat_center:.2f}")
        else:
            # Table parsing found nothing, use statistical extractor
            logging.info("Table parsing found no dimensions, using statistical extractor...")
            dimensions = statistical_extractor(markdown_text)
            logging.info(f"Statistical extractor returned {len(dimensions)} dimensions")

        # Enhanced debugging and user feedback
        debug_mode = st.session_state.get('debug_mode', False)

        # Parsing statistics
        parsing_stats = {
            'text_length': len(markdown_text),
            'numbers_found': len(re.findall(r'\d+\.?\d*', markdown_text)),
            'tables_found': 0,
            'specs_found': 0,
            'measurements_found': 0,
            'dimensions_extracted': len(dimensions)
        }
        
        # Count measurements in extracted dimensions
        for dim in dimensions:
            if isinstance(dim, dict):
                parsing_stats['measurements_found'] += len(dim.get('measurements', []))

        if debug_mode:
            st.markdown("---")
            st.markdown("### 🔍 OCR Parsing Debug Info")
            
            # Show parsing stats
            st.markdown("**Parsing Statistics:**")
            st.json(parsing_stats)

            # Count tables in OCR output
            table_count = len(re.findall(r'\|.*\|', markdown_text)) // 3  # Rough estimate
            parsing_stats['tables_found'] = table_count
            st.info(f"📊 Found approximately {table_count} tables in OCR output")
            
            # Show number extraction analysis
            all_nums = [float(m.group()) for m in re.finditer(r'\d+\.?\d*', markdown_text) 
                       if 0.01 <= float(m.group()) <= 1000]
            if all_nums:
                st.markdown(f"**Numbers Found:** {len(all_nums)} values")
                st.markdown(f"**Range:** {min(all_nums):.2f} to {max(all_nums):.2f}")
                
                # Show distribution histogram
                st.markdown("**📊 Number Distribution:**")
                sorted_nums = sorted(all_nums)
                if len(sorted_nums) > 10:
                    min_val = min(sorted_nums)
                    max_val = max(sorted_nums)
                    if max_val > min_val:
                        bin_size = (max_val - min_val) / 5
                        bins = [0] * 5
                        for n in sorted_nums:
                            bin_idx = min(int((n - min_val) / bin_size), 4)
                            bins[bin_idx] += 1
                        
                        for i, count in enumerate(bins):
                            bin_start = min_val + i * bin_size
                            bin_end = min_val + (i + 1) * bin_size
                            bar = "█" * min(count // 2, 50)
                            st.markdown(f"{bin_start:.2f}-{bin_end:.2f}: {bar} ({count})")
                
                st.markdown(f"**Sample values:** {', '.join([f'{n:.2f}' for n in sorted_nums[:30]])}")
            else:
                st.warning("⚠️ No numeric values detected in OCR output")

            # Show sample of OCR output
            with st.expander("📄 Raw OCR Output (first 3000 chars)", expanded=False):
                st.code(markdown_text[:3000], language="markdown")

            # Show what dimensions were extracted
            if dimensions:
                st.success(f"✅ Parsed {len(dimensions)} dimension(s) from OCR")
                parsing_stats['specs_found'] = len(dimensions)
                
                # Show detailed dimension info
                st.markdown("**📐 Extracted Dimensions:**")
                for i, dim in enumerate(dimensions):
                    if isinstance(dim, dict):
                        meas = dim.get('measurements', [])
                        spec = dim.get('spec', 'N/A')
                        st.markdown(f"**Dimension {i+1}:** {spec}")
                        st.markdown(f"  - Position: {dim.get('position', 'N/A')}")
                        st.markdown(f"  - Measurements: {len(meas)} values")
                        if meas:
                            st.markdown(f"  - Range: {min(meas):.2f} - {max(meas):.2f}")
                            st.markdown(f"  - First 10: {', '.join([f'{m:.2f}' for m in meas[:10]])}")
                for dim in dimensions:
                    if isinstance(dim, dict):
                        parsing_stats['measurements_found'] += len(dim.get('measurements', []))
                st.json(parsing_stats)
                
                st.markdown("**📐 Extracted Dimensions Details:**")
                for i, dim in enumerate(dimensions):
                    if isinstance(dim, dict):
                        meas = dim.get('measurements', [])
                        spec = dim.get('spec', 'N/A')
                        st.markdown(f"**Dimension {i+1}:** {spec}")
                        st.markdown(f"  - Measurements: {len(meas)} values")
                        if meas:
                            st.markdown(f"  - Range: {min(meas):.2f} - {max(meas):.2f}")
                            st.markdown(f"  - Sample: {', '.join([f'{m:.2f}' for m in meas[:10]])}")
                        st.json(dim)
            else:
                st.warning("⚠️ No dimensions parsed from tables")
                st.markdown("**What was looked for:**")
                st.markdown("- Tables with column headers like: 检验位置, 检验标准")
                st.markdown("- Specification patterns like: 27.85±0.10 or 27.80+0.10-0.00")
                st.markdown("- Measurement rows with numeric data")

        # Debug logging
        logging.info(f"Extracted {len(dimensions)} dimensions from OCR")
        logging.info(f"Parsing stats: {parsing_stats}")
        for i, dim in enumerate(dimensions):
            logging.info(f"  Dimension {i}: type={type(dim).__name__}, is_dict={isinstance(dim, dict)}")
            if not isinstance(dim, dict):
                logging.error(f"    ❌ BUG: Dimension {i} is not a dict! Value: {dim}")

        # Calculate statistics for each dimension
        dimensions_data = []
        parsing_errors = []

        for dim_data in dimensions:
            try:
                # Defensive: Ensure dim_data is a dict before processing
                if not isinstance(dim_data, dict):
                    error_msg = f"Invalid dimension data type ({type(dim_data).__name__})"
                    parsing_errors.append(error_msg)
                    if debug_mode:
                        st.warning(f"⚠️ Warning: {error_msg}")
                    continue

                # Ensure required fields exist
                if 'position' not in dim_data or 'spec' not in dim_data or 'measurements' not in dim_data:
                    error_msg = f"Dimension missing required fields: {list(dim_data.keys())}"
                    parsing_errors.append(error_msg)
                    if debug_mode:
                        st.warning(f"⚠️ Warning: {error_msg}")
                        st.json(dim_data)
                    continue

                dim_result = parse_dimension_from_data(
                    dim_data['position'],
                    dim_data['spec'],
                    dim_data['measurements']
                )
                dimensions_data.append(dim_result)
            except Exception as e:
                import traceback
                error_msg = str(e)
                parsing_errors.append(error_msg)
                position_info = dim_data.get('position') if isinstance(dim_data, dict) else f"Invalid type: {type(dim_data).__name__}"
                st.warning(f"⚠️ Warning: Could not process dimension '{position_info}': {error_msg[:100]}")
                if debug_mode:
                    with st.expander("🔍 Full Error Details"):
                        st.code(traceback.format_exc(), language="python")

        # FUZZY FALLBACK: If structured parsing failed, try fuzzy extraction
        if not dimensions_data:
            st.info("🔍 Structured table parsing failed. Trying fuzzy extraction...")
            fuzzy_dimensions = fuzzy_extract_measurements(markdown_text)

            if fuzzy_dimensions:
                st.success(f"✅ Fuzzy extraction found {len(fuzzy_dimensions)} dimension(s)!")
                parsing_stats['dimensions_extracted'] = len(fuzzy_dimensions)

                if debug_mode:
                    st.markdown("**Fuzzy extracted dimensions:**")
                    for i, dim in enumerate(fuzzy_dimensions):
                        st.markdown(f"**Dimension {i+1}:**")
                        st.json(dim)

                # Process fuzzy extracted dimensions
                for dim_data in fuzzy_dimensions:
                    try:
                        dim_result = parse_dimension_from_data(
                            dim_data['position'],
                            dim_data['spec'],
                            dim_data['measurements']
                        )
                        dimensions_data.append(dim_result)
                    except Exception as e:
                        error_msg = f"Fuzzy extraction error: {str(e)[:100]}"
                        parsing_errors.append(error_msg)
            else:
                st.warning("⚠️ Fuzzy extraction also found no dimensions")
                parsing_stats['dimensions_extracted'] = 0

        # Enhanced error message when no dimensions extracted
        if not dimensions_data:
            st.markdown("---")
            st.markdown("### ❌ No Valid Dimension Data Extracted")
            
            # Show debug info if available
            if debug_mode:
                st.markdown("**Debug Information:**")
                st.json(parsing_stats)
                
                # Show numbers found in text
                all_nums = [float(m.group()) for m in re.finditer(r'\d+\.?\d*', markdown_text) 
                           if 0.01 <= float(m.group()) <= 1000]
                if all_nums:
                    st.markdown(f"**Numbers detected:** {len(all_nums)} values")
                    st.markdown(f"Range: {min(all_nums):.2f} to {max(all_nums):.2f}")
                    st.markdown("Sample values: " + ", ".join([f"{n:.2f}" for n in all_nums[:20]]))
                else:
                    st.warning("⚠️ No numeric values detected in OCR output")

            st.markdown("""
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem; margin: 1rem 0; border-radius: 4px;">
                <div style="font-size: 0.875rem; color: #92400e;">
                    <strong>🔍 What This Means:</strong>
                    <p style="margin: 0.5rem 0;">The OCR successfully read your PDF, but the measurement tables couldn't be parsed. This usually happens when:</p>
                    <ul style="margin: 0.5rem 0; padding-left: 1.25rem;">
                        <li>PDF format doesn't match the expected inspection report template</li>
                        <li>OCR didn't capture dimension tables correctly (handwritten text, low quality)</li>
                        <li>Measurement data is embedded in images or unusual formats</li>
                        <li>Numbers are scattered without clear table structure</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Show troubleshooting steps
            with st.expander("🔧 Troubleshooting Steps", expanded=True):
                st.markdown("""
                **Step 1: Check OCR Quality (Enable Debug Mode)**
                1. Enable 🔍 **Debug Mode** in sidebar
                2. Re-upload the PDF
                3. Look at "Raw OCR Output" to see what was captured
                4. Check if numbers are visible and readable

                **Step 2: For Handwritten Reports**
                Handwritten PDFs often have issues:
                - OCR may not recognize handwritten numbers accurately
                - Table structure may be lost
                - Try these alternatives:
                  - Use Demo Mode and manually enter data
                  - Re-type measurements into Excel/CSV first
                  - Use clearer scanned images (300+ DPI)

                **Step 3: Verify PDF Content**
                Your PDF should contain:
                - Clear numeric measurements (e.g., 27.85, 6.02)
                - Preferably in table format
                - At least 5 measurements per dimension

                **Step 4: Alternative - Manual Entry**
                If OCR consistently fails:
                1. Use 🎯 **Demo Mode** to see the app workflow
                2. Manually enter your measurement data
                3. Or prepare data in CSV format first
                """)

            # Show parsing errors if any
            if parsing_errors:
                with st.expander("📋 Parsing Errors Found"):
                    for i, error in enumerate(set(parsing_errors), 1):
                        st.markdown(f"{i}. {error}")

            # Show helpful tips and alternatives
            st.markdown("---")
            st.markdown("### 💡 Alternatives")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🔍 Debug Mode:**")
                st.markdown("See what OCR actually captured from your PDF.")
                
            with col2:
                st.markdown("**🎯 Demo Mode:**")
                st.markdown("Test with sample data to understand expected format.")
                
            with col3:
                st.markdown("**📝 Manual Entry:**")
                st.markdown("Enter measurements directly if OCR fails.")

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

    # Debug mode indicator
    if st.session_state.get('debug_mode', False):
        st.markdown("""
        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 0.75rem; margin: 1rem 0; border-radius: 4px;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.25rem;">🔍</span>
                <div>
                    <div style="font-weight: 600; color: #92400e;">Debug Mode Enabled</div>
                    <div style="font-size: 0.875rem; color: #b45309;">Raw OCR output and parsing details will be shown</div>
                </div>
            </div>
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

        # Deployment Health Check
        with st.expander("🏥 Deployment Health", expanded=False):
            st.markdown("**System Checks:**")

            # Check API Key
            api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))
            if api_key and len(api_key) > 100:
                st.success("✅ API Key: Configured")
                st.caption(f"Length: {len(api_key)} chars")
            elif api_key:
                st.warning("⚠️ API Key: Short")
                st.caption(f"Length: {len(api_key)} chars (expected 300+)")
            else:
                st.error("❌ API Key: Missing")

            # Environment
            st.markdown("**Environment:**")
            st.markdown(f"- Streamlit: {st.__version__}")
            st.markdown(f"- Max upload: 200MB")

            # Session Status
            if st.session_state.get('processing'):
                st.info("🔄 Processing active")
            if st.session_state.get('ocr_results'):
                st.success("✅ OCR complete")

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
            # Clear old session data when new file is uploaded
            if 'uploaded_file' in st.session_state and st.session_state.uploaded_file != uploaded_file:
                # New file uploaded - clear old data
                st.session_state.ocr_results = None
                st.session_state.iqc_data = None
                st.session_state.processing = False
                logging.info("Cleared old session data for new file upload")

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

    # Enhanced API Key check with validation
    api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))

    # Strip triple quotes if present (Streamlit Cloud requires """ for secrets with special chars)
    if api_key and api_key.startswith('"""') and api_key.endswith('"""'):
        api_key = api_key[3:-3]  # Remove opening and closing triple quotes

    if not api_key:
        st.markdown(f"""
        <div class="status-card error">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.5rem;">🔑</span>
                <div>
                    <div style="font-weight: 600; color: #991b1b;">API Key Not Configured</div>
                    <div style="font-size: 0.875rem; color: #7f1d1d;">
                        Add <code>MINERU_API_KEY</code> to Streamlit Cloud secrets
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔧 How to Fix - Step by Step", expanded=True):
            st.markdown("""
            **Quick Setup (2 minutes):**

            1. **Get API Key**
               - Go to https://mineru.net
               - Log in to your account
               - Copy your API key from dashboard

            2. **Add to Streamlit Cloud**
               - Go to your app in Streamlit Cloud
               - Click: Settings → Secrets
               - Add secret: `MINERU_API_KEY=paste_your_key_here`
               - Click Save

            3. **Restart App**
               - Click Restart button in Streamlit Cloud
               - Wait for app to reload (30 seconds)
               - Try uploading PDF again
            """)
        return None

    # Validate API key format
    if len(api_key) < 100:
        st.warning(f"⚠️ API key seems short ({len(api_key)} chars, expected 300+). May not work correctly.")
    elif not (api_key.startswith('ey') or api_key.startswith('sk-')):
        st.warning("⚠️ API key format unusual. Expected JWT token starting with 'ey'.")

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
                    error_msg = upload_result.get('error', 'Unknown error')

                    # Categorize error for better user guidance
                    if 'timeout' in error_msg.lower():
                        error_title = "Upload Timeout"
                        suggestions = [
                            "PDF file too large (try compressing)",
                            "Network connection slow",
                            "Service temporarily busy"
                        ]
                    elif '401' in error_msg or 'auth' in error_msg.lower():
                        error_title = "Authentication Failed"
                        suggestions = [
                            "API key is invalid or expired",
                            "Check MINERU_API_KEY in Streamlit Cloud secrets",
                            "Get a new key from https://mineru.net"
                        ]
                    elif 'connection' in error_msg.lower():
                        error_title = "Connection Error"
                        suggestions = [
                            "Cannot reach MinerU.net",
                            "Check your internet connection",
                            "Service might be temporarily down"
                        ]
                    else:
                        error_title = "Upload Failed"
                        suggestions = [
                            "Ensure PDF is not password protected",
                            "Check PDF size (max 200MB)",
                            "Try a different PDF file"
                        ]

                    st.markdown(f"""
                    <div class="status-card error">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">❌</span>
                            <div>
                                <div style="font-weight: 600; color: #991b1b;">{error_title}</div>
                                <div style="font-size: 0.875rem; color: #7f1d1d;">{error_msg[:200]}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander("🔧 Troubleshooting Steps", expanded=True):
                        st.markdown("**Possible Solutions:**")
                        for i, suggestion in enumerate(suggestions, 1):
                            st.markdown(f"{i}. {suggestion}")

                        if st.session_state.get('debug_mode', False):
                            st.markdown("---")
                            st.markdown("**Full Error Message:**")
                            st.code(error_msg, language="text")

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

                        # Download OCR output button (always show for debugging)
                        st.download_button(
                            label="📥 Download OCR Output (For Debugging)",
                            data=markdown_text,
                            file_name=f"ocr_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            help="Download raw OCR results to see exactly what was captured from your PDF"
                        )

                        # Debug mode: Show raw OCR results
                        if st.session_state.get('debug_mode', False):
                            with st.expander("🔍 Raw OCR Results (Debug)", expanded=True):
                                st.markdown("#### 📝 Full OCR Output")
                                st.markdown(f"*Total characters: {len(markdown_text):,}*")
                                st.markdown(f"*Lines: {markdown_text.count(chr(10)):,}*")

                                # Show first 5000 chars
                                st.markdown("**First 5000 characters:**")
                                st.code(markdown_text[:5000], language="markdown")

                                if len(markdown_text) > 5000:
                                    st.markdown(f"*... and {len(markdown_text) - 5000:,} more characters*")
                        else:
                            # Suggest debug mode for troubleshooting
                            st.info("💡 **Tip:** Enable 🔍 **Debug Mode** in the sidebar to see raw OCR results and troubleshoot parsing issues.")
                            st.markdown("**Why?** Debug mode shows exactly what the OCR captured, helping you understand why parsing might have failed.")
                    else:
                        # Better error diagnostics
                        if not md_url:
                            st.error("❌ No markdown URL in API response")
                            st.info("💡 Debug: The API returned success but no full_md_link was provided")
                        elif markdown_text == "":
                            st.error(f"❌ Download failed from URL: {md_url[:100]}...")
                            st.info("💡 The URL may be expired or invalid")
                        else:
                            st.error("Failed to download OCR results")

                        if st.session_state.get('debug_mode', False):
                            st.json({"md_url": md_url, "markdown_length": len(markdown_text) if markdown_text else 0})

                        st.session_state.processing = False
                        return None
                else:
                    error_msg = result.get('error', 'Unknown error')

                    # Categorize processing error
                    if 'timeout' in error_msg.lower():
                        error_title = "Processing Timeout"
                        details = [
                            "OCR processing took too long (>5 minutes)",
                            "PDF might be very large or complex",
                            "Service experiencing high load"
                        ]
                    elif 'failed' in error_msg.lower():
                        error_title = "OCR Processing Failed"
                        details = [
                            "Server could not process the PDF",
                            "PDF might be corrupted or low quality",
                            "Unsupported PDF format"
                        ]
                    else:
                        error_title = "Processing Error"
                        details = [
                            "Unexpected error during OCR processing",
                            "Please try again",
                            "Contact support if issue persists"
                        ]

                    st.markdown(f"""
                    <div class="status-card error">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">⚠️</span>
                            <div>
                                <div style="font-weight: 600; color: #991b1b;">{error_title}</div>
                                <div style="font-size: 0.875rem; color: #7f1d1d;">{error_msg[:200]}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander("🔍 Error Details & Solutions", expanded=True):
                        st.markdown("**What Happened:**")
                        for detail in details:
                            st.markdown(f"• {detail}")

                        st.markdown("---")
                        st.markdown("**Try These Steps:**")
                        st.markdown("1. Refresh the page and try again")
                        st.markdown("2. Check if PDF file is valid (not corrupted)")
                        st.markdown("3. Try with a smaller, simpler PDF first")

                        if st.session_state.get('debug_mode', False):
                            st.markdown("---")
                            st.markdown("**Full Error Message:**")
                            st.code(error_msg, language="text")

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
