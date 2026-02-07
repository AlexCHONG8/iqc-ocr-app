# MinerU PDF to Markdown Converter - Skill

Convert PDFs to Markdown using MinerU with support for handwritten documents, OCR in 109 languages, and batch processing.

## Quick Start

```bash
# Install MinerU
pip install mineru[all]

# Convert a PDF
mineru -p input.pdf -o output/

# Convert with Chinese OCR
mineru -p input.pdf -o output/ -l ch_server

# Convert with checkbox fix post-processing
python scripts/fix_checkboxes.py output/document/document.md
```

## Features

- **Handwritten PDFs** with OCR recognition (109 languages)
- **Batch processing** of multiple PDFs
- **API key authentication** for cloud services
- **Formula conversion** to LaTeX format
- **Table extraction** to HTML/Markdown
- **Checkbox post-processing** for form PDFs

## Common Issues

### Checkbox selections show "OK NG" instead of selected option
```bash
python scripts/fix_checkboxes.py output/document/document.md
```

### Chinese characters display incorrectly
Ensure your preview tool uses UTF-8 encoding. Add UTF-8 BOM if needed:
```bash
printf '\xEF\xBB\xBF' > temp.md && cat original.md >> temp.md
```

## File Structure

```
mineru-pdf-converter/
├── SKILL.md                 # Main skill documentation
├── README.md                # This file
├── scripts/
│   ├── convert_pdf.py       # Main conversion script
│   └── fix_checkboxes.py    # Checkbox post-processing
└── references/
    └── api_reference.md     # MinerU API reference
```

## Links

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [MinerU Documentation](https://opendatalab.github.io/MinerU/)
