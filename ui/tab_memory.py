"""Memory estimation tab - analyze model memory consumption."""

import streamlit as st
import pandas as pd

from core.models import AnalysisResult
from core.analyzers.memory_estimator import MemoryEstimator


def render_memory_tab(result: AnalysisResult):
    """Render the memory estimation tab."""

    if not result.model_analysis_available:
        st.info(
            "El analisis de memoria requiere acceso al modelo semantico. "
            "Este reporte no tiene modelo disponible."
        )
        return

    estimator = MemoryEstimator(result)
    estimation = estimator.estimate()

    if not estimation.tables:
        st.info("No se encontraron tablas para estimar memoria.")
        return

    # ── Summary metrics ─────────────────────────────────────────
    st.markdown("#### Estimacion de Memoria del Modelo")
    st.caption(
        "Estimacion heuristica basada en tipos de datos y estructura del modelo. "
        "Para valores exactos use DAX Studio (VertiPaq Analyzer)."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Memoria Estimada", f"{estimation.total_estimated_mb:.1f} MB")

    # Para PBIP no hay tamaño "en disco" real - solo metadatos TMDL
    is_pbip_metadata = getattr(result, "model_size_source", "") == "pbip_metadata_only"
    if is_pbip_metadata or estimation.model_size_mb <= 0:
        c2.metric(
            "Modelo en Disco",
            "N/A",
            help=(
                "PBIP solo contiene metadatos (TMDL). "
                "El tamano real del modelo (datos comprimidos VertiPaq) "
                "solo se puede ver en Power BI Service o Desktop."
            ),
        )
    else:
        c2.metric(
            "Modelo en Disco",
            f"{estimation.model_size_mb:.1f} MB",
            help="Tamano del modelo comprimido (PBIX archivo .zip)",
        )

    c3.metric(
        "Tablas",
        len(estimation.tables),
        help="Solo tablas del usuario (excluye Auto Date/Time).",
    )
    c4.metric(
        "Ratio Compresion",
        f"{estimation.compression_ratio:.1f}x" if estimation.compression_ratio else "N/A",
    )

    st.divider()

    # ── Tables breakdown ────────────────────────────────────────
    st.markdown("##### Memoria por Tabla")

    table_data = []
    for t in estimation.tables:
        table_data.append({
            "Tabla": t.name,
            "Columnas": t.column_count,
            "Filas Est.": f"{t.estimated_rows:,}",
            "Memoria (MB)": t.estimated_mb,
            "Tipo": "Calculada" if t.is_calculated else "Import",
        })

    if table_data:
        df_tables = pd.DataFrame(table_data)
        st.dataframe(
            df_tables,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Memoria (MB)": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=max(t.estimated_mb for t in estimation.tables) or 1,
                    format="%.2f MB",
                ),
            },
        )

    st.divider()

    # ── Top columns ─────────────────────────────────────────────
    st.markdown("##### Top 20 Columnas por Memoria")

    col_data = []
    for c in estimation.top_columns:
        col_data.append({
            "Tabla": c.table,
            "Columna": c.column,
            "Tipo": c.data_type,
            "Memoria (MB)": c.estimated_mb,
            "Calculada": "Si" if c.is_calculated else "No",
            "Key": "Si" if c.is_key else "No",
        })

    if col_data:
        df_cols = pd.DataFrame(col_data)
        st.dataframe(
            df_cols,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Memoria (MB)": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=max(c.estimated_mb for c in estimation.top_columns) or 1,
                    format="%.2f MB",
                ),
            },
        )

    # ── Recommendations ─────────────────────────────────────────
    if estimation.recommendations:
        st.divider()
        st.markdown("##### Recomendaciones de Optimizacion")
        for rec in estimation.recommendations:
            st.warning(rec)
