#!/usr/bin/env python3
"""
Diagnostic Tool for MinerU API Integration
Run this to verify API key and test connectivity before deployment.
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_key(api_key: str) -> dict:
    """Test if API key is valid by making a simple API call."""
    print("\n" + "="*60)
    print("🔑 Testing API Key...")
    print("="*60)

    if not api_key:
        return {
            'valid': False,
            'error': 'API key is empty or not set'
        }

    # Check key format (support both JWT and API key formats)
    # JWT tokens start with "ey", API keys might start with "sk-"
    if not (api_key.startswith('ey') or api_key.startswith('sk-')):
        return {
            'valid': False,
            'error': f'Invalid API key format (should start with "ey" or "sk-", got: {api_key[:10]}...)'
        }

    if api_key.startswith('ey'):
        print(f"✓ API key format looks correct (JWT token)")
    else:
        print(f"✓ API key format looks correct (API key)")
    print(f"  Key length: {len(api_key)} characters")
    print(f"  Key prefix: {api_key[:20]}...")

    # Test API connectivity
    base_url = "https://mineru.net/api/v4"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Diagnostic Tool)"
    }

    try:
        # Test 1: Check if we can reach the API
        print("\n📡 Testing API connectivity...")

        # Try to list recent tasks (this should always work with valid key)
        response = requests.get(
            f"{base_url}/tasks",
            headers=headers,
            timeout=10
        )

        print(f"  Response status: {response.status_code}")

        if response.status_code == 401:
            return {
                'valid': False,
                'error': 'Authentication failed - API key is invalid or expired'
            }

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                print(f"✓ API connection successful!")
                tasks = result.get('data', {}).get('list', [])
                print(f"  Found {len(tasks)} recent tasks in account")
                return {
                    'valid': True,
                    'message': 'API key is valid and working',
                    'recent_tasks': len(tasks)
                }
            else:
                return {
                    'valid': False,
                    'error': f'API returned error code: {result.get("msg", "Unknown error")}'
                }

        return {
            'valid': False,
            'error': f'Unexpected response status: {response.status_code}'
        }

    except requests.exceptions.Timeout:
        return {
            'valid': False,
            'error': 'Request timed out - check network connection'
        }
    except requests.exceptions.ConnectionError:
        return {
            'valid': False,
            'error': 'Cannot connect to MinerU.net - check network connection'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'Unexpected error: {str(e)}'
        }

def check_deployment_config() -> dict:
    """Check deployment configuration files."""
    print("\n" + "="*60)
    print("📁 Checking Deployment Configuration...")
    print("="*60)

    issues = []

    # Check requirements.txt
    req_file = Path("requirements.txt")
    if req_file.exists():
        print(f"✓ requirements.txt exists")
        with open(req_file) as f:
            reqs = f.read()
            if 'streamlit' in reqs:
                print(f"  ✓ streamlit dependency found")
            if 'requests' in reqs:
                print(f"  ✓ requests dependency found")
    else:
        issues.append("requirements.txt not found")

    # Check .streamlit/config.toml
    config_file = Path(".streamlit/config.toml")
    if config_file.exists():
        print(f"✓ .streamlit/config.toml exists")
        with open(config_file) as f:
            config = f.read()
            if 'maxUploadSize' in config:
                print(f"  ✓ Upload size configured")
    else:
        issues.append(".streamlit/config.toml not found")

    # Check app.py
    app_file = Path("app.py")
    if app_file.exists():
        print(f"✓ app.py exists")
        with open(app_file) as f:
            content = f.read()
            if 'MinerUClient' in content:
                print(f"  ✓ MinerUClient class found")
            if 'st.secrets' in content:
                print(f"  ✓ Streamlit secrets integration found")
    else:
        issues.append("app.py not found")

    return {
        'valid': len(issues) == 0,
        'issues': issues
    }

def main():
    """Run all diagnostic checks."""
    print("\n" + "="*60)
    print("🔍 MinerU API Diagnostic Tool")
    print("="*60)
    print("This tool checks your MinerU API integration before deployment")

    # Get API key from environment
    api_key = os.getenv("MINERU_API_KEY", "")

    # Check API key
    api_test = test_api_key(api_key)

    if not api_test['valid']:
        print("\n" + "="*60)
        print("❌ API KEY VALIDATION FAILED")
        print("="*60)
        print(f"Error: {api_test['error']}")
        print("\n📝 How to fix:")
        print("1. Get API key from: https://mineru.net")
        print("2. Set MINERU_API_KEY in .env file:")
        print("   MINERU_API_KEY=your_full_api_key_here")
        print("3. Or set it in Streamlit Cloud secrets")
        print("\n")
        return False

    # Check deployment config
    config_test = check_deployment_config()

    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*60)

    all_passed = True

    # API Key Status
    if api_test['valid']:
        print(f"✅ API Key: VALID")
        if 'recent_tasks' in api_test:
            print(f"   Account has {api_test['recent_tasks']} recent tasks")
    else:
        print(f"❌ API Key: INVALID")
        all_passed = False

    # Config Status
    if config_test['valid']:
        print(f"✅ Configuration: VALID")
    else:
        print(f"❌ Configuration: ISSUES FOUND")
        for issue in config_test['issues']:
            print(f"   - {issue}")
        all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print("="*60)
        print("\n🚀 Next steps:")
        print("1. Push code to GitHub")
        print("2. Deploy to Streamlit Cloud")
        print("3. Set MINERU_API_KEY in Streamlit Cloud secrets")
        print("4. Restart the app and test")
    else:
        print("❌ ISSUES FOUND - Please fix before deploying")
        print("="*60)

    print("\n")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
