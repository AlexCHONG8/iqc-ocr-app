#!/usr/bin/env python3
"""
Real API test - download from actual MinerU CDN
This will help us debug the actual issue.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app import MinerUClient


def test_real_task_status():
    """Test getting task status from real API."""
    # Use the actual API key
    API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2OTczNDQ2MCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI2NTQ2MzhjMS1mNmJmLTQ0YzItYmNmMS1hY2QzNjg1OWI0MzQiLCJlbWFpbCI6IiIsImV4cCI6MTc3MDk0NDA2MH0.PZ4-GsVnjRm7p2J_UURXWh_8kgoB0JxJ8SQzuh7n3E2shXdpqp2NV_oxfL6tj3nk-uzgy4bmAgw9ExRFnRmDgg"

    client = MinerUClient(api_key=API_KEY)

    # List recent tasks to find a completed one
    import requests
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

    print("Fetching recent tasks...")
    resp = requests.get("https://mineru.net/api/v4/tasks", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get('code') != 0:
        print(f"API Error: {data.get('msg')}")
        return

    tasks = data.get('data', {}).get('list', [])
    print(f"\nFound {len(tasks)} task(s)")

    # Find first completed task with markdown
    for task in tasks:
        if task.get('state') == 'done':
            task_id = task.get('task_id')
            md_url = task.get('full_md_link')

            print(f"\n✓ Found completed task:")
            print(f"  Task ID: {task_id}")
            print(f"  File: {task.get('file_name')}")
            print(f"  MD URL: {md_url}")

            if md_url:
                print(f"\n🔍 Testing download from:")
                print(f"  {md_url}")

                # Test the actual download
                markdown = client.download_markdown(md_url)

                if markdown:
                    print(f"\n✅ Download SUCCESS!")
                    print(f"  Length: {len(markdown)} characters")
                    print(f"  Preview (first 200 chars):")
                    print(f"  {markdown[:200]}")
                else:
                    print(f"\n❌ Download FAILED - returned empty string")
                    print(f"  This is the bug we need to fix!")
            return

    print("\nNo completed tasks found with markdown")


if __name__ == "__main__":
    test_real_task_status()
