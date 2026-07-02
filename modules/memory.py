"""Memory Estimator — proyección de tamaño VertiPaq.

Wrapper thin sobre ui.tab_memory del Fixer.
"""

import streamlit as st

from shared.loader import require_project
from ui.tab_memory import render_memory_tab


def render(logger):
    """Memory Estimator module for PBI Hub."""
    project = require_project()
    if project is None:
        return

    st.markdown(
        '<h1 class="main-header">💾 Memory Estimator</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Proyección del tamaño del modelo VertiPaq '
        'en memoria basado en cardinalidad y tipos de columnas.</p>',
        unsafe_allow_html=True,
    )

    render_memory_tab(project)

    try:
        logger.log_event("memory_module_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
