"""Project loader — unified PBIP/PBIX loading for all modules.

Handles both local paths and cloud ZIP uploads. Once loaded, the project
lives in st.session_state and all modules read from it.
"""

import os
import shutil
import tempfile
import zipfile
from typing import Optional, Tuple

import streamlit as st

from core.analyzers.analyzer import PowerBIAnalyzer


def get_analyzer() -> PowerBIAnalyzer:
    """Return cached analyzer instance."""
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = PowerBIAnalyzer()
    return st.session_state.analyzer


def clean_path(raw_path: str) -> str:
    """Normalize a user-provided path (removes quotes, trailing slashes)."""
    if not raw_path:
        return ""
    path = raw_path.strip().strip('"').strip("'").strip()
    path = path.replace("\\", "/").rstrip("/")
    return path


def extract_zip(uploaded_file) -> str:
    """Extract uploaded ZIP to a temp directory. Returns extracted path."""
    temp_dir = tempfile.mkdtemp(prefix="pbi_hub_")
    with zipfile.ZipFile(uploaded_file, "r") as zf:
        zf.extractall(temp_dir)
    return temp_dir


def load_project(source_path: str) -> Optional[object]:
    """Load and analyze a PBIP/PBIX project.

    Args:
        source_path: File or folder path

    Returns:
        AnalysisResult or None on failure
    """
    resolved = PowerBIAnalyzer.resolve_path(source_path)
    if not os.path.exists(resolved):
        st.error(f"No se encontró: `{source_path}`")
        return None

    analyzer = get_analyzer()
    try:
        result = analyzer.analyze(resolved)
        st.session_state.project = result
        st.session_state.project_path = resolved
        return result
    except Exception as e:
        st.error(f"Error analizando el proyecto: {str(e)}")
        import traceback
        with st.expander("Detalles del error"):
            st.code(traceback.format_exc())
        return None


def clear_project():
    """Clear the loaded project from session state and cleanup temp dirs."""
    ext_path = st.session_state.get("extracted_path")
    if ext_path and os.path.isdir(ext_path):
        shutil.rmtree(ext_path, ignore_errors=True)

    for key in ("project", "project_path", "extracted_path"):
        if key in st.session_state:
            del st.session_state[key]


def get_project():
    """Return the currently loaded project (or None)."""
    return st.session_state.get("project")


def require_project() -> Optional[object]:
    """Return project or show a warning + return None. Modules use this."""
    project = get_project()
    if project is None:
        st.warning(
            "**Ningún proyecto cargado.** "
            "Cargá un archivo PBIP o ZIP desde el sidebar para comenzar."
        )
        return None
    return project
