"""Memory Estimator — proyección de tamaño VertiPaq.

Wrapper thin sobre ui.tab_memory del Fixer.
"""

import streamlit as st

from shared.loader import require_project
from ui.tab_memory import render_memory_tab
from apps_core.layout_core.module_showcase import render_module_showcase


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

    render_module_showcase(
        title="¿Qué estima este módulo?",
        description=(
            "Calcula el tamaño estimado del modelo en memoria (VertiPaq) "
            "para anticipar consumo de RAM y detectar columnas problemáticas."
        ),
        items=[
            ("💾", "Tamaño total del modelo"),
            ("📏", "Estimación por tabla"),
            ("🔢", "Estimación por columna"),
            ("⚙️", "Impacto de tipos de datos"),
            ("🗜️", "Recomendaciones de compresión"),
            ("⚠️", "Detección de high-cardinality"),
        ],
    )

    render_memory_tab(project)

    try:
        logger.log_event("memory_module_viewed", {
            "score": project.overall_score,
            "report": project.report_name,
        })
    except Exception:
        pass
