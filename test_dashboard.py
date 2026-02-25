import sys
import os

from src.ocr_service import OCRService
from src.spc_engine import SPCEngine
from src.dashboard_generator import generate_professional_dashboard

def test_dashboard_generation():
    ocr = OCRService()
    file_path = "Scan PDF/AJ26010702驱动棘轮AJR26010702原材料进货检验记录9-60.pdf"
    
    print(f"Extracting for {file_path}")
    dim_data = ocr.extract_table_data(file_path)
    
    if dim_data:
        print(f"Extracted {len(dim_data)} dimensions")
        stats_list = []
        for dim in dim_data:
            engine = SPCEngine(usl=dim['header']['usl'], lsl=dim['header']['lsl'])
            stats = engine.calculate_stats(dim['measurements'])
            stats_list.append(stats)
            
        print("Generating dashboard...")
        html_path = generate_professional_dashboard(dim_data, stats_list, layout="tabbed")
        print(f"Dashboard generated at: {html_path}")
        
if __name__ == "__main__":
    test_dashboard_generation()
