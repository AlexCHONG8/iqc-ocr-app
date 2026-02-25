"""
Entry point for Streamlit Community Cloud.
This file simply delegates execution to the main UI file in src/
so that the cloud platform can find and run it automatically.
"""
import sys
import os

# Ensure the root directory is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Read and execute the actual UI script in the same context
ui_path = os.path.join(current_dir, "src", "verify_ui.py")
with open(ui_path, "r", encoding="utf-8") as f:
    code = f.read()
    exec(code, globals())
