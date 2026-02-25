import os
import requests
import json
from dotenv import load_dotenv
from pprint import pprint
import zipfile
import io
import time

load_dotenv()
token = os.getenv("OCR_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
BASE_URL = "https://mineru.net/api/v4"

def test_ocr(file_path):
    print(f"1. Uploading {file_path} to tmpfiles.org...")
    with open(file_path, 'rb') as f:
        response = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': f})
    viewer_url = response.json()["data"]["url"]
    public_url = viewer_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"URL: {public_url}")

    print("2. Starting task...")
    task_resp = requests.post(f"{BASE_URL}/extract/task", headers=headers, json={"url": public_url, "is_ocr": True, "enable_table": True, "model_version": "vlm"})
    task_id = task_resp.json()["data"]["task_id"]

    for i in range(24): # Wait up to 2 mins for standard processing
        time.sleep(5)
        resp = requests.get(f"{BASE_URL}/extract/task/{task_id}", headers=headers).json()
        state = resp.get("data", {}).get("state")
        print(f"Status: {state}")
        if state == "done":
            zip_url = resp["data"]["full_zip_url"]
            zip_resp = requests.get(zip_url)
            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                for filename in z.namelist():
                    if filename.endswith(".md"):
                        md_content = z.read(filename).decode("utf-8")
                        with open("raw_output_new_format.md", "w") as out:
                            out.write(md_content)
                        print("✅ Success! Markdown saved to 'raw_output_new_format.md'")
                        # Print first few lines to get a sense of structure
                        print("\nSnippet:\n", md_content[:1500])
                        return
        elif state == "failed":
            print(f"Failed! {resp}")
            return

test_ocr("/Users/alexchong/Desktop/AI  projects/6SPC/Scan PDF/AJ26010702驱动棘轮AJR26010702原材料进货检验记录9-60.pdf")
