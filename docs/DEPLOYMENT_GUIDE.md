# 🚀 Deployment Guide - IQC OCR + SPC Analysis

## Step 1: Create GitHub Repository (Web Interface)

### Option A: Using GitHub Website (Easiest)

1. **Go to GitHub**
   - Visit: https://github.com/new

2. **Create new repository**
   - Repository name: `iqc-ocr-app`
   - Description: `IQC OCR + SPC Analysis Web Application`
   - Select: ⚪ Public (required for Streamlit Cloud free tier)
   - ❌ Don't initialize with README (we already have code)

3. **Click "Create repository"**

4. **Copy your repository URL**
   ```
   https://github.com/YOUR_USERNAME/iqc-ocr-app.git
   ```

### Option B: Using GitHub CLI (if installed)

```bash
gh repo create iqc-ocr-app --public --source=. --remote=origin --push
```

---

## Step 2: Push Code to GitHub

Run these commands in your terminal:

```bash
cd /Users/alexchong/AI/MinerU

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/iqc-ocr-app.git

# Verify remote
git remote -v

# Push to GitHub
git push -u origin main
```

**If you get an error about "main" branch:**
```bash
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy to Streamlit Cloud

### 3.1 Go to Streamlit Cloud

Visit: https://share.streamlit.io

### 3.2 Connect GitHub

1. Click "Sign in" → Sign in with GitHub

2. Click "New app" button

### 3.3 Configure Your App

Fill in the form:

| Field | Value |
|-------|-------|
| **Repository** | Select `iqc-ocr-app` |
| **Branch** | `main` |
| **Main file path** | `app.py` |
| **App URL** (optional) | `iqc-ocr-app` (or leave blank) |

### 3.4 Click "Deploy"

Wait for deployment (takes 1-2 minutes)

---

## Step 4: Set Environment Variables (Secrets)

### 4.1 In Streamlit Cloud:

1. Go to your app settings
2. Click "Secrets" (or "Environment Variables")
3. Add these secrets:

```bash
# Your MinerU.net API key
MINERU_API_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9... (your full key)

# Optional: Team access password
APP_PASSWORD=your_team_password_here
```

### 4.2 Where to get your API key:

Your existing key is in: `/Users/alexchong/AI/MinerU/mineru_cloud_simple.py` (line 14)

---

## Step 5: Restart & Test

1. In Streamlit Cloud, click "Restart" after adding secrets

2. Visit your app URL:
   ```
   https://iqc-ocr-app.streamlit.app
   ```

3. Test with a sample PDF

---

## Step 6: Share with Team

Send this to your colleagues:

---

**📊 IQC OCR + SPC Analysis - Access Link**

**URL:** https://iqc-ocr-app.streamlit.app

**Password:** [your_password] (if you set one)

**Instructions:**
1. Open the link in any web browser
2. Enter password (if required)
3. Upload your inspection PDF
4. Wait 1-2 minutes for processing
5. Download the report (HTML → Print to PDF)

**No software installation required!**

---

## Troubleshooting

### Issue: "App not found"
- **Solution:** Wait 2-3 minutes after deployment, URL takes time to propagate

### Issue: "API key not configured"
- **Solution:** Check Secrets in Streamlit Cloud, ensure MINERU_API_KEY is set correctly

### Issue: "Upload failed"
- **Solution:** Check PDF size (max 200MB), ensure PDF is not password protected

### Issue: "No data extracted"
- **Solution:** Ensure PDF has clear, readable text and tables with measurements

---

## Quick Reference Commands

```bash
# Check git status
git status

# View remote
git remote -v

# Push changes (after making updates)
git add .
git commit -m "Update description"
git push

# View logs on Streamlit Cloud
# Go to: app → Settings → Logs
```

---

## File Locations

| File | Path |
|------|------|
| Main app | `app.py` |
| Dependencies | `requirements.txt` |
| Streamlit config | `.streamlit/config.toml` |
| SPC functions | `iqc-report/scripts/iqc_stats.py` |
| HTML template | `iqc-report/assets/iqc_template.html` |
| API key (local) | `mineru_cloud_simple.py` |

---

## Support

If you need help:
1. Check Streamlit Cloud logs for errors
2. Verify all files are pushed to GitHub
3. Ensure secrets are correctly set

---

**Your App URL will be:**
`https://iqc-ocr-app.streamlit.app`

**Or with custom URL:**
`https://your-username-iqc-ocr-app.streamlit.app`
