import requests
import json
import time
import os

token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3MTkyODYwMCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiIwNjNmYzQyOC1lYzZmLTQ0MGEtODYxMy1jNTJlN2UxZDBmZGYiLCJlbWFpbCI6IiIsImV4cCI6MTc3OTcwNDYwMH0.9muRctChWY3tUdE6ctYrDgAdYzi0FUJFQwHehHj_2ThNBAHtTVtFm7TbsJMUK8gU022lCbEWfkNWBg-gyp-s2g"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("1. Get Upload Link")
resp1 = requests.post("https://mineru.net/api/v4/file-urls/batch", headers=headers, json={"files": [{"name": "sample_scan.pdf"}]})
data1 = resp1.json()
print("Response 1:", data1)

if data1.get("code") != 0:
    print("Failed to get upload link")
    exit(1)

file_url = data1["data"]["file_urls"][0]

print("\n2. Upload File")
# Use a simple dummy file if sample_scan.pdf doesn't exist just to test the API acceptance
if not os.path.exists("sample_scan.pdf"):
    with open("sample_scan.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

with open("sample_scan.pdf", "rb") as f:
    resp2 = requests.put(file_url, data=f)
print("Upload status:", resp2.status_code)

print("\n3. Submit Task")
clean_url = file_url.split("?")[0]
resp3 = requests.post("https://mineru.net/api/v4/extract/task", headers=headers, json={"url": clean_url, "is_ocr": True, "model_version": "vlm"})
data3 = resp3.json()
print("Submit response:", data3)
