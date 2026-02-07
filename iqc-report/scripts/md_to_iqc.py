#!/usr/bin/env python3
"""
Markdown to IQC Report Converter
Parses IQC inspection records from Markdown/HTML table files and generates HTML reports.
"""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from html.parser import HTMLParser

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.iqc_stats import parse_dimension_from_data, generate_iqc_data, generate_html_report


class HTMLTableParser(HTMLParser):
    """Parse HTML tables into structured data."""
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = ""
        self.in_td = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.current_table = []
        elif tag == 'tr':
            self.current_row = []
        elif tag == 'td':
            self.in_td = True
            self.current_cell = ""
            
    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_td = False
            self.current_row.append(self.current_cell.strip())
        elif tag == 'tr':
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag == 'table':
            if self.current_table:
                self.tables.append(self.current_table)
                self.current_table = []
                
    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data


def parse_html_tables(content: str) -> List[List[List[str]]]:
    """Parse HTML tables from content."""
    parser = HTMLTableParser()
    parser.feed(content)
    return parser.tables


def parse_markdown_table(content: str) -> List[Dict[str, str]]:
    """Parse markdown table into list of dictionaries."""
    lines = content.split('\n')
    tables = []
    current_table = []
    in_table = False

    for line in lines:
        if '|' in line:
            if not in_table:
                in_table = True
                current_table.append(line)
            else:
                current_table.append(line)
        else:
            if in_table and len(current_table) > 0:
                tables.append('\n'.join(current_table))
                current_table = []
                in_table = False

    if len(current_table) > 0:
        tables.append('\n'.join(current_table))

    results = []
    for table in tables:
        rows = [row.strip() for row in table.split('\n') if row.strip() and '|' in row]
        if len(rows) >= 2:
            headers = [h.strip() for h in rows[0].split('|')[1:-1]]
            data_row = rows[2] if len(rows) > 2 else ''
            values = [v.strip() for v in data_row.split('|')[1:-1]]
            results.append(dict(zip(headers, values)))

    return results


def extract_meta_info(content: str) -> Dict[str, str]:
    """Extract metadata (material info, batch, supplier, etc.) from markdown/HTML."""
    meta = {}

    # Check if content contains HTML tables
    if '<table>' in content:
        tables = parse_html_tables(content)
        if len(tables) > 0:
            # First table should contain material info
            table = tables[0]
            for row in table:
                if len(row) >= 2:
                    if '物料名称' in row[0]:
                        meta['material_name'] = row[1]
                    elif '物料编码' in row[0]:
                        meta['material_code'] = row[1]
                    elif '进料日期' in row[0]:
                        meta['date'] = row[1]
                    elif '物料批号' in row[0]:
                        # Extract batch number from combined string
                        batch_match = re.search(r'JSR\d+', row[1])
                        if batch_match:
                            meta['batch_no'] = batch_match.group()
                    elif '供应商' in row[0]:
                        meta['supplier'] = row[1]
    else:
        # Extract from markdown table
        meta_pattern = r'\|.*?物料名称.*?\|.*?\|'
        meta_match = re.search(r'项目\s*\|\s*内容.*?\n((?:\|.*?\|\s*\n)+)', content, re.DOTALL)
        if meta_match:
            meta_table = meta_match.group(1)
            lines = [line.strip() for line in meta_table.split('\n') if '|' in line]
            for line in lines:
                if '物料名称' in line:
                    meta['material_name'] = line.split('|')[-2].strip()
                elif '物料编码' in line:
                    meta['material_code'] = line.split('|')[-2].strip()
                elif '进料日期' in line:
                    meta['date'] = line.split('|')[-2].strip()
                elif '物料批号' in line:
                    meta['batch_no'] = line.split('|')[-2].strip()
                elif '供应商名称' in line or '供应商' in line:
                    meta['supplier'] = line.split('|')[-2].strip()

    return meta


def extract_dimensions_and_data(content: str) -> List[Dict[str, Any]]:
    """Extract dimension specifications and measurement data from markdown/HTML."""
    dimensions = []

    # Check if content contains HTML tables
    if '<table>' in content:
        tables = parse_html_tables(content)
        # Find dimension table (should have "检验位置" header)
        dim_table = None
        for table in tables:
            if len(table) > 0 and any('检验位置' in str(cell) for cell in table[0]):
                dim_table = table
                break
        
        if dim_table and len(dim_table) >= 3:
            # Row 0: Header row with position names
            positions = [cell.strip() for cell in dim_table[0] if cell.strip() and cell.strip() != '检验位置']
            
            # Row 1: Spec row
            specs = [cell.strip() for cell in dim_table[1] if cell.strip() and cell.strip() != '检验标准']
            
            # Row 2: Data header row ("结果序号")
            # Data rows start from row 3
            data_rows = dim_table[3:]
            
            # Group measurements by dimension (position)
            for i, pos in enumerate(positions):
                if i >= len(specs):
                    continue
                
                # Get measurements for this position
                # Column layout: 序号 | 测量值1 | 判定 | 测量值2 | 判定 | 测量值3 | 判定
                # Position i measurements are at column 2*i+1
                measurements = []
                for row in data_rows:
                    if len(row) > 2*i + 1:
                        try:
                            val = float(row[2*i + 1])
                            measurements.append(val)
                        except (ValueError, IndexError):
                            pass
                
                if len(measurements) >= 5:  # Need at least 5 measurements for statistics
                    dimensions.append({
                        'position': pos,
                        'spec': specs[i],
                        'measurements': measurements
                    })
        return dimensions

    # Find dimension section for markdown tables
    dim_section_match = re.search(
        r'### 尺寸检验结果.*?\n\n((?:\|.*?\|\s*\n)+)',
        content,
        re.DOTALL
    )

    if not dim_section_match:
        return dimensions

    # Extract header row with position names and specs
    dim_section_match = re.search(
        r'### 尺寸检验结果.*?\n\n((?:\|.*?\|\s*\n)+)',
        content,
        re.DOTALL
    )

    if not dim_section_match:
        return dimensions

    # Extract header row with position names and specs
    header_match = re.search(r'\|\s*检验位置\s*\|(.+?)\n', dim_section_match.group(0), re.DOTALL)
    if header_match:
        header_cells = [cell.strip() for cell in header_match.group(1).split('|') if cell.strip()]
        positions = header_cells

        # Extract spec row
        spec_match = re.search(r'\|\s*\*\*检验标准\*\*\s*\|(.+?)\n', dim_section_match.group(0), re.DOTALL)
        if spec_match:
            spec_cells = [cell.strip() for cell in spec_match.group(1).split('|') if cell.strip()]
            specs = spec_cells

            # Extract all data rows (skip header rows)
            # Data row format: | 1 | 27.85 | OK | 6.02 | OK | 73.14 | OK |
            # We need to skip: | 结果序号 | ... (the header row)
            all_lines = dim_section_match.group(0).split('\n')
            data_rows = []
            for line in all_lines:
                # Match rows starting with | number | and containing numeric measurements
                if re.match(r'\|\s*\d+\s*\|', line):
                    # Skip header row
                    if '结果序号' not in line:
                        # Extract row number and rest of the line
                        match = re.match(r'\|\s*(\d+)\s*\|(.+)', line)
                        if match:
                            data_rows.append((match.group(1), match.group(2)))

            # Group measurements by dimension (position)
            for i, pos in enumerate(positions):
                if i >= len(specs):
                    continue

                # Get measurements for this position
                measurements = []
                for row_num, row_data in data_rows:
                    values = [v.strip() for v in row_data.split('|') if v.strip()]
                    # Data row format after removing row number: 测量值1 | 判定 | 测量值2 | 判定 | 测量值3 | 判定
                    # Each measurement appears at index (i*2) where i is dimension index (0, 1, 2)
                    col_idx = i * 2
                    if col_idx < len(values):
                        try:
                            val = float(values[col_idx])
                            measurements.append(val)
                        except (ValueError, IndexError):
                            pass

                if len(measurements) >= 5:  # Need at least 5 measurements for statistics
                    dimensions.append({
                        'position': pos,
                        'spec': specs[i],
                        'measurements': measurements
                    })

    return dimensions


def parse_iqc_markdown(markdown_path: str) -> Dict[str, Any]:
    """Parse IQC markdown file and return structured data."""
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()

    meta = extract_meta_info(content)
    dimensions_data = extract_dimensions_and_data(content)

    return {
        'meta': meta,
        'dimensions': dimensions_data
    }


def convert_markdown_to_iqc_html(
    markdown_path: str,
    output_html: str = None
) -> str:
    """
    Convert IQC markdown file to HTML statistical report.

    Args:
        markdown_path: Path to the markdown file
        output_html: Optional output HTML path (default: same name as input with .html extension)

    Returns:
        Path to the generated HTML file
    """
    # Parse markdown
    parsed_data = parse_iqc_markdown(markdown_path)

    # Convert dimensions to statistics
    dimensions_stats = []
    for dim in parsed_data['dimensions']:
        dim_stats = parse_dimension_from_data(
            dim['position'],
            dim['spec'],
            dim['measurements']
        )
        dimensions_stats.append(dim_stats)

    # Generate IQC data structure
    iqc_data = generate_iqc_data(
        parsed_data['meta'].get('material_name', 'Unknown'),
        parsed_data['meta'].get('material_code', 'Unknown'),
        parsed_data['meta'].get('batch_no', 'Unknown'),
        parsed_data['meta'].get('supplier', 'Unknown'),
        parsed_data['meta'].get('date', 'Unknown'),
        dimensions_stats
    )

    # Generate output path if not provided
    if output_html is None:
        md_path = Path(markdown_path)
        output_html = md_path.parent / f"{md_path.stem}_iqc_report.html"

    # Generate HTML report
    generate_html_report(iqc_data, str(output_html))

    return str(output_html)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        input_md = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else None
        result = convert_markdown_to_iqc_html(input_md, output)
        print(f"✅ Converted: {input_md} -> {result}")
    else:
        print("Usage: python3 md_to_iqc.py <input_markdown> [output_html]")
