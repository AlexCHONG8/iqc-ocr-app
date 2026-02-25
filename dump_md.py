import json
from src.ocr_service import OCRService

ocr = OCRService()
file_path = "Scan PDF/AJ26012204旋钮AJR26012102原材料进货检验记录4-60.pdf"
md = ocr.client.process_file(file_path)

with open("dumped.md", "w", encoding="utf-8") as f:
    f.write(md)

print("Saved MD to dumped.md")

dim_data = ocr._parse_markdown_to_json(md)
print(f"Extracted {len(dim_data)} dimensions")
for dim in dim_data:
    print(dim["header"]["dimension_name"], len(dim["measurements"]))
