"""Overview tab - score, summary and key metrics."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from core.models import AnalysisResult, ScoreCategory
from ui.components import render_score_gauge, render_metric_card


def render_overview_tab(result: AnalysisResult):
    """Render the overview tab content."""

    # Model warning FIRST (before metrics so user understands context)
    if not result.model_analysis_available:
        st.warning(
            f"**Modelo semantico no disponible:** {result.model_analysis_note} "
            f"Las metricas del modelo se muestran como '--'. "
            f"El analisis de reporte (paginas, visuals, diseno) funciona normalmente."
        )

    # Score and category
    col1, col2 = st.columns([1, 2])

    with col1:
        fig = render_score_gauge(result)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Resumen Ejecutivo")

        model_ok = result.model_analysis_available

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Paginas", result.total_pages,
                               _status_for("total_pages", result))
        with c2:
            render_metric_card("Visuals", result.total_visuals,
                               _status_for("visualizations_per_page", result))
        with c3:
            auto_count = getattr(result, "auto_date_time_tables_count", 0)
            tables_help = "Solo tablas del usuario (excl. LocalDateTable auto-datetime)."
            if auto_count > 0:
                tables_help += f" Hay {auto_count} tablas auto-datetime ocultas."
            render_metric_card("Tablas",
                               result.total_tables if model_ok else "--",
                               _status_for("tables_in_model", result),
                               help=tables_help)
        with c4:
            render_metric_card("Medidas",
                               result.total_measures if model_ok else "--",
                               _status_for("dax_measures_complex", result))

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            render_metric_card("Relaciones",
                               result.total_relationships if model_ok else "--",
                               _status_for("relationships", result))
        with c6:
            render_metric_card("Bidireccionales",
                               result.bidirectional_relationships if model_ok else "--",
                               _status_for("bidirectional_relationships", result))
        with c7:
            render_metric_card("Col. Calculadas",
                               result.calculated_columns if model_ok else "--",
                               _status_for("calculated_columns", result))
        with c8:
            render_metric_card("Custom Visuals", result.custom_visuals_count,
                               _status_for("custom_visuals", result))

    st.divider()

    # Visual types distribution
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Tipos de Visual")
        if result.visual_types:
            vt = dict(sorted(result.visual_types.items(), key=lambda x: -x[1]))
            fig = go.Figure(go.Bar(
                x=list(vt.values()),
                y=list(vt.keys()),
                orientation='h',
                marker_color='#F2C811',
                marker_line_width=0,
            ))
            fig.update_layout(
                height=max(200, len(vt) * 28),
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Cantidad",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Space Grotesk, DM Sans, sans-serif", color="#8B95A8"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se detectaron tipos de visual.")

    with col_b:
        st.markdown("#### Detalle por Pagina")
        if result.pages_detail:
            df = pd.DataFrame([
                {
                    "Pagina": p.name,
                    "Visuals": p.visuals_count,
                    "Filtros": p.filters_count,
                    "Tamano": f"{p.width}x{p.height}",
                    "Oculta": "Si" if p.hidden else "",
                    "Tooltip": "Si" if p.tooltip else "",
                }
                for p in result.pages_detail
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No se detectaron paginas.")

    # Design analysis
    st.markdown("#### Analisis de Diseno")
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Slicers", result.slicers_count)
    d2.metric("Botones", result.buttons_count)
    d3.metric("Shapes", result.shapes_count)
    d4.metric("Textboxes", result.textboxes_count)
    d5.metric("Bookmarks", result.bookmarks_count)

    d6, d7, d8, d9, d10 = st.columns(5)
    d6.metric("Pag. Ocultas", result.hidden_pages_count)
    d7.metric("Pag. Tooltip", result.tooltip_pages_count)
    d8.metric("Tema Custom", "Si" if result.has_custom_theme else "No")
    d9.metric("Imagenes", f"{round(result.embedded_images_mb, 1)} MB")
    d10.metric("Custom Vis.", result.custom_visuals_count)


def _status_for(metric_key: str, result: AnalysisResult) -> str:
    ms = result.metric_scores.get(metric_key)
    return ms.status if ms else "good"
