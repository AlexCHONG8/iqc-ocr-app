import requests
import time

token = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIxMTgwMDcwNCIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3MTkyODYwMCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTg2MTY5OTAzODMiLCJvcGVuSWQiOm51bGwsInV1aWQiOiIwNjNmYzQyOC1lYzZmLTQ0MGEtODYxMy1jNTJlN2UxZDBmZGYiLCJlbWFpbCI6IiIsImV4cCI6MTc3OTcwNDYwMH0.9muRctChWY3tUdE6ctYrDgAdYzi0FUJFQwHehHj_2ThNBAHtTVtFm7TbsJMUK8gU022lCbEWfkNWBg-gyp-s2g"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("Uploading to tmpfiles.org...")
with open("sample_scan.pdf", "rb") as f:
    resp1 = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f})

data1 = resp1.json()
viewer_url = data1["data"]["url"]
public_url = viewer_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
print("URL:", public_url)

print("Submitting to MinerU...")
resp3 = requests.post("https://mineru.net/api/v4/extract/task", headers=headers, json={"url": public_url, "is_ocr": True, "model_version": "vlm"})
data3 = resp3.json()
print(data3)

if data3["code"] == 0:
    task_id = data3["data"]["task_id"]
    for i in range(12):
        time.sleep(5)
        resp4 = requests.get(f"https://mineru.net/api/v4/extract/task/{task_id}", headers=headers)
        data4 = resp4.json()
        state = data4["data"]["state"]
        print("State:", state)
        if state == "done":
            print("Success!", data4)
            break
        elif state == "failed":
            print("Failed:", data4)
            break
