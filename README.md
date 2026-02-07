# IQC OCR + SPC Analysis

A cloud-based web application for processing handwritten inspection reports with OCR and generating ISO 13485 compliant statistical process control (SPC) reports.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- ✅ **PDF OCR Recognition** - Supports 109 languages including Chinese handwriting
- ✅ **6SPC Statistical Analysis** - Complete process capability analysis
- ✅ **Interactive Control Charts** - Xbar-R, Histogram, Probability plots
- ✅ **ISO 13485 Compliant** - Professional quality reports
- ✅ **Cloud-Based** - No local installation required for end users
- ✅ **Team Collaboration** - Secure access for small teams

## Quick Start

### Option 1: Deploy to Streamlit Cloud (Recommended)

1. **Fork or clone this repository**
   ```bash
   git clone https://github.com/yourusername/iqc-ocr-app.git
   cd iqc-ocr-app
   ```

2. **Get MinerU.net API Key**
   - Visit [https://mineru.net](https://mineru.net)
   - Sign up for free account
   - Get your API key from dashboard

3. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git push -u origin main
   ```

4. **Deploy to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file path: `app.py`
   - In Secrets, add: `MINERU_API_KEY=your_api_key_here`
   - Click "Deploy"

5. **Share with Team**
   - Share the deployed URL
   - Set `APP_PASSWORD` in secrets for team access

### Option 2: Run Locally

1. **Install Python 3.8+**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   # Create .env file
   echo "MINERU_API_KEY=your_api_key_here" > .env
   echo "APP_PASSWORD=your_password_here" >> .env
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**
   - Navigate to [http://localhost:8501](http://localhost:8501)

## Usage

1. **Upload PDF** - Select a scanned inspection report (max 200MB)

2. **Process OCR** - Click "Start OCR Processing" and wait 1-2 minutes

3. **Review Data** - Verify extracted measurements and specifications

4. **Generate Report** - Download HTML report with interactive charts

5. **Save as PDF** - Open HTML in browser and use "Print to PDF"

## Project Structure

```
MinerU/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml           # Streamlit configuration
├── iqc-report/
│   ├── scripts/
│   │   └── iqc_stats.py      # 6SPC calculation functions
│   └── assets/
│       └── iqc_template.html # HTML report template
├── mineru_cloud_simple.py    # MinerU.net API client
└── README.md                 # This file
```

## Statistical Methods

### 6SPC (Six Sigma Statistical Process Control)

The application calculates the following metrics:

- **Cp** - Process Capability Index
- **Cpk** - Process Capability Index (adjusted for centering)
- **Pp** - Overall Performance Index
- **Ppk** - Overall Performance Index (adjusted)
- **Xbar-R Charts** - Control charts for subgroup means and ranges
- **Process Spread** - 6σ distribution width

### Interpretation Guidelines

| Cpk Value | Status | Recommendation |
|-----------|--------|----------------|
| Cpk ≥ 1.33 | ✅ Excellent | Process is capable and centered |
| 1.0 ≤ Cpk < 1.33 | ⚠️ Fair | Monitor process centering |
| Cpk < 1.0 | ❌ Poor | Investigate and improve process |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MINERU_API_KEY` | MinerU.net API key | Yes |
| `APP_PASSWORD` | Team access password | Optional |

## Troubleshooting

### OCR Processing Fails

- Check API key is valid in Secrets/Environment
- Verify PDF is not password protected
- Try uploading a smaller PDF file

### Data Extraction Fails

- Ensure PDF has clear, readable text
- Check for table structure in inspection data
- Try cropping PDF to relevant sections only

### Report Generation Fails

- Clear browser cache and reload
- Check extracted data has valid measurements
- Try downloading HTML instead of PDF

## System Requirements

### For Development (Local)
- Python 3.8 or higher
- 500MB disk space for Python environment
- 2GB RAM minimum

### For Deployment (Streamlit Cloud Free Tier)
- 1GB RAM (sufficient for web interface)
- 1GB disk space
- No cost for basic usage

### For End Users
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection
- No software installation required

## License

MIT License - feel free to use and modify for your needs.

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: [your email]

## Acknowledgments

- [MinerU.net](https://mineru.net) - OCR processing
- [Streamlit](https://streamlit.io) - Web framework
- [Chart.js](https://chartjs.org) - Data visualization

---

**Made with ❤️ for Quality Control Professionals**
