import requests
import json
import time

token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3MTkyODYwMCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiIwNjNmYzQyOC1lYzZmLTQ0MGEtODYxMy1jNTJlN2UxZDBmZGYiLCJlbWFpbCI6IiIsImV4cCI6MTc3OTcwNDYwMH0.9muRctChWY3tUdE6ctYrDgAdYzi0FUJFQwHehHj_2ThNBAHtTVtFm7TbsJMUK8gU022lCbEWfkNWBg-gyp-s2g"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Get Link
resp1 = requests.post("https://mineru.net/api/v4/file-urls/batch", headers=headers, json={"files": [{"name": "sample_scan_page0.jpg"}]})
data1 = resp1.json()
file_url = data1["data"]["file_urls"][0]

# 2. Upload
with open("sample_scan_page0.jpg", "rb") as f:
    resp2 = requests.put(file_url, data=f)
print("Upload status:", resp2.status_code)

# 3. Submit
clean_url = file_url.split("?")[0]
# Also trying with full URL
# clean_url = file_url
resp3 = requests.post("https://mineru.net/api/v4/extract/task", headers=headers, json={"url": clean_url, "is_ocr": True, "model_version": "vlm"})
data3 = resp3.json()
print("Submit response:", data3)

task_id = data3["data"]["task_id"]

# 4. Poll
for i in range(10):
    time.sleep(5)
    resp4 = requests.get(f"https://mineru.net/api/v4/extract/task/{task_id}", headers=headers)
    data4 = resp4.json()
    state = data4["data"]["state"]
    print("State:", state)
    if state == "done":
        print("Success:", data4)
        break
    elif state == "failed":
        print("Failed:", data4)
        break
