# MinerU API Reference

Complete reference for MinerU CLI tools and API options.

## Core Commands

### mineru
Main CLI tool for PDF to Markdown conversion.

```bash
mineru [OPTIONS]
```

**Options:**
- `-p, --path PATH` - Input file path or directory (required)
- `-o, --output PATH` - Output directory (required)
- `-b, --backend` - Parser backend (default: hybrid-auto-engine)
  - `pipeline` - CPU-based, good for handwritten
  - `hybrid-auto-engine` - Auto-select GPU/CPU, best accuracy
  - `vlm-auto-engine` - VLM with auto device selection
  - `hybrid-http-client` - Cloud API with hybrid backend
  - `vlm-http-client` - Cloud API with VLM backend
- `-m, --method` - Parsing method: auto, txt, ocr (pipeline/hybrid only)
- `-l, --lang` - Document language for OCR
- `-u, --url TEXT` - Service address for http-client backends
- `-s, --start INTEGER` - Starting page number (0-based)
- `-e, --end INTEGER` - Ending page number (0-based)
- `-f, --formula BOOLEAN` - Enable formula parsing (default: true)
- `-t, --table BOOLEAN` - Enable table parsing (default: true)
- `-d, --device TEXT` - Inference device (cpu/cuda/cuda:0/npu/mps)
- `--vram INTEGER` - Max GPU VRAM per process in GB (pipeline only)
- `--source` - Model source: huggingface, modelscope, local

### mineru-api
Start a local API server for remote processing.

```bash
mineru-api [OPTIONS]
```

**Options:**
- `--host TEXT` - Server host (default: 127.0.0.1)
- `--port INTEGER` - Server port (default: 8000)
- `--reload` - Enable auto-reload (development mode)

### mineru-gradio
Start a Gradio web interface.

```bash
mineru-gradio [OPTIONS]
```

**Options:**
- `--enable-example BOOLEAN` - Enable example files
- `--enable-http-client BOOLEAN` - Enable http-client backend
- `--enable-api BOOLEAN` - Enable Gradio API
- `--max-convert-pages INTEGER` - Max pages to convert
- `--server-name TEXT` - Server name
- `--server-port INTEGER` - Server port
- `--latex-delimiters-type [a|b|all]` - LaTeX delimiter type

## Language Codes

| Code | Language |
|------|----------|
| `ch` | Chinese (server) |
| `ch_server` | Chinese (server, high accuracy) |
| `ch_lite` | Chinese (lite, fast) |
| `en` | English |
| `korean` | Korean |
| `japan` | Japanese |
| `chinese_cht` | Chinese Traditional |
| `ta` | Tamil |
| `te` | Telugu |
| `ka` | Kannada |
| `th` | Thai |
| `el` | Greek |
| `latin` | Latin/European languages |
| `arabic` | Arabic |
| `east_slavic` | East Slavic languages |
| `cyrillic` | Cyrillic languages |
| `devanagari` | Devanagari scripts |

## Environment Variables

### Authentication
- `MINERU_VL_API_KEY` - API key for vlm/hybrid backends
- `MINERU_VL_MODEL_NAME` - Model name for multi-model servers

### Device Configuration
- `MINERU_DEVICE_MODE` - Inference device (cpu/cuda/mps/npu)
- `MINERU_VIRTUAL_VRAM_SIZE` - Max GPU VRAM per process (GB)

### Model Configuration
- `MINERU_MODEL_SOURCE` - Model source (huggingface/modelscope/local)
- `MINERU_HYBRID_BATCH_RATIO` - Batch ratio for hybrid backends
- `MINERU_HYBRID_FORCE_PIPELINE_ENABLE` - Force pipeline for text extraction

### Feature Toggles
- `MINERU_FORMULA_ENABLE` - Enable formula parsing (true/false)
- `MINERU_FORMULA_CH_SUPPORT` - Chinese formula optimization (true/false)
- `MINERU_TABLE_ENABLE` - Enable table parsing (true/false)
- `MINERU_TABLE_MERGE_ENABLE` - Enable table merging (true/false)

### Performance Tuning
- `MINERU_PDF_RENDER_TIMEOUT` - PDF render timeout in seconds (default: 300)
- `MINERU_INTRA_OP_NUM_THREADS` - ONNX intra-op threads (default: -1)
- `MINERU_INTER_OP_NUM_THREADS` - ONNX inter-op threads (default: -1)

### Configuration
- `MINERU_TOOLS_CONFIG_JSON` - Config file path (default: ~/mineru.json)

## Cloud API Usage

### Setting up API Key

```bash
# Environment variable (recommended)
export MINERU_VL_API_KEY="your-api-key"

# Or pass via mineru command with http-client backend
mineru -p input.pdf -o output/ \
    -b vlm-http-client \
    -u https://your-api-endpoint.com/v1
```

### MinerU.net Cloud API

For official MinerU.net cloud services:
1. Visit https://mineru.net/apiManage/docs
2. Sign up and get your API key
3. Use the provided API endpoint URL

```bash
python convert_pdf.py input.pdf \
    -b vlm-http-client \
    -u https://api.mineru.net/v1 \
    -k your-api-key \
    -o output/
```

## Output File Structure

```
output/
├── input_filename/
│   ├── input_filename.md          # Main markdown output
│   ├── images/                    # Extracted images
│   └── auto.json                  # Structured JSON output
└── conversion_results.json        # Batch processing results
```

## Error Codes

| Error | Cause | Solution |
|-------|-------|----------|
| `command not found` | MinerU not installed | `pip install mineru[all]` |
| `CUDA out of memory` | GPU memory exhausted | Use `pipeline` backend or reduce batch size |
| `API key invalid` | Authentication failed | Check `MINERU_VL_API_KEY` |
| `File not found` | Input path incorrect | Verify input file path |
| `Permission denied` | No write access to output | Check output directory permissions |
