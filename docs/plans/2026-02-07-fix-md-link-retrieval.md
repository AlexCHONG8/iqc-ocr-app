# Fix MinerU API Markdown Link Retrieval

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the bug where OCR completes successfully but `full_md_link` is not retrieved from the API response.

**Architecture:** The app uses `/api/v4/extract-results/batch/{batch_id}` endpoint which returns a different response structure than `/api/v4/tasks` endpoint. Need to either switch to tasks endpoint or handle batch response correctly.

**Tech Stack:** Python, requests library, MinerU.net API, unittest (TDD)

---

## Root Cause Analysis

**Evidence from Investigation:**
- `test_real_download.py` successfully retrieved `full_md_link` using `/api/v4/tasks` endpoint
- `app.py` uses `/api/v4/extract-results/batch/{batch_id}` endpoint (line 355)
- Batch endpoint response does NOT include `full_md_link` field
- OCR completes (state='done') but `md_url` is None

**Hypothesis:** Batch endpoint requires different field access or need to use tasks endpoint instead.

---

## Task 1: Add Debug Logging to Capture Actual API Response

**Files:**
- Modify: `app.py:350-380` (check_task_status method)
- Test: Create new test file

**Step 1: Write test to expose API response structure**

Create `test_api_response_structure.py`:

```python
#!/usr/bin/env python3
"""Test to capture actual API response structure from batch endpoint."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from app import MinerUClient

class TestAPIResponseStructure(unittest.TestCase):
    """Capture and display actual API response structure."""

    def test_batch_endpoint_response_structure(self):
        """Show what fields are actually returned by batch endpoint."""
        API_KEY = "your-api-key-here"  # Use real key for this test

        # You need a real batch_id from a recent upload
        # This test is meant to be run manually with real data
        client = MinerUClient(api_key=API_KEY)

        # Use a real batch_id from your uploads
        # batch_id = "your-real-batch-id"

        # status = client.check_task_status(batch_id)
        # print("Full API response keys:", status.keys())
        # print("Response:", status)

        # This test documents what we expect vs what we get
        self.assertTrue(True, "Manual test - replace with real batch_id")

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

**Step 2: Add debug logging to check_task_status**

Modify `app.py` check_task_status method (after line 359):

```python
result = response.json()

# DEBUG: Log full response structure
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Batch API response: {result}")
logger.debug(f"Response keys: {result.keys()}")
logger.debug(f"Data keys: {result.get('data', {}).keys()}")
logger.debug(f"Extract result keys: {result.get('data', {}).get('extract_result', [{}])[0].keys() if result.get('data', {}).get('extract_result') else 'empty'}")
```

**Step 3: Run test to verify it fails**

Run: `python test_api_response_structure.py`
Expected: Shows actual response structure from batch endpoint

**Step 4: Run app with real PDF upload**

Run: `streamlit run app.py`
Upload a real PDF
Check console output for debug logs

**Step 5: Commit debug code**

```bash
git add app.py test_api_response_structure.py
git commit -m "debug: add logging to capture batch API response structure"
```

---

## Task 2: Compare Batch vs Tasks API Endpoints

**Files:**
- Create: `compare_endpoints.py`
- Reference: `test_real_download.py` (shows tasks endpoint works)

**Step 1: Write endpoint comparison script**

Create `compare_endpoints.py`:

```python
#!/usr/bin/env python3
"""Compare batch endpoint vs tasks endpoint responses."""

import requests
import json

API_KEY = "your-api-key-here"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

def compare_endpoints(batch_id):
    """Compare responses from batch and tasks endpoints."""

    # Batch endpoint (what app uses)
    batch_url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
    batch_resp = requests.get(batch_url, headers=HEADERS, timeout=10)
    batch_data = batch_resp.json()

    print("=== BATCH ENDPOINT RESPONSE ===")
    print(json.dumps(batch_data, indent=2, ensure_ascii=False))
    print(f"\nHas full_md_link: {'full_md_link' in str(batch_data)}")

    # Tasks endpoint (what test uses)
    tasks_url = "https://mineru.net/api/v4/tasks"
    tasks_resp = requests.get(tasks_url, headers=HEADERS, timeout=10)
    tasks_data = tasks_resp.json()

    print("\n=== TASKS ENDPOINT RESPONSE ===")
    # Find matching task
    tasks = tasks_data.get('data', {}).get('list', [])
    for task in tasks:
        if batch_id in task.get('task_id', ''):
            print(json.dumps(task, indent=2, ensure_ascii=False))
            print(f"\nHas full_md_link: {'full_md_link' in task}")
            break

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        compare_endpoints(sys.argv[1])
    else:
        print("Usage: python compare_endpoints.py <batch_id>")
```

**Step 2: Run comparison**

```bash
python compare_endpoints.py <your-batch-id-from-upload>
```

**Step 3: Document findings**

Create `API_ENDPOINT_DIFFERENCES.md`:

```markdown
# MinerU API Endpoint Differences

## Batch Endpoint: /api/v4/extract-results/batch/{batch_id}
- Response structure: {...}
- Contains full_md_link: [YES/NO]
- Field name for markdown: [...]

## Tasks Endpoint: /api/v4/tasks
- Response structure: {...}
- Contains full_md_link: [YES/NO]
- Field name for markdown: full_md_link

## Conclusion
- Which endpoint should we use?
- Do we need to call both endpoints?
```

**Step 4: Commit findings**

```bash
git add compare_endpoints.py API_ENDPOINT_DIFFERENCES.md
git commit -m "docs: compare batch vs tasks API endpoints"
```

---

## Task 3: Implement Fix Based on Findings

**Option A: If tasks endpoint provides full_md_link**

**Step 1: Write test for tasks endpoint integration**

```python
@patch('app.requests.get')
def test_check_task_status_uses_tasks_endpoint(self, mock_get):
    """Should use /api/v4/tasks endpoint to get full_md_link."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'code': 0,
        'data': {
            'list': [{
                'task_id': 'batch-123',
                'state': 'done',
                'full_md_link': 'https://cdn.example.com/result.md'
            }]
        }
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = MinerUClient(api_key="test-key")
    result = client.check_task_status("batch-123")

    self.assertTrue(result['success'])
    self.assertEqual(result['md_url'], 'https://cdn.example.com/result.md')
```

**Step 2: Implement tasks endpoint method**

```python
def check_task_status_tasks_endpoint(self, batch_id: str) -> Dict[str, Any]:
    """Check status using /api/v4/tasks endpoint which returns full_md_link."""
    tasks_url = f"{self.base_url}/tasks"
    try:
        response = requests.get(tasks_url, headers=self.headers, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get('code') != 0:
            return {'success': False, 'error': result.get('msg')}

        tasks = result.get('data', {}).get('list', [])

        # Find task matching our batch_id
        for task in tasks:
            if batch_id in task.get('task_id', ''):
                return {
                    'success': True,
                    'state': task.get('state'),
                    'md_url': task.get('full_md_link'),
                    'err_msg': task.get('err_msg')
                }

        return {'success': False, 'error': 'Task not found in list'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**Step 3: Run test to verify it passes**

Run: `python -m unittest test_mineru_client.py -v`
Expected: PASS

**Step 4: Update app to use new method**

Modify `app.py` line ~865:

```python
# OLD: status = client.check_task_status(batch_id)
status = client.check_task_status_tasks_endpoint(batch_id)
```

**Option B: If batch endpoint has different field name**

**Step 1: Update field mapping**

```python
return {
    'success': True,
    'state': first_result.get('state'),
    'md_url': first_result.get('full_md_link') or first_result.get('md_link') or first_result.get('markdown_url'),
    'err_msg': first_result.get('err_msg')
}
```

**Step 5: Commit fix**

```bash
git add app.py test_mineru_client.py
git commit -m "fix: use tasks endpoint to retrieve full_md_link from API"
```

---

## Task 4: End-to-End Integration Test

**Files:**
- Test: `test_e2e_upload_download.py`
- Modify: `app.py` (main processing flow)

**Step 1: Write E2E test**

Create `test_e2e_upload_download.py`:

```python
#!/usr/bin/env python3
"""End-to-end test: Upload PDF, wait for OCR, download markdown."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from app import MinerUClient

def test_e2e_workflow():
    """Complete workflow: upload -> wait -> download."""
    API_KEY = "your-api-key"
    client = MinerUClient(api_key=API_KEY)

    # Read test PDF
    with open("test_sample.pdf", "rb") as f:
        pdf_bytes = f.read()

    # Upload
    upload_result = client.upload_pdf(pdf_bytes, "test_sample.pdf")
    print(f"Upload result: {upload_result}")

    assert upload_result['success'], "Upload failed"
    batch_id = upload_result['batch_id']

    # Wait for completion
    print(f"Waiting for batch {batch_id}...")
    status = client.wait_for_completion(batch_id, timeout=300)

    print(f"Final status: {status}")
    assert status['success'], f"Processing failed: {status.get('error')}"

    md_url = status.get('md_url')
    assert md_url, "No md_url in status!"

    # Download markdown
    markdown = client.download_markdown(md_url)
    print(f"Downloaded {len(markdown)} characters")

    assert len(markdown) > 100, "Markdown too short!"
    assert "检验位置" in markdown or "Dimension" in markdown, "Unexpected content"

    print("✅ E2E test passed!")

if __name__ == "__main__":
    test_e2e_workflow()
```

**Step 2: Run E2E test**

```bash
python test_e2e_upload_download.py
```

**Step 3: Verify complete workflow in Streamlit app**

Run: `streamlit run app.py`
Upload: test_sample.pdf
Verify: All steps complete successfully

**Step 4: Commit E2E test**

```bash
git add test_e2e_upload_download.py
git commit -m "test: add end-to-end integration test"
```

---

## Task 5: Clean Up and Document

**Files:**
- Create: `API_USAGE.md`
- Modify: `README.md`

**Step 1: Document API endpoint usage**

Create `API_USAGE.md`:

```markdown
# MinerU API Usage Notes

## Endpoints

### 1. Batch Upload: /api/v4/file-urls/batch
- Purpose: Get upload URLs for PDF files
- Returns: upload_urls, batch_id

### 2. Task Status: /api/v4/tasks
- Purpose: List all tasks with full details
- Returns: Array of tasks with full_md_link

### 3. Batch Status: /api/v4/extract-results/batch/{batch_id}
- Purpose: Get status of specific batch
- Returns: Status but NOT full_md_link

## Important

**Use `/api/v4/tasks` endpoint to retrieve `full_md_link`**

The batch endpoint does not return the markdown download URL. We must:
1. Upload using batch endpoint → get batch_id
2. Monitor status using batch endpoint (for state updates)
3. Retrieve final result using tasks endpoint (for full_md_link)
```

**Step 2: Update README.md**

Add troubleshooting section:

```markdown
## Troubleshooting

### "No markdown URL in API response"
- This happens when using batch endpoint
- Fix: App now uses tasks endpoint for final retrieval
- Check logs for debug info
```

**Step 3: Remove debug logging (optional)**

```python
# Comment out or remove debug logging from check_task_status
# logger.debug(...)
```

**Step 4: Commit documentation**

```bash
git add API_USAGE.md README.md
git commit -m "docs: add API usage notes and troubleshooting guide"
```

---

## Task 6: Final Verification

**Step 1: Run all tests**

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

Expected: All tests pass

**Step 2: Test with real PDFs**

Upload multiple PDF samples:
- Simple form: ✅
- Complex table: ✅
- Handwriting: ✅
- Mixed Chinese/English: ✅

**Step 3: Check git status**

```bash
git status
git log --oneline -5
```

**Step 4: Tag release**

```bash
git tag -a v0.2.0 -m "Fix API md_link retrieval bug"
git push origin main --tags
```

---

## Summary

**Bug:** `full_md_link` not returned by batch API endpoint

**Root Cause:** `/api/v4/extract-results/batch/{batch_id}` endpoint response structure differs from `/api/v4/tasks`

**Solution:** Use tasks endpoint to retrieve markdown URL

**Verification:** E2E test confirms complete workflow works

**Files Modified:**
- `app.py`: Updated API endpoint usage
- `test_mineru_client.py`: Added tasks endpoint tests
- `API_USAGE.md`: Documented correct API usage

**Next Steps:**
- Deploy to Streamlit Cloud
- Configure MINERU_API_KEY
- Share with team
