"""PBI Hub — Unified Power BI Analysis, Fixing & Optimization Suite.

Combina lo mejor de Power BI Fixer y YPF BI Monitor en una sola app.
Un solo upload de PBIP → todos los módulos lo comparten via session_state.
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from ui.styles import MAIN_CSS
from shared.loader import (
    load_project, extract_zip, clear_project, get_project, clean_path
)
from core.environment import is_cloud, get_current_user
from core.usage_logger import UsageLogger
from core.analyzers.analyzer import PowerBIAnalyzer

# Modules
from modules import home, analyzer, fixer, dax_optimizer, performance_analyzer, dax_benchmarker


# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="PBI Hub — YPF",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%23F2C811'/><text x='16' y='22' text-anchor='middle' font-size='16' fill='%230B0E14' font-family='monospace'>H</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(MAIN_CSS, unsafe_allow_html=True)

CLOUD_MODE = is_cloud()


def _get_logger() -> UsageLogger:
    if "logger" not in st.session_state:
        st.session_state.logger = UsageLogger("PBI_Hub", "1.0")
    return st.session_state.logger


# ── Sidebar ──────────────────────────────────────────────────────────

def _render_sidebar():
    """Sidebar with logo, project loader, and navigation."""

    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0 0.5rem 0;">
        <h1 style="font-size: 1.4rem; font-weight: 700; margin: 0;
                   color: #E8ECF4; letter-spacing: -0.04em;
                   font-family: 'Space Grotesk', sans-serif;">
            PBI <span style="color: #F2C811;">Hub</span>
        </h1>
        <p style="font-size: 0.68rem; margin-top: 0.4rem; color: #5A6478;
                  text-transform: uppercase; letter-spacing: 0.1em;">
            YPF Data Analytics
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Project loader ───────────────────────────────────────────────
    st.sidebar.markdown("**📁 Proyecto**")

    project = get_project()

    if project is not None:
        # Show loaded project info
        st.sidebar.success(f"✅ {project.report_name}")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.caption(f"Score: **{project.overall_score:.0f}**")
        with col2:
            if st.button("Cerrar", use_container_width=True):
                clear_project()
                st.rerun()
    else:
        # Show loader UI
        if CLOUD_MODE:
            _render_cloud_loader()
        else:
            _render_local_loader()

    st.sidebar.divider()

    # ── Navigation ───────────────────────────────────────────────────
    st.sidebar.markdown("**🧭 Navegación**")

    nav_options = [
        "🏠 Home",
        "🔍 Analyzer",
        "🔧 Auto-Fixer",
        "⚡ DAX Optimizer",
        "📈 Performance Analyzer",
        "🎯 DAX Benchmarker",
    ]

    # Store selection in session_state
    if "current_page" not in st.session_state:
        st.session_state.current_page = nav_options[0]

    page = st.sidebar.radio(
        "Nav",
        nav_options,
        label_visibility="collapsed",
        key="nav_radio",
    )

    st.sidebar.divider()

    # Footer
    st.sidebar.caption(
        "PBI Hub v1.0 · MVP\n\n"
        "Módulos futuros: DAX Optimizer, Performance Analyzer, "
        "DAX Benchmarker, DocGen, Layout Organizer, Tools, Memory, Usage."
    )

    return page


def _render_local_loader():
    """Local mode: text input with path."""
    raw_path = st.sidebar.text_input(
        "Ruta al proyecto",
        placeholder="C:/.../MiReporte.pbip",
        help="Ruta a .pbip, carpeta .SemanticModel, o .pbix",
        label_visibility="collapsed",
    )
    file_path = clean_path(raw_path)

    if st.sidebar.button("Cargar", type="primary", use_container_width=True,
                         disabled=not file_path):
        with st.spinner("Analizando..."):
            result = load_project(file_path)
            if result:
                _get_logger().log_event("project_loaded", {
                    "mode": "local",
                    "score": result.overall_score,
                    "user": get_current_user(),
                })
                st.rerun()


def _render_cloud_loader():
    """Cloud mode: ZIP file uploader."""
    uploaded = st.sidebar.file_uploader(
        "Subir proyecto (ZIP)",
        type=["zip"],
        help="ZIP con carpeta .Report (y .SemanticModel si tiene modelo).",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        with st.spinner("Extrayendo y analizando..."):
            try:
                import zipfile
                temp_dir = extract_zip(uploaded)
                st.session_state.extracted_path = temp_dir
                result = load_project(temp_dir)
                if result:
                    _get_logger().log_event("project_loaded", {
                        "mode": "cloud",
                        "score": result.overall_score,
                        "user": get_current_user(),
                    })
                    st.rerun()
            except zipfile.BadZipFile:
                st.sidebar.error("ZIP inválido")
            except Exception as e:
                st.sidebar.error(f"Error: {str(e)[:80]}")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    logger = _get_logger()
    page = _render_sidebar()

    # ── Route to module ──────────────────────────────────────────────
    if page.endswith("Home"):
        home.render(logger)
    elif page.endswith("Analyzer") and "Performance" not in page:
        analyzer.render(logger)
    elif page.endswith("Auto-Fixer"):
        fixer.render(logger)
    elif "DAX Optimizer" in page:
        dax_optimizer.render(logger)
    elif "Performance Analyzer" in page:
        performance_analyzer.render(logger)
    elif "DAX Benchmarker" in page:
        dax_benchmarker.render(logger)


if __name__ == "__main__":
    main()
