---
name: iqc-report
description: Generate ISO 13485 compliant IQC statistical reports with 6SPC analysis including Cp/Cpk/Pp/Ppk indices, Xbar-R control charts, histograms, and normal probability plots. Supports both JSON and Markdown input formats. Use when - User requests IQC statistical analysis from inspection data files, Keywords like IQC, Cpk, 6SPC, process capability, control chart are mentioned, Quality inspection data needs to be converted to HTML reports with interactive charts. Supports Chinese quality inspection records with specifications like bilateral tolerance or symmetric diameter tolerance. Converts raw inspection markdown files to interactive HTML statistical reports.
---

# IQC Statistical Report Generator

Generate ISO 13485 compliant IQC statistical analysis reports with 6SPC (Six Sigma Statistical Process Control) charts. Supports both JSON and Markdown input formats.

## Quick Start

### From Markdown File
```bash
# Convert markdown IQC record to HTML report
python3 scripts/md_to_iqc.py input.md output.html
```

### From JSON File
```bash
# Parse inspection data and generate HTML report
python3 scripts/iqc_stats.py input.json output.html
```

## Workflow

### Markdown to HTML
1. **Parse markdown** - Extract metadata (material, batch, supplier) and inspection tables
2. **Parse dimensions** - Extract position names, specifications, and measurement data
3. **Calculate statistics** - Run 6SPC analysis (Cp/Cpk/Pp/Ppk, control limits)
4. **Generate HTML** - Embed data in template with Chart.js visualizations
5. **Validate output** - Check all values are within specification limits

### JSON to HTML
1. **Parse input data** - Extract dimensions, measurements, and metadata from JSON file
2. **Calculate statistics** - Run 6SPC analysis (Cp/Cpk/Pp/Ppk, control limits)
3. **Generate HTML** - Embed data in template with Chart.js visualizations
4. **Validate output** - Check all values are within specification limits

## Input Format

### Markdown Format

Chinese quality inspection record with tables:

```markdown
# 原材料进货检验记录

| 项目 | 内容 |
|------|------|
| 物料名称 | 推杆 |
| 进料日期 | 2025.12.15 |
| 物料编码 | 1M131AISI1011000 |
| 物料批号 | JSR25121502 |
| 供应商名称 | 思纳福 |

### 尺寸检验结果

| 检验位置 | 1 | 11 |
|----------|---|----|
| **检验标准** | 27.80+0.10-0.00(mm) | Φ6.00±0.10(mm) |

| 序号 | 测试结果(1) | 测试结果(11) |
|------|-------------|--------------|
| 1 | 27.85 | 6.02 |
| 2 | 27.84 | 6.02 |
| ... | ... | ... |
```

### JSON Format

JSON structure or parsed inspection record:

```json{
  "meta": {
    "material_name": "推杆",
    "material_code": "1M131AISI1011000",
    "batch_no": "JSR25121502",
    "supplier": "思纳福医疗",
    "date": "2025.12.15"
  },
  "dimensions": [
    {
      "position": "位置1 Position 1",
      "spec": "27.80+0.10-0.00 mm",
      "measurements": [27.85, 27.84, ...]
    }
  ]
}
```

## Specification Parsing

See [spec_parsing.md](references/spec_parsing.md) for supported formats:
- Bilateral: `27.80+0.10-0.00`
- Symmetric: `Ø6.00±0.10`
- Unilateral: `73.20+0.00-0.15`

## Statistical Calculations

The script calculates:
- **Cp/Cpk** - Process capability indices
- **Pp/Ppk** - Overall performance indices
- **Xbar-R charts** - Control charts with UCL/LCL
- **6σ spread** - Six sigma process spread
- Subgroup statistics (n=5): mean, range, control limits

## Output

Interactive HTML report with:
- Meta information header
- Per-dimension analysis cards
- 5 Chart.js visualizations per dimension:
  - Capability plot (process 6σ vs spec tolerance)
  - Histogram
  - Xbar control chart
  - Range control chart
  - Normal probability plot
- Raw data table
- AI quality suggestions based on Cpk values

## Resources

- `scripts/md_to_iqc.py` - Markdown parser and converter
- `scripts/iqc_stats.py` - Statistical calculation engine
- `assets/iqc_template.html` - HTML report template
- `references/spec_parsing.md` - Specification format reference
