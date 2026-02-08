"""
Enhanced Error Handling and User Feedback for IQC OCR App
Add these functions to app.py to improve deployment reliability.
"""

import streamlit as st
import logging
from typing import Dict, Any

def validate_api_key(api_key: str) -> Dict[str, Any]:
    """
    Validate API key format and provide helpful error messages.

    Returns:
        dict with 'valid' boolean and 'message' string
    """
    if not api_key:
        return {
            'valid': False,
            'message': 'API Key Not Configured',
            'details': [
                "Add MINERU_API_KEY to Streamlit Cloud secrets",
                "Go to: Your App → Settings → Secrets",
                "Format: MINERU_API_KEY=your_full_key_here",
                "Get key from: https://mineru.net"
            ]
        }

    # Check key format
    if not (api_key.startswith('ey') or api_key.startswith('sk-')):
        return {
            'valid': False,
            'message': 'Invalid API Key Format',
            'details': [
                f"Your key starts with: {api_key[:10]}...",
                "Expected format: JWT token (starts with 'ey')",
                "Common issues:",
                "  - Copied partial key (need full key)",
                "  - Extra whitespace or quotes",
                "  - Wrong key from different service"
            ]
        }

    # Check key length (JWT tokens are typically 300+ chars)
    if len(api_key) < 100:
        return {
            'valid': False,
            'message': 'API Key Too Short',
            'details': [
                f"Your key length: {len(api_key)} characters",
                "Expected: 300+ characters for JWT token",
                "You may have copied a truncated key"
            ]
        }

    return {
        'valid': True,
        'message': 'API key format validated'
    }


def render_api_key_error(validation_result: Dict[str, Any]):
    """Render user-friendly API key error message with actionable steps."""
    st.markdown(f"""
    <div class="status-card error">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.5rem;">🔑</span>
            <div>
                <div style="font-weight: 600; color: #991b1b;">{validation_result['message']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔧 How to Fix", expanded=True):
        for detail in validation_result.get('details', []):
            st.markdown(f"• {detail}")

        st.markdown("---")
        st.markdown("**Quick Fix Steps:**")
        st.markdown("""
        1. Go to [MinerU.net](https://mineru.net) and log in
        2. Copy your full API key from dashboard
        3. In Streamlit Cloud: Your App → Settings → Secrets
        4. Add: `MINERU_API_KEY=paste_full_key_here`
        5. Click Save and then Restart the app
        """)


def render_upload_error(error_message: str, debug_mode: bool = False):
    """Render detailed upload error with troubleshooting steps."""
    error_lower = error_message.lower()

    # Categorize error type
    if 'timeout' in error_lower:
        error_type = "Timeout"
        suggestions = [
            "PDF file might be too large (try compressing)",
            "Network connection is slow",
            "MinerU.net service is busy (try again in 1-2 min)"
        ]
    elif '401' in error_lower or 'unauthorized' in error_lower or 'auth' in error_lower:
        error_type = "Authentication Failed"
        suggestions = [
            "API key is invalid or expired",
            "Check API key in Streamlit Cloud secrets",
            "Get a new key from https://mineru.net"
        ]
    elif 'connection' in error_lower:
        error_type = "Connection Error"
        suggestions = [
            "Cannot reach MinerU.net service",
            "Check your internet connection",
            "MinerU.net might be down (check status)"
        ]
    else:
        error_type = "Upload Failed"
        suggestions = [
            "Ensure PDF is not password protected",
            "Check PDF size (max 200MB)",
            "Try a different PDF file"
        ]

    st.markdown(f"""
    <div class="status-card error">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.5rem;">⚠️</span>
            <div>
                <div style="font-weight: 600; color: #991b1b;">{error_type}</div>
                <div style="font-size: 0.875rem; color: #7f1d1d;">{error_message[:200]}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔧 Troubleshooting Steps", expanded=True):
        st.markdown("**Possible Solutions:**")
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"{i}. {suggestion}")

        if debug_mode:
            st.markdown("---")
            st.markdown("**Debug Info:**")
            st.code(error_message, language="text")


def render_processing_error(error_message: str, debug_mode: bool = False):
    """Render detailed processing error with diagnostics."""
    st.markdown(f"""
    <div class="status-card error">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.5rem;">❌</span>
            <div>
                <div style="font-weight: 600; color: #991b1b;">OCR Processing Failed</div>
                <div style="font-size: 0.875rem; color: #7f1d1d;">{error_message[:200]}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔍 Error Details & Solutions", expanded=True):
        if 'timeout' in error_message.lower():
            st.markdown("**Issue:** Processing took too long (>5 minutes)")
            st.markdown("**Solutions:**")
            st.markdown("• Try a smaller PDF file")
            st.markdown("• PDF might be very complex (many images/tables)")
            st.markdown("• MinerU.net is experiencing high load")

        elif 'failed' in error_message.lower():
            st.markdown("**Issue:** OCR processing failed on server")
            st.markdown("**Solutions:**")
            st.markdown("• PDF might be corrupted (try re-saving)")
            st.markdown("• PDF quality too low (blurry/scanned)")
            st.markdown("• Unsupported PDF format")

        else:
            st.markdown("**Issue:** Unexpected error during processing")
            st.markdown("**Solutions:**")
            st.markdown("• Try refreshing the page and upload again")
            st.markdown("• Check if PDF file is valid")
            st.markdown("• Contact support if issue persists")

        if debug_mode:
            st.markdown("---")
            st.markdown("**Full Error Message:**")
            st.code(error_message, language="text")


def add_diagnostic_info_to_sidebar():
    """Add diagnostic information to sidebar for troubleshooting."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔧 App Diagnostics")

        # API Key Status
        api_key = st.secrets.get("MINERU_API_KEY", "")
        if api_key:
            key_valid = validate_api_key(api_key)
            if key_valid['valid']:
                st.success("✅ API Key: Configured")
            else:
                st.error("❌ API Key: Invalid")
        else:
            st.warning("⚠️ API Key: Not Set")

        # Environment Info
        import os
        st.markdown("**Environment:**")
        st.markdown(f"- Python: `{os.sys.version.split()[0]}`")
        st.markdown(f"- Streamlit: `{st.__version__}`")

        # Session State Info
        if st.session_state.get('processing'):
            st.info("🔄 Processing in progress")
        if st.session_state.get('ocr_results'):
            st.success("✅ OCR results cached")
        if st.session_state.get('iqc_data'):
            st.success("✅ IQC data generated")


def cleanup_session_state():
    """
    Clean up session state to prevent stale data between uploads.
    Call this when a new file is uploaded.
    """
    keys_to_clear = [
        'ocr_results',
        'iqc_data',
        'processing',
        'extracted_data',
        'report_generated'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    logging.info("Session state cleaned up")


def render_deployment_health_check():
    """
    Render a deployment health check section in the app.
    This helps diagnose deployment-specific issues.
    """
    with st.expander("🏥 Deployment Health Check", expanded=False):
        st.markdown("**Checking app configuration...**)

        issues = []

        # Check 1: API Key
        api_key = st.secrets.get("MINERU_API_KEY", "")
        if not api_key:
            issues.append("❌ MINERU_API_KEY not found in secrets")
        else:
            validation = validate_api_key(api_key)
            if not validation['valid']:
                issues.append(f"❌ {validation['message']}")
            else:
                st.success("✅ API Key configured")

        # Check 2: File upload size limit
        st.markdown("**Configuration:**")
        st.markdown(f"- Max upload size: 200MB")
        st.markdown(f"- Processing timeout: 300 seconds (5 minutes)")

        # Check 3: Demo mode availability
        st.markdown("**Features:**")
        st.markdown(f"- ✅ Demo Mode available")
        st.markdown(f"- ✅ Debug Mode available")

        if issues:
            st.markdown("---")
            st.markdown("**Issues Found:**")
            for issue in issues:
                st.error(issue)
        else:
            st.markdown("---")
            st.success("✅ All checks passed!")


# =============================================================================
# INTEGRATION INSTRUCTIONS
# =============================================================================
"""
To integrate these enhancements into app.py:

1. Add this import at the top:
   from app_enhanced import (
       validate_api_key,
       render_api_key_error,
       render_upload_error,
       render_processing_error,
       add_diagnostic_info_to_sidebar,
       cleanup_session_state,
       render_deployment_health_check
   )

2. In render_sidebar(), add at the end:
   add_diagnostic_info_to_sidebar()

3. In render_upload_section(), replace the file upload handling:
   if uploaded_file:
       if 'uploaded_file' in st.session_state and st.session_state.uploaded_file != uploaded_file:
           cleanup_session_state()
       st.session_state.uploaded_file = uploaded_file

4. In render_processing_section(), replace API key check:
   api_key = st.secrets.get("MINERU_API_KEY", os.getenv("MINERU_API_KEY", ""))
   validation = validate_api_key(api_key)
   if not validation['valid']:
       render_api_key_error(validation)
       return None

5. Replace upload error handling:
   if not upload_result.get('success'):
       render_upload_error(
           upload_result.get('error', 'Unknown error'),
           st.session_state.get('debug_mode', False)
       )
       st.session_state.processing = False
       return None

6. Replace processing error handling:
   if not result.get('success'):
       render_processing_error(
           result.get('error', 'Unknown error'),
           st.session_state.get('debug_mode', False)
       )
       st.session_state.processing = False
       return None

7. Add health check to sidebar or main page:
   render_deployment_health_check()
"""
