"""Tools tab — Delta Analyzer, Perspectives, Translations.

Consolidated advanced tools in a single tab with sub-navigation
to avoid information overload (ui-ux-pro-max: progressive disclosure).
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from core.models import AnalysisResult
from core.analyzers.delta_analyzer import (
    save_snapshot, list_snapshots, compare_snapshots,
)
from core.analyzers.model_manager import ModelManager
from core.aggregation_suggester import (
    scan_model, generate_recommendation, get_summary_stats
)


def render_tools_tab(result: AnalysisResult):
    """Render the advanced tools tab."""

    sub = st.tabs(["Delta Analyzer", "Aggregation Suggester", "Perspectives", "Translations"])

    with sub[0]:
        _render_delta(result)
    with sub[1]:
        _render_aggregation_suggester(result)
    with sub[2]:
        _render_perspectives(result)
    with sub[3]:
        _render_translations(result)


# ═══════════════════════════════════════════════════════════════════
#  DELTA ANALYZER
# ═══════════════════════════════════════════════════════════════════

def _render_delta(result: AnalysisResult):
    st.markdown("#### Delta Analyzer")
    st.caption(
        "Guarda snapshots del analisis y compara versiones para ver que cambio. "
        "Util para validar mejoras despues de aplicar fixes."
    )

    # Save snapshot
    col_save, col_space = st.columns([1, 3])
    with col_save:
        if st.button("Guardar Snapshot", use_container_width=True):
            path = save_snapshot(result)
            st.success(f"Snapshot guardado")

    # List snapshots
    snapshots = list_snapshots(result.report_path)

    if not snapshots:
        st.info("No hay snapshots guardados. Guarde uno para comenzar a comparar.")
        return

    st.markdown(f"**{len(snapshots)} snapshot(s) disponibles**")

    # Snapshot table
    snap_df = pd.DataFrame([
        {
            "Fecha": s["timestamp"][:19],
            "Score": s["score"],
            "Paginas": s["pages"],
            "Visuals": s["visuals"],
            "Tablas": s["tables"],
            "Medidas": s["measures"],
        }
        for s in snapshots[:10]
    ])
    st.dataframe(snap_df, use_container_width=True, hide_index=True)

    # Compare
    if len(snapshots) >= 2:
        st.markdown("##### Comparar")
        c1, c2 = st.columns(2)
        options = [f"{s['timestamp'][:19]} (score: {s['score']})" for s in snapshots]

        with c1:
            idx_a = st.selectbox("Snapshot anterior", range(len(options)),
                                 format_func=lambda i: options[i],
                                 index=min(1, len(options) - 1))
        with c2:
            idx_b = st.selectbox("Snapshot actual", range(len(options)),
                                 format_func=lambda i: options[i],
                                 index=0)

        if st.button("Comparar Snapshots"):
            if idx_a == idx_b:
                st.warning("Seleccione dos snapshots diferentes.")
            else:
                delta = compare_snapshots(snapshots[idx_a]["path"], snapshots[idx_b]["path"])
                _render_delta_result(delta)


def _render_delta_result(delta):
    """Render comparison results."""
    # Score change
    score_diff = delta.score_after - delta.score_before
    if score_diff > 0:
        st.success(f"Score: {delta.score_before:.1f} -> {delta.score_after:.1f} (+{score_diff:.1f})")
    elif score_diff < 0:
        st.error(f"Score: {delta.score_before:.1f} -> {delta.score_after:.1f} ({score_diff:.1f})")
    else:
        st.info(f"Score sin cambios: {delta.score_after:.1f}")

    # Summary
    s = delta.summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cambios", s["total"])
    c2.metric("Agregados", s["added"])
    c3.metric("Eliminados", s["removed"])
    c4.metric("Modificados", s["modified"])

    if not delta.changes:
        st.info("Sin cambios entre los snapshots.")
        return

    # Group by category
    by_cat = {}
    for c in delta.changes:
        by_cat.setdefault(c.category, []).append(c)

    cat_labels = {
        "score": "Score", "table": "Tablas", "measure": "Medidas",
        "relationship": "Relaciones", "page": "Paginas",
        "visual": "Visuals", "filter": "Filtros", "column": "Columnas",
    }

    for cat, changes in by_cat.items():
        with st.expander(f"{cat_labels.get(cat, cat)} ({len(changes)} cambios)"):
            for c in changes:
                icon = {"added": "+", "removed": "-", "modified": "~"}.get(c.change_type, "?")
                st.caption(f"  [{icon}] {c.name}: {c.detail}")


# ═══════════════════════════════════════════════════════════════════
#  AGGREGATION SUGGESTER
# ═══════════════════════════════════════════════════════════════════

def _render_aggregation_suggester(result: AnalysisResult):
    st.markdown("#### Aggregation Table Suggester")
    st.caption(
        "Detecta medidas DAX que generan tablas en memoria (SUMMARIZECOLUMNS, ADDCOLUMNS+VALUES, etc.) "
        "y recomienda convertirlas en tablas de agregación nativas para mejor performance."
    )

    if not result.model_analysis_available:
        st.info("⚠️ Requiere modelo semántico disponible (carpeta .SemanticModel).")
        return

    model_data = result._raw_model_data

    if not model_data:
        st.warning("No se pudo cargar el modelo semántico.")
        return

    # Scan model
    with st.spinner("Escaneando medidas DAX..."):
        candidates = scan_model(model_data)

    if not candidates:
        st.success("✅ No se detectaron medidas candidatas para agregación — el modelo está optimizado.")
        return

    # Summary stats
    stats = get_summary_stats(candidates)
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Candidatos totales", stats['total'])
    with c2:
        st.metric("Alta confianza", stats['by_confidence']['high'])
    with c3:
        st.metric("Confianza media", stats['by_confidence']['medium'])
    with c4:
        st.metric("Tablas afectadas", stats['affected_tables'])

    # Pattern breakdown
    st.markdown("**Patrones detectados:**")
    pattern_labels = {
        'SUMMARIZECOLUMNS': 'SUMMARIZECOLUMNS',
        'ADDCOLUMNS+VALUES': 'ADDCOLUMNS(VALUES(...))',
        'SUMMARIZE': 'SUMMARIZE',
        'GROUPBY': 'GROUPBY',
    }
    cols = st.columns(len(stats['by_pattern']))
    for i, (pattern, count) in enumerate(stats['by_pattern'].items()):
        with cols[i]:
            st.caption(f"{pattern_labels.get(pattern, pattern)}: **{count}**")

    st.markdown("---")

    # Candidates table
    st.markdown("#### Medidas candidatas")

    conf_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    df = pd.DataFrame([
        {
            '': conf_icons[c.confidence],
            'Medida': c.measure_name,
            'Tabla': c.table_name,
            'Patrón': c.pattern,
            'Confianza': c.confidence.upper(),
        }
        for c in candidates
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Details per candidate
    st.markdown("---")
    st.markdown("#### Detalle y recomendaciones")

    for i, c in enumerate(candidates[:10]):  # Show first 10
        icon = conf_icons[c.confidence]
        with st.expander(f"{icon} {c.measure_name} (Tabla: {c.table_name})"):
            st.caption(f"**Patrón detectado:** `{c.pattern}`")
            st.caption(f"**Confianza:** {c.confidence.upper()}")
            st.markdown(f"**Razón:** {c.reason}")

            st.markdown("**Fragmento DAX:**")
            st.code(c.match_snippet, language='dax')

            st.markdown("**Expresión completa:**")
            st.code(c.dax_expression, language='dax')

            # Recommendation
            rec = generate_recommendation(c)
            st.markdown(rec)

    if len(candidates) > 10:
        st.caption(f"Mostrando 10 de {len(candidates)} candidatos. Exportá el análisis completo para ver todos.")


# ═══════════════════════════════════════════════════════════════════
#  PERSPECTIVES
# ═══════════════════════════════════════════════════════════════════

def _render_perspectives(result: AnalysisResult):
    st.markdown("#### Perspectives")
    st.caption(
        "Las perspectivas permiten mostrar solo un subconjunto de tablas/medidas "
        "a distintos grupos de usuarios."
    )

    if not result.model_analysis_available:
        st.info("Requiere modelo semantico disponible.")
        return

    mgr = ModelManager(result._model_base_path)
    perspectives = mgr.list_perspectives()

    if perspectives:
        st.markdown(f"**{len(perspectives)} perspectiva(s) existentes**")
        for p in perspectives:
            with st.expander(f"{p.name} ({len(p.tables)} tablas)"):
                for t in p.tables:
                    cols = len(t.get("columns", []))
                    measures = len(t.get("measures", []))
                    st.caption(f"  {t['table']}: {cols} columnas, {measures} medidas")
    else:
        st.info("No hay perspectivas definidas en el modelo.")

    # Create new perspective
    st.markdown("##### Crear Perspectiva")

    model = result._raw_model_data
    model_data = model.get("model", model)
    all_tables = [
        t.get("name", "") for t in model_data.get("tables", [])
        if t.get("name", "") and not t.get("name", "").startswith("LocalDateTable_")
        and not t.get("name", "").startswith("DateTableTemplate_")
    ]

    if not all_tables:
        st.caption("No hay tablas disponibles.")
        return

    persp_name = st.text_input("Nombre de la perspectiva", placeholder="Vista Gerencial")
    selected_tables = st.multiselect("Tablas a incluir", all_tables)

    if st.button("Crear Perspectiva", disabled=not persp_name or not selected_tables):
        ok = mgr.create_perspective(persp_name, selected_tables)
        if ok:
            st.success(f"Perspectiva '{persp_name}' creada con {len(selected_tables)} tablas.")
        else:
            st.error("Error creando perspectiva.")


# ═══════════════════════════════════════════════════════════════════
#  TRANSLATIONS
# ═══════════════════════════════════════════════════════════════════

def _render_translations(result: AnalysisResult):
    st.markdown("#### Translations")
    st.caption(
        "Las traducciones permiten mostrar nombres de tablas, columnas y medidas "
        "en diferentes idiomas segun la configuracion regional del usuario."
    )

    if not result.model_analysis_available:
        st.info("Requiere modelo semantico disponible.")
        return

    mgr = ModelManager(result._model_base_path)
    translations = mgr.list_translations()

    if translations:
        st.markdown(f"**{len(translations)} idioma(s) configurado(s)**")
        for t in translations:
            tables_count = len(t.table_translations)
            cols_count = len(t.column_translations)
            measures_count = len(t.measure_translations)
            ling = " (con Q&A linguistic)" if t.has_linguistic else ""

            with st.expander(f"{t.culture}{ling}"):
                st.caption(f"Tablas traducidas: {tables_count} | Columnas: {cols_count} | Medidas: {measures_count}")

                if t.table_translations:
                    st.markdown("**Tablas:**")
                    for orig, trans in list(t.table_translations.items())[:20]:
                        st.caption(f"  {orig} -> {trans}")

                if t.column_translations:
                    st.markdown("**Columnas:**")
                    for orig, trans in list(t.column_translations.items())[:20]:
                        st.caption(f"  {orig} -> {trans}")
    else:
        st.info("No hay traducciones definidas en el modelo.")

    # Quick add translation
    st.markdown("##### Agregar Idioma")

    common_cultures = ["en-US", "es-AR", "es-ES", "pt-BR", "pt-PT", "fr-FR", "de-DE", "it-IT"]
    existing = {t.culture for t in translations}
    available = [c for c in common_cultures if c not in existing]

    if not available:
        available = ["otro"]

    culture = st.selectbox("Idioma", available)
    if culture == "otro":
        culture = st.text_input("Codigo de cultura", placeholder="ja-JP")

    if st.button("Crear archivo de traduccion", disabled=not culture):
        ok = mgr.create_translation(culture, {"tables": {}, "columns": {}, "measures": {}})
        if ok:
            st.success(
                f"Archivo de traduccion '{culture}' creado. "
                f"Edite el archivo .tmdl para agregar traducciones."
            )
        else:
            st.error("Error creando traduccion.")
