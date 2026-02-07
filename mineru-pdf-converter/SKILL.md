---
name: mineru-pdf-converter
description: Automated PDF to Markdown conversion using MinerU with support for handwritten documents, OCR in 109 languages, batch processing, API key authentication, and checkbox post-processing for form PDFs. Use for converting PDFs to Markdown, extracting handwritten/scanned content with OCR, batch processing, using API key authentication, preserving document structure with tables/formulas/images, and fixing checkbox selections in forms.
---

# MinerU PDF to Markdown Converter

## Overview

Automated PDF-to-Markdown conversion using [MinerU](https://github.com/opendatalab/MinerU), supporting:
- **Handwritten PDFs** with OCR recognition (109 languages)
- **Batch processing** of multiple PDFs
- **API key authentication** for cloud services
- **Formula conversion** to LaTeX format
- **Table extraction** to HTML/Markdown
- **Local or cloud processing** options

## Quick Start

### 1. Install MinerU

```bash
# Using pip
pip install --upgrade pip
pip install mineru[all]

# Or using uv (faster)
uv pip install mineru[all]
```

### 2. Convert a Single PDF

```bash
# Basic conversion (uses local CPU processing)
python /path/to/skill/scripts/convert_pdf.py input.pdf -o output/

# With OCR language specified (for better accuracy)
python /path/to/skill/scripts/convert_pdf.py input.pdf -o output/ -l en

# For handwritten/scanned PDFs
python /path/to/skill/scripts/convert_pdf.py handwritten.pdf -o output/ -l ch
```

### 3. Batch Convert Multiple PDFs

```bash
# Convert all PDFs in a directory
python /path/to/skill/scripts/convert_pdf.py ./pdfs/ -o output/

# Specify multiple files
python /path/to/skill/scripts/convert_pdf.py file1.pdf file2.pdf file3.pdf -o output/
```

## Backend Options

| Backend | Best For | Device | API Key |
|---------|----------|--------|---------|
| `pipeline` | CPU, handwritten PDFs | CPU/mps | No |
| `hybrid-auto-engine` | Best accuracy, GPU available | GPU/CPU | No |
| `vlm-http-client` | Cloud API with OpenAI-compatible server | Any | Yes |
| `hybrid-http-client` | Cloud API with hybrid backend | Any | Yes |

### Using Cloud API with Key

```bash
# Set API key as environment variable
export MINERU_VL_API_KEY="your-api-key-here"

# Or pass directly
python /path/to/skill/scripts/convert_pdf.py input.pdf \
    -b vlm-http-client \
    -u https://api.mineru.net/v1 \
    -k your-api-key \
    -o output/
```

## Language Options

Specify document language for improved OCR accuracy:

| Language | Code | Notes |
|----------|------|-------|
| Chinese (Simplified) | `ch` / `ch_server` | Best for handwritten Chinese |
| Chinese (Lite) | `ch_lite` | Faster, lower accuracy |
| English | `en` | Default for English documents |
| Japanese | `japan` | |
| Korean | `korean` | |
| Arabic | `arabic` | |
| Latin/European | `latin` | Covers multiple European languages |
| Auto-detect | `auto` | Slower but automatic |

## CLI Reference

```
usage: convert_pdf.py [-h] [-o OUTPUT] [-b {pipeline,hybrid-auto-engine,vlm-http-client,hybrid-http-client}]
                       [-u API_URL] [-k API_KEY] [-l LANG] [-d DEVICE]
                       input [input ...]

positional arguments:
  input                 Input PDF file(s) or directory

options:
  -h, --help            Show help message
  -o OUTPUT, --output OUTPUT
                        Output directory (default: ./output)
  -b {pipeline,hybrid-auto-engine,vlm-http-client,hybrid-http-client}, --backend {pipeline,...}
                        Parser backend (default: pipeline)
  -u API_URL, --api-url API_URL
                        API URL for http-client backends
  -k API_KEY, --api-key API_KEY
                        API key for authentication
  -l LANG, --lang LANG   Document language (default: auto)
  -d DEVICE, --device DEVICE
                        Inference device (cpu, cuda, mps, npu)
```

## Troubleshooting

### Issue: "mineru: command not found"
**Solution:** Install MinerU: `pip install mineru[all]`

### Issue: Checkbox selections show as "OK NG" instead of selected option
**Cause:** MinerU OCR captures both checkbox options but doesn't detect which is checked.

**Solution:** Use the post-processing script to fix checkboxes:
```bash
python fix_checkboxes.py output/document/document.md
```

The script fixes common patterns:
- `OK NG` → `☑OK` (checked)
- `ΦOK □NG` → `☑OK` (Φ = checked box)
- `合格 不合格` → `合格` (qualified)

For better checkbox detection during conversion:
```bash
# Enable formula/structure extraction for better form recognition
mineru -p input.pdf -o output/ --formula_enable

# Use higher DPI for checkbox clarity
mineru -p input.pdf -o output/ --dpi 300
```

### Issue: Chinese characters display incorrectly in preview
**Cause:** Preview tool may not auto-detect UTF-8 encoding.

**Solution:**
1. Add UTF-8 BOM for better compatibility:
```bash
printf '\xEF\xBB\xBF' > temp.md && cat original.md >> temp.md
```
2. Or ensure your IDE/preview tool is set to UTF-8 encoding

### Issue: Poor OCR quality on handwritten text
**Solution:**
1. Specify the correct language with `-l`
2. For Chinese, try `-l ch_server` for higher accuracy
3. Ensure the PDF is high resolution (300 DPI+ recommended)

### Issue: Out of memory errors
**Solution:**
1. Use `pipeline` backend for lower memory usage: `-b pipeline`
2. Process fewer files at once
3. Set batch ratio: `export MINERU_HYBRID_BATCH_RATIO=2`

### Issue: API authentication failures
**Solution:**
1. Verify API key is correct
2. Check API URL format (should include https://)
3. Ensure environment variable `MINERU_VL_API_KEY` is set if using cloud backend

## Output Format

Converted markdown files are saved in the output directory with the same filename as the input PDF:
- `document.pdf` → `output/document/document.md`

A `conversion_results.json` file is also created with processing details:
```json
[
  {
    "success": true,
    "input": "/path/to/input.pdf",
    "output": "/path/to/output/input/input.md"
  }
]
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MINERU_VL_API_KEY` | API key for cloud backends | - |
| `MINERU_DEVICE_MODE` | Inference device (cpu/cuda/mps/npu) | cpu |
| `MINERU_MODEL_SOURCE` | Model source (huggingface/modelscope/local) | huggingface |
| `MINERU_HYBRID_BATCH_RATIO` | Batch ratio for hybrid backends | auto |
| `MINERU_FORMULA_ENABLE` | Enable formula parsing | true |
| `MINERU_TABLE_ENABLE` | Enable table parsing | true |

## Resources

### scripts/convert_pdf.py
Main automation script for PDF to Markdown conversion. Handles batch processing, API authentication, and output management.

### scripts/fix_checkboxes.py
Post-processing script to fix checkbox selections in converted markdown. Common issue with form PDFs where OCR captures both options but doesn't detect which is checked.

### references/api_reference.md
Complete MinerU CLI reference and API documentation.

## Related Links

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [MinerU Documentation](https://opendatalab.github.io/MinerU/)
- [MinerU Web App](https://mineru.net)
- [MinerU API Docs](https://mineru.net/apiManage/docs)
