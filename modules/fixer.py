"""Auto-Fixer — 37 fixers automáticos para reporte, modelo y BPA."""

import streamlit as st

from shared.loader import require_project
from ui.tab_fixer import render_fixer_tab


def render(logger):
    """Render Auto-Fixer module."""
    project = require_project()
    if project is None:
        return

    st.markdown(
        '<h1 class="main-header">🔧 Auto-Fixer</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Correcciones automáticas de problemas '
        'de reporte, modelo y Best Practices. 37 fixers disponibles.</p>',
        unsafe_allow_html=True,
    )

    render_fixer_tab(project)

    try:
        logger.log_event("fixer_module_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
