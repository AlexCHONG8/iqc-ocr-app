#!/usr/bin/env python3
"""Check all tasks including pagination."""

import requests
import json

API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2OTczNDQ2MCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI2NTQ2MzhjMS1mNmJmLTQ0YzItYmNmMS1hY2QzNjg1OWI0MzQiLCJlbWFpbCI6IiIsImV4cCI6MTc3MDk0NDA2MH0.PZ4-GsVnjRm7p2J_UURXWh_8kgoB0JxJ8SQzuh7n3E2shXdpqp2NV_oxfL6tj3nk-uzgy4bmAgw9ExRFnRmDgg"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

def check_all_pages():
    """Check multiple pages of tasks."""
    url = "https://mineru.net/api/v4/tasks"

    # Try with page and limit parameters
    for page in range(1, 3):
        print(f"\n{'='*60}")
        print(f"Page {page}")
        print('='*60)

        params = {
            'page': page,
            'per_page': 50,
            'order_by': 'created_at',
            'order': 'desc'  # newest first
        }

        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') == 0:
                tasks = data.get('data', {}).get('list', [])
                print(f"Found {len(tasks)} tasks")

                for i, task in enumerate(tasks[:5], 1):
                    task_id = task.get('task_id', 'N/A')[:30]
                    created = task.get('created_at', 'N/A')
                    state = task.get('state', 'N/A')
                    filename = task.get('file_name', 'N/A')[:30]
                    has_md = '✅' if task.get('full_md_link') else '❌'

                    print(f"{i}. {filename}")
                    print(f"   ID: {task_id}")
                    print(f"   Created: {created} | State: {state} | MD: {has_md}")

                # Check for our batch_id
                batch_id = "78849f07-545c-4803-9e59-2d796647e4c4"
                for task in tasks:
                    if batch_id in task.get('task_id', '') or '78849f07' in task.get('task_id', ''):
                        print(f"\n🎯 FOUND MATCHING TASK:")
                        print(json.dumps(task, indent=2, ensure_ascii=False))
                        return task
        except Exception as e:
            print(f"Error: {e}")

    print("\n❌ Batch ID not found in any page")

if __name__ == "__main__":
    check_all_pages()
