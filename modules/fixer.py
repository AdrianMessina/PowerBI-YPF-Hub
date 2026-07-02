"""Auto-Fixer — 37 fixers automáticos para reporte, modelo y BPA."""

import streamlit as st

from shared.loader import require_project
from ui.tab_fixer import render_fixer_tab
from apps_core.layout_core.module_showcase import render_module_showcase


def render(logger):
    """Render Auto-Fixer module."""

    # Header FIRST (visible even without project loaded)
    st.markdown(
        '<h1 class="main-header">🔧 Auto-Fixer</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Correcciones automáticas de problemas '
        'de reporte, modelo y Best Practices. 37 fixers disponibles.</p>',
        unsafe_allow_html=True,
    )

    render_module_showcase(
        title="¿Qué corrige automáticamente?",
        description=(
            "Aplica 37 correcciones automáticas sin abrir Power BI Desktop. "
            "Cubre problemas de reporte (PBIR), modelo (TMDL) y BPA."
        ),
        items=[
            ("🎨", "11 fixers de reporte"),
            ("🧱", "10 fixers de modelo"),
            ("📏", "16 fixers BPA"),
            ("✅", "Validador post-fix"),
            ("🔄", "Rollback disponible"),
            ("📋", "Log de cambios aplicados"),
        ],
    )

    # Now check project
    project = require_project()
    if project is None:
        return

    render_fixer_tab(project)

    try:
        logger.log_event("fixer_module_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
