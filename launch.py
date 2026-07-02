"""Cloudera CDSW/CML Application entry point for PBI Hub."""

import os
import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "streamlit", "run", "app.py",
    "--server.port", os.environ.get("CDSW_APP_PORT", "8501"),
    "--server.address", "127.0.0.1",
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
])
