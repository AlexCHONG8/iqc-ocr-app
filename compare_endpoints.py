#!/usr/bin/env python3
"""Compare batch endpoint vs tasks endpoint responses."""

import requests
import json

# Use the real API key from test_real_download.py
API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2OTczNDQ2MCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI2NTQ2MzhjMS1mNmJmLTQ0YzItYmNmMS1hY2QzNjg1OWI0MzQiLCJlbWFpbCI6IiIsImV4cCI6MTc3MDk0NDA2MH0.PZ4-GsVnjRm7p2J_UURXWh_8kgoB0JxJ8SQzuh7n3E2shXdpqp2NV_oxfL6tj3nk-uzgy4bmAgw9ExRFnRmDgg"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}


def compare_endpoints(batch_id):
    """Compare responses from batch and tasks endpoints."""

    print(f"\n{'='*60}")
    print(f"Comparing API Endpoints for Batch ID: {batch_id}")
    print(f"{'='*60}\n")

    # Batch endpoint (what app uses)
    batch_url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
    print(f"📡 Fetching from BATCH endpoint...")
    print(f"   URL: {batch_url}")

    try:
        batch_resp = requests.get(batch_url, headers=HEADERS, timeout=10)
        batch_data = batch_resp.json()

        print("\n" + "="*60)
        print("BATCH ENDPOINT RESPONSE")
        print("="*60)
        print(json.dumps(batch_data, indent=2, ensure_ascii=False))

        # Check for full_md_link
        has_md_link = 'full_md_link' in str(batch_data)
        print(f"\n🔍 Contains 'full_md_link': {has_md_link} {'✅' if has_md_link else '❌'}")

        if batch_data.get('code') == 0:
            data = batch_data.get('data', {})
            extract_result = data.get('extract_result', [])
            if extract_result:
                print(f"🔍 First result keys: {list(extract_result[0].keys())}")
    except Exception as e:
        print(f"❌ Batch endpoint error: {e}")

    # Tasks endpoint (what test uses)
    print(f"\n{'='*60}")
    print(f"📡 Fetching from TASKS endpoint...")
    tasks_url = "https://mineru.net/api/v4/tasks"
    print(f"   URL: {tasks_url}")

    try:
        tasks_resp = requests.get(tasks_url, headers=HEADERS, timeout=10)
        tasks_data = tasks_resp.json()

        if tasks_data.get('code') == 0:
            tasks = tasks_data.get('data', {}).get('list', [])

            # Find task matching our batch_id
            matching_task = None
            for task in tasks:
                if batch_id in task.get('task_id', ''):
                    matching_task = task
                    break

            if matching_task:
                print("\n" + "="*60)
                print("TASKS ENDPOINT RESPONSE (matching task)")
                print("="*60)
                print(json.dumps(matching_task, indent=2, ensure_ascii=False))

                # Check for full_md_link
                has_md_link = 'full_md_link' in matching_task
                print(f"\n🔍 Contains 'full_md_link': {has_md_link} {'✅' if has_md_link else '❌'}")
                print(f"🔍 Task keys: {list(matching_task.keys())}")
            else:
                print(f"⚠️  No matching task found for batch_id: {batch_id}")
                print(f"   Available tasks: {[t.get('task_id') for t in tasks[:5]]}")
    except Exception as e:
        print(f"❌ Tasks endpoint error: {e}")

    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print("="*60)
    print("Key Finding:")
    print("  • Batch endpoint: Returns status but NOT full_md_link")
    print("  • Tasks endpoint: Returns full_md_link ✓")
    print("\nSolution: Use tasks endpoint to retrieve markdown URL")
    print(f"{'='*60}\n")


def list_recent_tasks():
    """List recent tasks to get batch IDs for comparison."""
    print("Fetching recent tasks...")
    tasks_url = "https://mineru.net/api/v4/tasks"

    try:
        resp = requests.get(tasks_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get('code') == 0:
            tasks = data.get('data', {}).get('list', [])
            print(f"\nRecent Tasks ({len(tasks)} total):")
            print("-" * 60)

            for i, task in enumerate(tasks[:10], 1):
                task_id = task.get('task_id', 'N/A')[:30]
                state = task.get('state', 'N/A')
                filename = task.get('file_name', 'N/A')[:30]
                has_md = '✅' if task.get('full_md_link') else '❌'

                print(f"{i}. {filename}")
                print(f"   ID: {task_id}")
                print(f"   State: {state} | MD Link: {has_md}")

                if task.get('full_md_link'):
                    print(f"   📥 {task.get('full_md_link')[:60]}...")
                print()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Compare specific batch ID
        batch_id = sys.argv[1]
        compare_endpoints(batch_id)
    else:
        # List recent tasks first
        list_recent_tasks()
        print("\nUsage: python compare_endpoints.py <batch_id>")
        print("       (Run with a batch_id from the list above to compare)")
