"""Usage Dashboard — métricas de uso de la suite.

Wrapper thin sobre ui.tab_usage del Fixer.
NO requiere proyecto cargado (funciona con logs del logger).
"""

import streamlit as st

from ui.tab_usage import render_usage_tab


def render(logger):
    """Usage Dashboard module for PBI Hub."""

    st.markdown(
        '<h1 class="main-header">📊 Usage Dashboard</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Métricas de uso de la suite: eventos, '
        'usuarios activos, apps más utilizadas.</p>',
        unsafe_allow_html=True,
    )

    render_usage_tab()

    try:
        logger.log_event("usage_module_viewed", {})
    except Exception:
        pass
