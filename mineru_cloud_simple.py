#!/usr/bin/env python3
"""
MinerU Cloud Client - Simple version
Works with MinerU.net API to list tasks and download converted markdown.
"""

import requests
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

# Your API key (valid until Feb 13, 2026)
API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2OTczNDQ2MCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI2NTQ2MzhjMS1mNmJmLTQ0YzItYmNmMS1hY2QzNjg1OWI0MzQiLCJlbWFpbCI6IiIsImV4cCI6MTc3MDk0NDA2MH0.PZ4-GsVnjRm7p2J_UURXWh_8kgoB0JxJ8SQzuh7n3E2shXdpqp2NV_oxfL6tj3nk-uzgy4bmAgw9ExRFnRmDgg"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}


def list_tasks():
    """List all your conversion tasks."""
    resp = requests.get("https://mineru.net/api/v4/tasks", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get('code') != 0:
        raise Exception(f"API error: {data.get('msg')}")

    tasks = data.get('data', {}).get('list', [])
    return tasks


def download_markdown(md_url, output_path):
    """Download markdown from CDN URL."""
    resp = requests.get(md_url, timeout=30)
    resp.raise_for_status()

    # Detect and use proper encoding from response
    # CDN may not set encoding correctly, so force UTF-8
    resp.encoding = 'utf-8'
    content = resp.text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with UTF-8 encoding and ensure newline consistency
    output_path.write_text(content, encoding='utf-8', newline='\n')

    print(f"  Downloaded {len(content)} characters, {len(content.encode('utf-8'))} bytes")
    return output_path


def print_tasks():
    """Print all tasks in a nice format."""
    tasks = list_tasks()

    if not tasks:
        print("No tasks found.")
        return

    print(f"\n{'='*60}")
    print(f"  Found {len(tasks)} task(s)")
    print(f"{'='*60}\n")

    for i, task in enumerate(tasks, 1):
        state = task.get('state', 'unknown')
        state_icon = "✅" if state == "done" else "⏳" if state == "processing" else "❌"

        print(f"{state_icon} [{i}] {task.get('file_name', 'unknown')}")
        print(f"   Task ID: {task.get('task_id', 'N/A')}")
        print(f"   Status: {state}")
        print(f"   Created: {task.get('created_at', 'N/A')}")
        print(f"   Model: {task.get('model_version', 'N/A')}")

        if task.get('full_md_link'):
            print(f"   Markdown: Available")
        if task.get('err_msg'):
            print(f"   Error: {task.get('err_msg')}")
        print()


def download_task(task_index):
    """Download markdown from a specific task."""
    tasks = list_tasks()

    if task_index < 1 or task_index > len(tasks):
        print(f"Error: Task index must be between 1 and {len(tasks)}")
        return None

    task = tasks[task_index - 1]

    if task.get('state') != 'done':
        print(f"Error: Task is not complete yet (status: {task.get('state')})")
        return None

    md_url = task.get('full_md_link')
    if not md_url:
        print("Error: No markdown link available")
        return None

    filename = Path(task.get('file_name', 'output')).stem + '.md'

    print(f"Downloading: {filename}")
    output = download_markdown(md_url, filename)
    print(f"✅ Saved to: {output}")
    return output


def main():
    if len(sys.argv) < 2:
        print("MinerU Cloud Client")
        print("\nUsage:")
        print("  python mineru_cloud_simple.py list          # List all tasks")
        print("  python mineru_cloud_simple.py download <n>  # Download markdown from task n")
        print("\nExamples:")
        print("  python mineru_cloud_simple.py list")
        print("  python mineru_cloud_simple.py download 1")
        return

    command = sys.argv[1].lower()

    if command == "list":
        print_tasks()
    elif command == "download":
        if len(sys.argv) < 3:
            print("Error: Please specify task number")
            print("Usage: python mineru_cloud_simple.py download <task_number>")
            return
        task_index = int(sys.argv[2])
        download_task(task_index)
    else:
        print(f"Error: Unknown command '{command}'")
        print("Available commands: list, download")


if __name__ == "__main__":
    main()
