"""Recommendations tab - categorized issues with fix links."""

import streamlit as st
from core.models import AnalysisResult, Severity
from ui.components import render_recommendation


def render_recommendations_tab(result: AnalysisResult):
    """Render the recommendations tab."""

    if not result.recommendations:
        st.success("No se encontraron problemas. El reporte cumple con las mejores practicas.")
        return

    # Summary
    critical = [r for r in result.recommendations if r.severity == Severity.CRITICAL]
    warnings = [r for r in result.recommendations if r.severity == Severity.WARNING]
    info = [r for r in result.recommendations if r.severity == Severity.INFO]
    fixable = [r for r in result.recommendations if r.fixable]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Criticos", len(critical))
    c2.metric("Advertencias", len(warnings))
    c3.metric("Informativos", len(info))
    c4.metric("Auto-fix Disponible", len(fixable))

    st.markdown("---")

    # Filter
    filter_severity = st.multiselect(
        "Filtrar por severidad",
        options=["critical", "warning", "info"],
        default=["critical", "warning", "info"],
        format_func=lambda x: {"critical": "Criticos", "warning": "Advertencias", "info": "Informativos"}[x],
    )

    show_fixable_only = st.checkbox("Solo mostrar con auto-fix disponible")

    # Render recommendations
    for rec in result.recommendations:
        severity_val = rec.severity.value if isinstance(rec.severity, Severity) else rec.severity
        if severity_val not in filter_severity:
            continue
        if show_fixable_only and not rec.fixable:
            continue
        render_recommendation(rec)
