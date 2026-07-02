"""Tools — Delta Analyzer, Aggregation Suggester, Perspectives, Translations.

Wrapper thin sobre ui.tab_tools del Fixer.
"""

import streamlit as st

from shared.loader import require_project
from ui.tab_tools import render_tools_tab


def render(logger):
    """Tools module for PBI Hub."""
    project = require_project()
    if project is None:
        return

    st.markdown(
        '<h1 class="main-header">🛠️ Tools</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Herramientas avanzadas: Delta Analyzer, '
        'Aggregation Suggester, Perspectives y Translations.</p>',
        unsafe_allow_html=True,
    )

    render_tools_tab(project)

    try:
        logger.log_event("tools_module_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
