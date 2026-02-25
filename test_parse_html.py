from bs4 import BeautifulSoup
import re
from pprint import pprint

def test_parse():
    with open("raw_output_new_format.md", "r") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    
    dimensions = {}
    
    # 1. First Pass: Find Dimension Headers
    for table in tables:
        rows = table.find_all('tr')
        # Check if it's a measurement table
        is_measurement_table = False
        for row in rows:
            text = row.get_text()
            if "尺寸检验" in text or "外观检验" in text:
                is_measurement_table = True
                break
                
        if not is_measurement_table: continue
        
        # We need to map positions like "①" to column indexes and extract specs
        header_row = None
        spec_row = None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text = " ".join([c.get_text().strip() for c in cells])
            if "检验位置" in text:
                header_row = cells
                if i + 1 < len(rows):
                    spec_row = rows[i+1].find_all(['th', 'td'])
                break
                
        if header_row and spec_row:
            # First cell is "检验位置" or "检验标准"
            idx_offset = 1 
            for j in range(1, len(header_row)):
                loc_name = header_row[j].get_text(strip=True)
                if loc_name in ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']:
                    spec_text = spec_row[j].get_text(strip=True) if j < len(spec_row) else ""
                    print(f"Found Location: {loc_name}, Spec: {spec_text}")
                    
                    # Compute USL/LSL
                    usl_val = lsl_val = 0.0
                    if '±' in spec_text:
                        base, tol = spec_text.replace('mm', '').split('±')
                        base = float(base.replace('Ф', '').replace('Φ', ''))
                        tol = float(tol)
                        usl_val = base + tol
                        lsl_val = base - tol
                    elif '+' in spec_text and '-' in spec_text:
                        # "Φ4.2+0.05-0.15mm" -> base=4.2, +0.05, -0.15
                        m = re.match(r'[\u03A6Φ]?([\d\.]+)\+([\d\.]+)-([\d\.]+)mm?', spec_text)
                        if m:
                            base = float(m.group(1))
                            plus = float(m.group(2))
                            minus = float(m.group(3))
                            usl_val = base + plus
                            lsl_val = base - minus
                        
                    if loc_name not in dimensions:
                        dimensions[loc_name] = {
                            "name": f"位置 {loc_name} ({spec_text})",
                            "usl": usl_val,
                            "lsl": lsl_val,
                            "measurements": []
                        }

    # 2. Second Pass: Extract Data rows based on "序号" or "结果序号"
    print("\nDimensions mapping ready:")
    pprint(dimensions)
    
    for table in tables:
        rows = table.find_all('tr')
        # Figure out col span mappings for this specific table (e.g. ① forms columns 1,2, ② forms 3,4)
        col_to_loc = {}
        data_start_idx = -1
        
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text_cells = [c.get_text(strip=True) for c in cells]
            
            if "检验位置" in " ".join(text_cells):
                # Mapping column idx to location
                # Example headers ['检验位置', '①', '②', '③']
                for j, cell_text in enumerate(text_cells):
                    if cell_text in dimensions.keys():
                        col_to_loc[j] = cell_text
            
            if "序号" in text_cells[0] or "结果序号" in text_cells[0]:
                data_start_idx = i + 1
                break
                
        if data_start_idx != -1 and col_to_loc:
            print(f"Reading data starting row {data_start_idx} with mapping {col_to_loc}")
            for row in rows[data_start_idx:]:
                cells = row.find_all(['th', 'td'])
                if not cells: continue
                
                # Check if row is purely numbers (a data row)
                first_cell = cells[0].get_text(strip=True)
                if not first_cell.isdigit(): continue
                
                seq_num = int(first_cell)
                if seq_num > 100: continue # Likely not a sequence id
                
                # Data rows usually have format: [Seq, Val1, Result1, Val2, Result2, ...]
                # Let's map cells based on the col_to_loc indices. The offset is usually (col_idx * 2) - 1
                for map_col, loc in col_to_loc.items():
                    # For a row like [1, 2.29, OKNG, 10.20, OKNG, 3.95, OKNG]
                    # loc ① (map_col 1) -> value is at cell 1
                    # loc ② (map_col 2) -> value is at cell 3
                    # loc ③ (map_col 3) -> value is at cell 5
                    val_idx = (map_col * 2) - 1
                    if val_idx < len(cells):
                        val_str = cells[val_idx].get_text(strip=True)
                        try:
                            val = float(val_str)
                            dimensions[loc]["measurements"].append(val)
                        except:
                            pass

    print("\nExtraction Summary:")
    for loc, data in dimensions.items():
        print(f"{data['name']} -> {len(data['measurements'])} points: {data['measurements'][:5]}")

test_parse()
