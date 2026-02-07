#!/usr/bin/env python3
"""
MinerU Cloud API Client - Lightweight PDF to Markdown converter
Uses MinerU.net cloud API - no local installation required.
"""

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests")
    import requests


# MinerU Cloud API Configuration
# Based on OpenDataLab/MinerU cloud service
API_BASE_URL = "https://mineru.net/api/v1"
# Alternative endpoints to try:
# - https://mineru.net/api/v1
# - https://api.opendatalab.com/mineru/v1
# - https://openxlab.org.cn/api/mineru/v1

API_ENDPOINTS = [
    "https://mineru.net/api/v1",
    "https://api.mineru.net/v1",
    "https://mineru.net/api/v4",
    "https://api.opendatalab.com/mineru/v1",
]

# Your API key
API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2OTczNDQ2MCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI2NTQ2MzhjMS1mNmJmLTQ0YzItYmNmMS1hY2QzNjg1OWI0MzQiLCJlbWFpbCI6IiIsImV4cCI6MTc3MDk0NDA2MH0.PZ4-GsVnjRm7p2J_UURXWh_8kgoB0JxJ8SQzuh7n3E2shXdpqp2NV_oxfL6tj3nk-uzgy4bmAgw9ExRFnRmDgg"


class MinerUCloudClient:
    """Client for MinerU Cloud API."""

    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "MinerU-Cloud-Client/1.0"
        })
        self.api_base = None

    def _discover_endpoint(self) -> str:
        """Find the working API endpoint."""
        for endpoint in API_ENDPOINTS:
            try:
                # Try a simple health check or options request
                resp = self.session.options(endpoint, timeout=5)
                if resp.status_code in [200, 401, 405]:  # Endpoint exists
                    print(f"✓ Found API endpoint: {endpoint}")
                    return endpoint
            except:
                continue

        print("⚠ Could not auto-detect endpoint, using default")
        return API_BASE_URL

    def upload_pdf(self, pdf_path: str) -> dict:
        """
        Upload a PDF file for processing.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with task_id and status
        """
        if not self.api_base:
            self.api_base = self._discover_endpoint()

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"Uploading: {pdf_file.name} ({pdf_file.stat().st_size / 1024 / 1024:.1f} MB)")

        # Try different upload endpoints
        upload_endpoints = [
            f"{self.api_base}/upload",
            f"{self.api_base}/applications",
            f"{self.api_base}/files/upload",
            "/api/v4/application/fileUpload",  # From mineru.net source
        ]

        for upload_url in upload_endpoints:
            try:
                # Prepare file for upload
                with open(pdf_file, "rb") as f:
                    files = {
                        "file": (pdf_file.name, f, "application/pdf")
                    }

                    # Try with full URL first
                    url = upload_url if upload_url.startswith("http") else f"https://mineru.net{upload_url}"

                    resp = self.session.post(url, files=files, timeout=60)

                    if resp.status_code == 200:
                        result = resp.json()
                        print(f"✓ Upload successful!")

                        # Handle different response formats
                        if "data" in result:
                            return result["data"]
                        elif "task_id" in result:
                            return result
                        elif "id" in result:
                            return {"task_id": result["id"], "file_id": result["id"]}
                        else:
                            return result

            except Exception as e:
                print(f"  Tried {upload_url}: {e}")
                continue

        raise Exception(f"Upload failed. Last response: {resp.text if 'resp' in locals() else 'No response'}")

    def get_status(self, task_id: str) -> dict:
        """
        Check conversion status.

        Args:
            task_id: Task ID from upload

        Returns:
            Dict with status and results
        """
        if not self.api_base:
            self.api_base = self._discover_endpoint()

        status_endpoints = [
            f"{self.api_base}/status/{task_id}",
            f"{self.api_base}/tasks/{task_id}",
            f"{self.api_base}/applications/{task_id}",
            f"/api/v4/application/taskDetail?task_id={task_id}",
        ]

        for status_url in status_endpoints:
            try:
                url = status_url if status_url.startswith("http") else f"https://mineru.net{status_url}"
                resp = self.session.get(url, timeout=30)

                if resp.status_code == 200:
                    return resp.json()
            except:
                continue

        return {"status": "unknown", "error": "Could not fetch status"}

    def download_result(self, task_id: str, output_path: str = None) -> str:
        """
        Download converted markdown.

        Args:
            task_id: Task ID
            output_path: Where to save the markdown file

        Returns:
            Path to downloaded file
        """
        if not self.api_base:
            self.api_base = self._discover_endpoint()

        # First get the result to find download URL
        status = self.get_status(task_id)

        # Look for download URL in response
        download_url = None
        if "data" in status:
            data = status["data"]
            download_url = data.get("download_url") or data.get("url") or data.get("result_url")
        elif "download_url" in status:
            download_url = status["download_url"]
        elif "url" in status:
            download_url = status["url"]

        if not download_url:
            # Try direct download endpoints
            download_endpoints = [
                f"{self.api_base}/download/{task_id}",
                f"{self.api_base}/result/{task_id}",
            ]

            for dl_url in download_endpoints:
                try:
                    url = dl_url if dl_url.startswith("http") else f"https://mineru.net{dl_url}"
                    resp = self.session.get(url, timeout=60)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        markdown_content = resp.text

                        if output_path is None:
                            output_path = f"{task_id}.md"

                        Path(output_path).write_text(markdown_content, encoding="utf-8")
                        print(f"✓ Downloaded to: {output_path}")
                        return output_path
                except:
                    continue
        else:
            # Download from the URL we found
            resp = self.session.get(download_url, timeout=60)
            if resp.status_code == 200:
                markdown_content = resp.text

                if output_path is None:
                    output_path = f"{task_id}.md"

                Path(output_path).write_text(markdown_content, encoding="utf-8")
                print(f"✓ Downloaded to: {output_path}")
                return output_path

        raise Exception("Could not download result")

    def convert(self, pdf_path: str, output_path: str = None, wait: bool = True) -> str:
        """
        Full conversion workflow: upload -> wait -> download.

        Args:
            pdf_path: Path to input PDF
            output_path: Path for output markdown (optional)
            wait: Wait for conversion to complete

        Returns:
            Path to converted markdown file
        """
        # Upload
        upload_result = self.upload_pdf(pdf_path)
        task_id = upload_result.get("task_id") or upload_result.get("id")

        if not task_id:
            raise Exception(f"No task_id in response: {upload_result}")

        print(f"Task ID: {task_id}")

        if wait:
            # Poll for completion
            import time
            print("Processing...")

            max_attempts = 120  # 10 minutes max
            for i in range(max_attempts):
                time.sleep(5)

                status = self.get_status(task_id)
                current_status = status.get("data", {}).get("status") if "data" in status else status.get("status")

                if current_status in ["completed", "success", "finished", "done"]:
                    print("✓ Conversion complete!")
                    break
                elif current_status in ["failed", "error"]:
                    raise Exception(f"Conversion failed: {status}")

                if i % 6 == 0:  # Every 30 seconds
                    print(f"  Status: {current_status or 'processing...'}")
            else:
                print("⚠ Timeout, attempting download anyway...")

        # Download result
        return self.download_result(task_id, output_path)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MinerU Cloud PDF to Markdown")
    parser.add_argument("pdf", help="Input PDF file")
    parser.add_argument("-o", "--output", help="Output markdown file")
    parser.add_argument("-k", "--api-key", help="API key (default: built-in)", default=API_KEY)
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for conversion")

    args = parser.parse_args()

    client = MinerUCloudClient(api_key=args.api_key)

    try:
        output = client.convert(args.pdf, args.output, wait=not args.no_wait)
        print(f"\n✅ Success! Output: {output}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
