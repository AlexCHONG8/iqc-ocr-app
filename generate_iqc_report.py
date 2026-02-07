import sys
import os
import json
from iqc_export_skill import extract_iqc_data

def generate_report(input_file, template_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = extract_iqc_data(content)
    
    with open(template_file, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Inject data into template
    report_content = template.replace('/*JSON_DATA_HERE*/ {}', json.dumps(data, ensure_ascii=False))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = "/Users/alexchong/AI/MinerU/20260122_111541.md"
    template_path = "/Users/alexchong/AI/MinerU/templates/template_iso13485.html"
    output_path = "/Users/alexchong/AI/MinerU/IQC_Statistical_Report.html"
    
    generate_report(input_path, template_path, output_path)
