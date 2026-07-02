"""Detailed metrics tab - deep dive into all metrics."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.models import AnalysisResult


def render_metrics_tab(result: AnalysisResult):
    """Render the detailed metrics tab."""

    sub_tabs = st.tabs([
        "Modelo de Datos", "Medidas DAX", "Relaciones", "Visualizaciones"
    ])

    with sub_tabs[0]:
        _render_model_metrics(result)
    with sub_tabs[1]:
        _render_dax_metrics(result)
    with sub_tabs[2]:
        _render_relationship_metrics(result)
    with sub_tabs[3]:
        _render_visual_metrics(result)


def _render_model_metrics(result: AnalysisResult):
    """Model data metrics."""
    if not result.model_analysis_available:
        st.warning("Analisis del modelo no disponible. Use formato PBIP para analisis completo.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Tablas",
        result.total_tables,
        help="Solo tablas creadas por el usuario. Excluye tablas automaticas de Auto Date/Time."
    )
    c2.metric("Columnas", result.total_columns)
    c3.metric("Col. Calculadas", result.calculated_columns)
    c4.metric("Tablas Calculadas", result.calculated_tables)

    # Desglose de tablas por tipo (transparencia para el usuario)
    tables_by_type = getattr(result, "tables_by_type", {}) or {}
    if tables_by_type:
        with st.expander("Desglose de tablas por tipo"):
            user_count = tables_by_type.get("user", 0)
            calc_count = tables_by_type.get("calculated", 0)
            auto_local = tables_by_type.get("auto_datetime_local", 0)
            auto_template = tables_by_type.get("auto_datetime_template", 0)
            sys_hidden = tables_by_type.get("system_hidden", 0)
            total_tmdl = user_count + calc_count + auto_local + auto_template + sys_hidden

            st.markdown(f"""
**Contabilizadas ({result.total_tables}):**
- {user_count} de datos (Import / DirectQuery)
- {calc_count} calculadas (DAX)

**Excluidas (auto-generadas por Power BI):**
- {auto_template} DateTableTemplate
- {auto_local} LocalDateTable (una por cada columna de fecha cuando Auto Date/Time esta activo)
- {sys_hidden} ocultas del sistema

**Total fisico en TMDL:** {total_tmdl} archivos `.tmdl`
            """)

    # Columns by table
    if result.columns_by_table:
        st.markdown("##### Columnas por Tabla")
        df = pd.DataFrame([
            {"Tabla": t, "Columnas": c}
            for t, c in sorted(result.columns_by_table.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Calculated columns detail
    if result.calculated_columns_detail:
        st.markdown("##### Columnas Calculadas")
        df = pd.DataFrame(result.calculated_columns_detail)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Threshold comparison - en PBIP el model_size_mb no esta disponible
    st.markdown("##### Comparacion con Umbrales")
    is_pbip_metadata = getattr(result, "model_size_source", "") == "pbip_metadata_only"
    metric_keys = ["tables_in_model", "calculated_columns"]
    if not is_pbip_metadata:
        metric_keys.append("model_size_mb")
    _render_threshold_chart(result, metric_keys)

    if is_pbip_metadata:
        st.caption(
            "Tamano del modelo no disponible para PBIP (solo metadatos). "
            "Verifica el tamano real en Power BI Service."
        )


def _render_dax_metrics(result: AnalysisResult):
    """DAX measures metrics."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Medidas", result.total_measures)
    c2.metric("Medidas Complejas", result.complex_dax_measures)

    auto_count = getattr(result, "auto_date_time_tables_count", 0)
    if result.auto_date_time_enabled:
        c3.metric(
            "Auto Date/Time",
            "Habilitado",
            delta=f"{auto_count} tablas auto" if auto_count else None,
            delta_color="inverse",
            help=(
                "Power BI genera tablas ocultas LocalDateTable_* por cada columna de fecha. "
                "Recomendado: deshabilitar y usar una tabla de calendario explicita."
            ),
        )
    else:
        c3.metric("Auto Date/Time", "Deshabilitado")

    # Measures by table
    if result.measures_by_table:
        st.markdown("##### Medidas por Tabla")
        table_data = [
            {"Tabla": t, "Cantidad": len(m), "Medidas": ", ".join(m[:5]) + ("..." if len(m) > 5 else "")}
            for t, m in sorted(result.measures_by_table.items(), key=lambda x: -len(x[1]))
            if m
        ]
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Measures without description
    no_desc = [m for m in result.measures_detail if not m.description]
    if no_desc:
        with st.expander(f"Medidas sin descripcion ({len(no_desc)})"):
            df = pd.DataFrame([
                {"Tabla": m.table, "Medida": m.name}
                for m in no_desc[:50]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Complex measures list
    complex_m = [m for m in result.measures_detail if _is_complex(m.expression)]
    if complex_m:
        with st.expander(f"Medidas complejas ({len(complex_m)})"):
            df = pd.DataFrame([
                {"Tabla": m.table, "Medida": m.name,
                 "Largo Expr.": len(m.expression)}
                for m in complex_m[:50]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)


def _render_relationship_metrics(result: AnalysisResult):
    """Relationships metrics."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Relaciones", result.total_relationships)
    c2.metric("Bidireccionales", result.bidirectional_relationships)
    inactive = sum(1 for r in result.relationships_detail if not r.is_active)
    c3.metric("Inactivas", inactive)

    if result.relationships_detail:
        st.markdown("##### Todas las Relaciones")
        df = pd.DataFrame([
            {
                "Desde": f"{r.from_table}.{r.from_column}",
                "Hacia": f"{r.to_table}.{r.to_column}",
                "Bidireccional": "Si" if r.is_bidirectional else "No",
                "Activa": "Si" if r.is_active else "No",
            }
            for r in result.relationships_detail
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

    if result.bidirectional_relationships_detail:
        st.markdown("##### Relaciones Bidireccionales")
        st.warning(
            "Las relaciones bidireccionales pueden causar ambiguedad en las consultas "
            "y degradar el rendimiento. Considere cambiarlas a unidireccionales."
        )
        for bidi in result.bidirectional_relationships_detail:
            st.markdown(f"- `{bidi['from']}` <-> `{bidi['to']}`")


def _render_visual_metrics(result: AnalysisResult):
    """Visual metrics."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Visuals", result.total_visuals)
    c2.metric("Prom. por Pagina", result.avg_visuals_per_page)
    c3.metric("Max en Pagina", f"{result.max_visuals_per_page} ({result.max_visuals_page_name})")
    c4.metric("Filtros Max", f"{result.max_filters_per_page} ({result.max_filters_page_name})")

    # Visual types breakdown
    if result.visual_types:
        st.markdown("##### Distribucion de Tipos de Visual")
        df = pd.DataFrame([
            {"Tipo": k, "Cantidad": v}
            for k, v in sorted(result.visual_types.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Custom visuals
    if result.custom_visuals_list:
        st.markdown("##### Custom Visuals")
        for cv in result.custom_visuals_list:
            st.markdown(f"- `{cv}`")

    # Embedded images
    if result.embedded_images_list:
        st.markdown(f"##### Imagenes Embebidas ({result.embedded_images_mb:.1f} MB total)")
        df = pd.DataFrame([
            {"Nombre": img["name"], "Tamano (KB)": f"{img['size_kb']:.1f}"}
            for img in result.embedded_images_list
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


def _render_threshold_chart(result: AnalysisResult, metric_keys: list):
    """Render a bar chart comparing values to thresholds."""
    labels = []
    values = []
    thresholds_good = []
    thresholds_warn = []

    for key in metric_keys:
        ms = result.metric_scores.get(key)
        if not ms:
            continue
        labels.append(key.replace("_", " ").title())
        values.append(ms.value)
        thresholds_good.append(ms.threshold_good)
        thresholds_warn.append(ms.threshold_warning)

    if not labels:
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Actual", x=labels, y=values, marker_color="#F2C811"))
    fig.add_trace(go.Bar(name="Umbral Bueno", x=labels, y=thresholds_good, marker_color="#10B981", opacity=0.5))
    fig.add_trace(go.Bar(name="Umbral Advertencia", x=labels, y=thresholds_warn, marker_color="#F59E0B", opacity=0.5))
    fig.update_layout(
        barmode="group", height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk, DM Sans, sans-serif", color="#8B95A8"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _is_complex(expression: str) -> bool:
    if not expression:
        return False
    expr_upper = expression.upper()
    return any(kw in expr_upper for kw in [
        "VAR ", "CALCULATE(", "CALCULATETABLE(", "SUMX(", "FILTER(",
    ])
