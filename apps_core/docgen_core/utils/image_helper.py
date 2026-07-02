"""
Image helper utilities for managing uploaded images
"""

import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validate_image_format(file) -> bool:
    """
    Validate that uploaded file is a supported image format

    Args:
        file: Streamlit UploadedFile object

    Returns:
        True if format is valid (PNG, JPG, JPEG)
    """
    if not hasattr(file, 'name'):
        return False

    valid_extensions = ['.png', '.jpg', '.jpeg']
    file_ext = Path(file.name).suffix.lower()

    return file_ext in valid_extensions


def save_uploaded_images(uploaded_files, prefix: str = "viz") -> List[str]:
    """
    Save uploaded images to temporary directory

    Args:
        uploaded_files: List of Streamlit UploadedFile objects or single file
        prefix: Prefix for saved filenames (default: "viz")

    Returns:
        List of paths to saved images
    """
    # Handle single file
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files] if uploaded_files else []

    logger.info(f"save_uploaded_images called with {len(uploaded_files)} file(s), prefix='{prefix}'")

    # Create temp directory
    temp_dir = Path(tempfile.gettempdir()) / 'powerbi_doc_gen' / 'temp_images'
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using temp directory: {temp_dir}")

    saved_paths = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for idx, uploaded_file in enumerate(uploaded_files):
        if not uploaded_file:
            logger.warning(f"Skipping None uploaded file at index {idx}")
            continue

        if not validate_image_format(uploaded_file):
            logger.warning(f"Skipping invalid image format: {uploaded_file.name}")
            continue

        # Generate unique filename with timestamp
        file_ext = Path(uploaded_file.name).suffix.lower()
        filename = f"{prefix}_{timestamp}_{idx}{file_ext}"
        file_path = temp_dir / filename

        try:
            # Save file
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            saved_paths.append(str(file_path))
            logger.info(f"✓ Saved image {idx+1}: {file_path} (size: {file_path.stat().st_size} bytes)")

        except Exception as e:
            logger.error(f"✗ Error saving image {uploaded_file.name}: {e}")
            continue

    logger.info(f"save_uploaded_images completed: {len(saved_paths)} images saved successfully")
    return saved_paths


def cleanup_temp_images(image_paths: Optional[List[str]] = None):
    """
    Clean up temporary images after document generation

    Args:
        image_paths: Optional list of specific image paths to delete.
                    If None, cleans entire temp_images directory.
    """
    try:
        if image_paths:
            # Delete specific files
            for path_str in image_paths:
                path = Path(path_str)
                if path.exists() and path.is_file():
                    path.unlink()
                    logger.info(f"Deleted temporary image: {path}")
        else:
            # Clean entire temp_images directory
            temp_dir = Path(tempfile.gettempdir()) / 'powerbi_doc_gen' / 'temp_images'
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned temp images directory: {temp_dir}")

    except Exception as e:
        logger.error(f"Error cleaning up temporary images: {e}")


def get_temp_image_dir() -> Path:
    """
    Get the temporary images directory path

    Returns:
        Path to temp images directory
    """
    return Path(tempfile.gettempdir()) / 'powerbi_doc_gen' / 'temp_images'
