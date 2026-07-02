"""Analyzer — score, métricas detalladas y recomendaciones priorizadas.

Combina las tabs Overview, Métricas y Recomendaciones del Fixer en un
único módulo con sub-tabs.
"""

import streamlit as st

from shared.loader import require_project
from ui.tab_overview import render_overview_tab
from ui.tab_metrics import render_metrics_tab
from ui.tab_recommendations import render_recommendations_tab
from ui.tab_export import render_export_tab
from ui.components import render_summary_metrics
from apps_core.layout_core.module_showcase import render_module_showcase


def render(logger):
    """Render Analyzer module."""

    # Header FIRST (visible even without project loaded)
    st.markdown(
        '<h1 class="main-header">🔍 Analyzer</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Análisis integral con score, métricas '
        'y recomendaciones basadas en 60+ reglas de Best Practices.</p>',
        unsafe_allow_html=True,
    )

    render_module_showcase(
        title="¿Qué analiza este módulo?",
        description=(
            "Evalúa tu proyecto Power BI y genera un score de calidad "
            "aplicando más de 60 reglas de Best Practices Analyzer (BPA)."
        ),
        items=[
            ("📊", "Score global 0-100"),
            ("🗂️", "Métricas de reporte"),
            ("🧮", "Métricas del modelo"),
            ("⚠️", "Recomendaciones priorizadas"),
            ("🎯", "Detección de anti-patterns"),
            ("📤", "Export CSV / JSON"),
        ],
    )

    # Now check project
    project = require_project()
    if project is None:
        return

    # Summary metrics at top
    render_summary_metrics(project)

    # Sub-tabs (from Fixer's tab_overview, tab_metrics, tab_recommendations)
    tabs = st.tabs(["Overview", "Métricas", "Recomendaciones", "Exportar"])

    with tabs[0]:
        render_overview_tab(project)
    with tabs[1]:
        render_metrics_tab(project)
    with tabs[2]:
        render_recommendations_tab(project)
    with tabs[3]:
        render_export_tab(project)

    try:
        logger.log_event("analyzer_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
