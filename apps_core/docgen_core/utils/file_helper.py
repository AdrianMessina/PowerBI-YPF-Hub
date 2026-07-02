"""
File helper utilities
"""

import tempfile
import shutil
from pathlib import Path
from typing import Optional


def save_uploaded_file(uploaded_file, target_dir: Optional[Path] = None) -> Path:
    """
    Save Streamlit uploaded file to disk

    Args:
        uploaded_file: Streamlit UploadedFile object
        target_dir: Target directory (default: temp dir)

    Returns:
        Path to saved file
    """
    if target_dir is None:
        target_dir = Path(tempfile.gettempdir()) / 'powerbi_doc_gen'

    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / uploaded_file.name

    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    return file_path


def cleanup_temp_files(temp_dir: Optional[Path] = None):
    """
    Clean up temporary files

    Args:
        temp_dir: Directory to clean (default: app temp dir)
    """
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / 'powerbi_doc_gen'

    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
