"""Environment detection — local vs Cloudera ML.

Single source of truth for runtime detection, user identity,
temp storage, and log paths. Used across the entire app.
"""

import os
import tempfile
from pathlib import Path


def is_cloud() -> bool:
    """Detect if running inside Cloudera ML (CML/CDSW)."""
    return bool(
        os.environ.get("CDSW_APP_PORT")
        or os.environ.get("CDSW_PROJECT_URL")
        or os.environ.get("CDSW_ENGINE_ID")
    )


def get_current_user() -> str:
    """Get current username — works on Windows, Linux, and CML."""
    for var in ("HADOOP_USER_NAME", "CDSW_PROJECT_USER", "USERNAME", "USER"):
        user = os.environ.get(var, "").strip()
        if user:
            return user.lower()
    return "unknown"


def get_app_port() -> int:
    """Get the port to run Streamlit on."""
    return int(os.environ.get("CDSW_APP_PORT", "8501"))


def get_temp_dir() -> Path:
    """Get temp directory for uploaded/extracted files."""
    if is_cloud():
        d = Path("/tmp/pbi_fixer")
    else:
        d = Path(tempfile.gettempdir()) / "pbi_fixer"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_log_dir() -> Path:
    """Get persistent directory for logs.

    CML: /home/cdsw is persistent across sessions.
    Local: logs/ in project root.
    """
    if is_cloud():
        d = Path("/home/cdsw/pbi_fixer_logs")
    else:
        d = Path(__file__).parent.parent / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_log_backend() -> str:
    """Determine best log backend for current environment."""
    explicit = os.environ.get("LOG_BACKEND", "").lower()
    if explicit:
        return explicit
    return "sqlite" if is_cloud() else "file"
