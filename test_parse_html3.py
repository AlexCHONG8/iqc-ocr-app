from bs4 import BeautifulSoup
import re

def test_parse():
    with open("raw_output_new_format.md", "r") as f:
        md = f.read()

    soup = BeautifulSoup(md, 'html.parser')
    tables = soup.find_all('table')
    
    dimensions = {}
    sample_size = 60
    
    # Pass 1: Dynamically find ALL dimension headers anywhere in the table
    for table in tables:
        rows = table.find_all('tr')
        # Check if it's a measurement table
        is_measurement_table = any("尺寸检验" in r.get_text() or "外观检验" in r.get_text() for r in rows)
        if not is_measurement_table: continue
        
        # We need to scan row by row because multiple headers exist in the SAME table!
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text = " ".join([c.get_text().strip() for c in cells])
            
            if "检验位置" in text or "检测项目" in text:
                header_row = cells
                spec_row = rows[i+1].find_all(['th', 'td']) if i + 1 < len(rows) else []
                
                for j in range(1, len(header_row)):
                    loc_name = header_row[j].get_text(strip=True)
                    if loc_name in ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']:
                        spec_text = spec_row[j].get_text(strip=True) if j < len(spec_row) else ""
                        usl_val, lsl_val = 10.0, 9.0
                        if '±' in spec_text:
                            try:
                                base, tol = spec_text.replace('mm', '').split('±')
                                base = float(base.replace('Ф', '').replace('Φ', ''))
                                tol = float(tol)
                                usl_val, lsl_val = base + tol, base - tol
                            except: pass
                            
                        if loc_name not in dimensions:
                            dimensions[loc_name] = {
                                "name": f"位置 {loc_name} ({spec_text})",
                                "usl": round(usl_val, 3),
                                "lsl": round(lsl_val, 3),
                                "measurements": [],
                                "_seq_map": {} 
                            }

    print(f"Found {len(dimensions)} dimensions: {list(dimensions.keys())}")
    
    # Pass 2: Extract Data Rows respecting changing headers
    for table in tables:
        rows = table.find_all('tr')
        col_to_loc = {}
        
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text_cells = [c.get_text(strip=True) for c in cells]
            line_text = " ".join(text_cells)
            
            # If we hit a header row, UPDATE our column mapping!
            if "检验位置" in line_text:
                col_to_loc.clear()
                for j, cell_text in enumerate(text_cells):
                    if cell_text in dimensions:
                        col_to_loc[j] = cell_text
                print(f"Row {i} changed map to: {col_to_loc}")
                continue # Skip processing this row as data
                
            # Data row extraction using CURRENT col_to_loc
            if col_to_loc and text_cells:
                first_cell = text_cells[0]
                if first_cell.isdigit():
                    seq_num = int(first_cell)
                    if seq_num > sample_size * 2: continue
                    
                    for header_col_idx, loc in col_to_loc.items():
                        val_idx = (header_col_idx * 2) - 1
                        if val_idx < len(text_cells):
                            val_str = text_cells[val_idx]
                            val_match = re.search(r'([\d.]+)', val_str)
                            if val_match:
                                try:
                                    val = float(val_match.group(1))
                                    dimensions[loc]["_seq_map"][seq_num] = val
                                except ValueError: pass

    # Print summary
    for loc, data in dimensions.items():
        measurements = []
        for seq, val in sorted(data["_seq_map"].items()):
            if len(measurements) < sample_size:
                measurements.append(val)
        print(f"{data['name']}: {len(measurements)} points.")

test_parse()
