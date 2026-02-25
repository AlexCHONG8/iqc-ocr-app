from bs4 import BeautifulSoup
import re
from pprint import pprint

def test_parse():
    with open("raw_output_new_format.md", "r") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    
    dimensions = {}
    sample_size = 60 # Default, try to find it dynamically later
    
    # Extract Global Batch Info
    batch_info = {
        "batch_id": "Unknown",
        "batch_size": None
    }
    for table in tables:
        text = table.get_text()
        if "物料批号" in text:
            cells = table.find_all('td')
            for i, cell in enumerate(cells):
                if "物料批号" in cell.get_text():
                    if i + 1 < len(cells):
                        batch_info["batch_id"] = cells[i+1].get_text(strip=True)
                if "进料数量" in cell.get_text():
                    if i + 1 < len(cells):
                        try:
                            batch_info["batch_size"] = int(cells[i+1].get_text(strip=True))
                        except: pass
                if "抽样数量" in cell.get_text():
                    if i + 1 < len(cells):
                        try:
                            sample_size = int(cells[i+1].get_text(strip=True))
                        except: pass

    # 1. First Pass: Find Dimension Headers
    for table_idx, table in enumerate(tables):
        rows = table.find_all('tr')
        is_measurement_table = any("尺寸检验" in r.get_text() or "外观检验" in r.get_text() for r in rows)
        if not is_measurement_table: continue
        
        header_row, spec_row = None, None
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text = " ".join([c.get_text().strip() for c in cells])
            if "检验位置" in text or "检测项目" in text:
                header_row = cells
                if i + 1 < len(rows): spec_row = rows[i+1].find_all(['th', 'td'])
                break
                
        if header_row and spec_row:
            for j in range(1, len(header_row)):
                loc_name = header_row[j].get_text(strip=True)
                # Look for circles 1-10
                if loc_name in ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']:
                    spec_text = spec_row[j].get_text(strip=True) if j < len(spec_row) else ""
                    
                    # Compute USL/LSL
                    usl_val, lsl_val = 10.0, 9.0 # fallback
                    if '±' in spec_text:
                        base, tol = spec_text.replace('mm', '').split('±')
                        base = float(base.replace('Ф', '').replace('Φ', ''))
                        tol = float(tol)
                        usl_val, lsl_val = base + tol, base - tol
                    elif '+' in spec_text and '-' in spec_text:
                        m = re.match(r'[\u03A6Φ]?([\d\.]+)\+([\d\.]+)-([\d\.]+)mm?', spec_text)
                        if m:
                            base, plus, minus = float(m.group(1)), float(m.group(2)), float(m.group(3))
                            usl_val, lsl_val = base + plus, base - minus
                        
                    if loc_name not in dimensions:
                        dimensions[loc_name] = {
                            "name": f"位置 {loc_name} ({spec_text})",
                            "usl": round(usl_val, 3),
                            "lsl": round(lsl_val, 3),
                            "measurements": [] # we will use a dictionary mapped by sequence ID to handle dupes
                        }
                        # Initialize a dictionary for sequence mapping inside the dimension
                        dimensions[loc_name]["_seq_map"] = {}

    # 2. Extract Data Rows
    # Table layout varies, but row format is generally: [Seq, Val1, Result1, Val2, Result2, ...]
    for table in tables:
        rows = table.find_all('tr')
        
        # Determine column mapping for this specific table (e.g. col 1 belongs to ①)
        col_to_loc = {}
        data_start_idx = -1
        
        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            text_cells = [c.get_text(strip=True) for c in cells]
            
            if "检验位置" in " ".join(text_cells):
                for j, cell_text in enumerate(text_cells):
                    if cell_text in dimensions:
                        col_to_loc[j] = cell_text
            
            if "序号" in text_cells[0] or "结果序号" in text_cells[0]:
                data_start_idx = i + 1
                break
                
        if data_start_idx != -1 and col_to_loc:
            # print(f"Processing table starting row {data_start_idx}, mapping: {col_to_loc}")
            for row in rows[data_start_idx:]:
                cells = row.find_all(['th', 'td'])
                if not cells: continue
                
                # Check for two sequence columns! Sometimes tables are split horizontally:
                # [Seq(0), Val(1), Res(2), Seq(3), Val(4), Res(5)]
                # Let's dynamically find all cells that look like strictly sequence IDs.
                
                text_cells = [c.get_text(strip=True) for c in cells]
                
                # Assume standard horizontal layout mapped to headers:
                # The headers were e.g., ['检验位置', '①', '②', '③']
                # Data row: ['1', '2.29', 'OKNG', '10.20', 'OKNG', '3.95', 'OKNG']
                first_cell = text_cells[0]
                if not first_cell.isdigit(): continue
                seq_num = int(first_cell)
                if seq_num > sample_size * 2: continue # Sanity limit
                
                # For standard layout, loc 1 -> cells 1,2; loc 2 -> cells 3,4.
                for header_col_idx, loc in col_to_loc.items():
                    val_idx = (header_col_idx * 2) - 1
                    if val_idx < len(text_cells):
                        val_str = text_cells[val_idx]
                        try:
                            val = float(val_str)
                            dimensions[loc]["_seq_map"][seq_num] = val
                        except Exception as e:
                            pass
                            
                # Check if there's a SECOND sequence column in the same row!
                # E.g. cells structure: [1, val, res, 19, val, res]
                # In the new format, columns map the SAME dimension properties over different sequences on the SAME page.
                # Actually, the header for column split was just `['序号', '结果判定', '序号', '结果判定']` for Appearance logic.
                # For dimensions, the headers were `[检验位置, ①, ②, ③]` - single sequence column on left.
                
    # 3. Finalize Output
    final_output = []
    print(f"Sample Size expected: {sample_size}")
    
    for loc, data in dimensions.items():
        # Flatten the seq map, handling duplicates safely
        seq_items = sorted(data["_seq_map"].items())
        
        # TRUNCATE to exact sample size based on the sequence 1..N
        # We need exactly `sample_size` points.
        measurements = []
        for seq, val in seq_items:
            # We skip duplicates inherently due to dictionary keys, and we can enforce sequence order
            if len(measurements) < sample_size:
                measurements.append(val)
                
        print(f"{data['name']}: Final extracted {len(measurements)} points.")
        if len(measurements) > 0:
            final_output.append({
                "header": {
                    "batch_id": batch_info["batch_id"],
                    "batch_size": batch_info["batch_size"],
                    "dimension_name": data["name"],
                    "usl": data["usl"],
                    "lsl": data["lsl"]
                },
                "measurements": measurements
            })

    print(f"Total Dimensions successfully parsed: {len(final_output)}")
    # pprint(final_output[0])

test_parse()
