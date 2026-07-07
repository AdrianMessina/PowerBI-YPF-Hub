"""Storage Mode tab — Import/DirectQuery analysis + DirectQuery validation.

Renderiza:
- Distribución de tablas por storage mode (Import/DirectQuery/Dual)
- Storage mode type del modelo (Import puro / DQ puro / Composite)
- Detalle de tablas DirectQuery con snippet de source
- Issues críticos: columnas calculadas en DQ, funciones no soportadas
- Anti-patterns de query folding en M code
"""

import streamlit as st

from core.models import AnalysisResult


MODE_ICONS = {
    "import": "📦",
    "directQuery": "🔗",
    "dual": "🔄",
}

MODE_LABELS = {
    "import": "Import",
    "directQuery": "DirectQuery",
    "dual": "Dual",
}

MODE_DESCRIPTIONS = {
    "import": "Datos cargados en memoria VertiPaq — máxima performance, refresh programado.",
    "directQuery": "Queries al origen en tiempo real — datos frescos, latencia 3-10× mayor.",
    "dual": "Import + DirectQuery según contexto — usado en modelos Composite.",
}

STORAGE_TYPE_LABELS = {
    "import": ("📦 Import puro", "#107C10"),
    "directQuery": ("🔗 DirectQuery puro", "#F59E0B"),
    "composite": ("🔀 Composite Model", "#3B82F6"),
}


def render_storage_mode_tab(result: AnalysisResult):
    """Render Storage Mode analysis tab."""

    if not result.model_analysis_available:
        st.warning(
            "**Modelo semántico no disponible.** El análisis de storage mode "
            "requiere acceso al modelo (PBIP con TMDL). Si estás analizando un "
            "PBIX empaquetado, subí el proyecto en formato PBIP."
        )
        return

    tables_by_mode = result.tables_by_mode or {"import": 0, "directQuery": 0, "dual": 0}
    total_tables = sum(tables_by_mode.values())

    if total_tables == 0:
        st.info("No se detectaron tablas de usuario para analizar storage mode.")
        return

    # ── Header: storage mode type del modelo ───────────────────────
    stype = result.storage_mode_type or "import"
    label, color = STORAGE_TYPE_LABELS.get(stype, ("? Desconocido", "#5A6478"))

    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
                border-left: 4px solid {color}; border-radius: 8px;
                padding: 1.1rem 1.35rem; margin: 0.5rem 0 1.25rem;">
        <div style="color: #94A3B8; font-family: 'Fira Sans', sans-serif; font-size: 0.78rem;
                    font-weight: 600; letter-spacing: 0.08em; margin-bottom: 0.35rem;">
            ARQUITECTURA DEL MODELO
        </div>
        <div style="color: #F1F5F9; font-family: 'Fira Sans', sans-serif; font-size: 1.35rem;
                    font-weight: 700; letter-spacing: -0.02em;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Distribución por mode ──────────────────────────────────────
    st.markdown("#### Distribución de tablas por storage mode")

    c1, c2, c3 = st.columns(3)
    for col, mode in [(c1, "import"), (c2, "directQuery"), (c3, "dual")]:
        n = tables_by_mode.get(mode, 0)
        pct = (n / total_tables * 100) if total_tables else 0
        with col:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
                        border-radius: 8px; padding: 1rem 1.15rem; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 0.15rem;">{MODE_ICONS[mode]}</div>
                <div style="color: #94A3B8; font-family: 'Fira Sans', sans-serif; font-size: 0.75rem;
                            font-weight: 600; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                    {MODE_LABELS[mode].upper()}
                </div>
                <div style="color: #F1F5F9; font-family: 'Fira Sans', sans-serif; font-size: 2rem;
                            font-weight: 700; line-height: 1;">
                    {n}
                </div>
                <div style="color: #CBD5E1; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem;
                            margin-top: 0.25rem;">
                    {pct:.0f}% del modelo
                </div>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("ℹ️ ¿Qué significa cada storage mode?", expanded=False):
        for mode in ("import", "directQuery", "dual"):
            st.markdown(f"""
**{MODE_ICONS[mode]} {MODE_LABELS[mode]}** — {MODE_DESCRIPTIONS[mode]}
            """)

    st.markdown("---")

    # ── DirectQuery tables detail ──────────────────────────────────
    if result.directquery_tables_detail:
        st.markdown("#### 🔗 Tablas DirectQuery / Dual")
        st.caption(
            "Estas tablas consultan el origen en tiempo real. Cualquier degradación "
            "del source impacta directo al usuario final."
        )

        for t in result.directquery_tables_detail:
            n_calc = t.get("n_calculated_columns", 0)
            calc_badge = ""
            if n_calc > 0:
                calc_badge = (
                    f'<span style="background: rgba(209,52,56,0.15); color: #FCA5A5;'
                    f' padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;'
                    f' font-weight: 600; margin-left: 0.5rem;">'
                    f'❌ {n_calc} col. calculada(s)</span>'
                )

            mode_badge = (
                f'<span style="background: rgba(59,130,246,0.15); color: #93C5FD;'
                f' padding: 2px 8px; border-radius: 4px; font-size: 0.72rem;'
                f' font-family: Fira Code, monospace;">{MODE_LABELS[t["mode"]]}</span>'
            )

            with st.expander(f"{MODE_ICONS[t['mode']]} {t['name']}"):
                st.markdown(
                    f"**{t['name']}** {mode_badge} {calc_badge}",
                    unsafe_allow_html=True,
                )
                if t.get("source_snippet"):
                    st.caption("Source (primeras líneas):")
                    st.code(t["source_snippet"], language="powerquery")
                else:
                    st.caption("_Sin snippet de source disponible._")

        st.markdown("---")

    # ── DirectQuery issues (críticos + warnings) ───────────────────
    critical = [i for i in (result.directquery_issues or []) if i.get("severity") == "critical"]
    warnings = [i for i in (result.directquery_issues or []) if i.get("severity") == "warning"]

    if critical or warnings:
        st.markdown("#### ⚠️ Validación DirectQuery")

        if critical:
            st.markdown(f"""
            <div style="background: rgba(209,52,56,0.10); border: 1px solid rgba(209,52,56,0.30);
                        border-left: 3px solid #D13438; border-radius: 6px;
                        padding: 0.85rem 1.15rem; margin: 0.75rem 0;">
                <div style="color: #FCA5A5; font-family: 'Fira Sans', sans-serif; font-weight: 700;
                            font-size: 0.9rem; margin-bottom: 0.35rem;">
                    🔴 {len(critical)} error(es) crítico(s)
                </div>
                <div style="color: #E8ECF4; font-family: 'Fira Sans', sans-serif; font-size: 0.85rem;">
                    Estos problemas rompen el modelo o degradan performance dramáticamente.
                </div>
            </div>
            """, unsafe_allow_html=True)

            for i, iss in enumerate(critical[:20], 1):
                col = iss.get("column", "")
                loc = f"`{iss['table']}`" + (f" · `{col}`" if col else "")
                st.markdown(f"**{i}. {iss['issue']}** — {loc}")
                st.caption(iss.get("detail", ""))
                st.markdown("")

        if warnings:
            with st.expander(f"🟡 {len(warnings)} warning(s) — funciones DAX de soporte limitado"):
                for i, iss in enumerate(warnings[:30], 1):
                    col = iss.get("column", "")
                    loc = f"`{iss['table']}`" + (f" · `{col}`" if col else "")
                    st.markdown(f"**{i}. {iss['issue']}** — {loc}")
                    st.caption(iss.get("detail", ""))
                    st.markdown("")

        st.markdown("---")

    # ── Query folding warnings ─────────────────────────────────────
    if result.query_folding_warnings:
        st.markdown("#### 🔎 Query Folding — anti-patterns detectados")
        st.caption(
            "Detectamos operaciones M que rompen query folding. "
            "En DirectQuery esto es **crítico**: fuerza a materializar toda la tabla."
        )

        for i, w in enumerate(result.query_folding_warnings[:20], 1):
            st.markdown(f"**{i}. {w['antipattern']}** — tabla `{w['table']}`")
            if w.get("snippet"):
                st.code(w["snippet"], language="powerquery")

        st.markdown("---")

    # ── Guidance para modelos Import puros (composite suggestion) ───
    if stype == "import" and total_tables > 15:
        st.markdown("#### 💡 Sugerencia arquitectural")
        st.markdown(f"""
        <div style="background: rgba(4,81,228,0.08); border: 1px solid rgba(4,81,228,0.20);
                    border-radius: 6px; padding: 0.85rem 1.15rem; margin: 0.75rem 0;
                    color: #CBD5E1; font-family: 'Fira Sans', sans-serif; font-size: 0.85rem;">
            Modelo <strong style="color: #F1F5F9;">Import puro con {total_tables} tablas</strong>.
            Si el volumen crece o necesitás datos en tiempo real, considerá un
            <strong style="color: #F1F5F9;">Composite Model</strong>: dimensiones en Import
            (filtros instantáneos) + hechos en DirectQuery (datos frescos).
        </div>
        """, unsafe_allow_html=True)

    # ── Todo OK ────────────────────────────────────────────────────
    if not result.directquery_tables_detail and not result.directquery_issues \
            and not result.query_folding_warnings:
        st.markdown("""
        <div style="background: rgba(16,124,16,0.10); border: 1px solid rgba(16,124,16,0.25);
                    border-left: 3px solid #107C10; border-radius: 6px;
                    padding: 0.9rem 1.15rem; margin: 0.75rem 0;">
            <div style="color: #86EFAC; font-family: 'Fira Sans', sans-serif; font-weight: 700;
                        font-size: 0.9rem; margin-bottom: 0.25rem;">
                ✓ Storage mode saludable
            </div>
            <div style="color: #CBD5E1; font-family: 'Fira Sans', sans-serif; font-size: 0.85rem;">
                Modelo Import puro sin issues de DirectQuery ni anti-patterns de query folding.
            </div>
        </div>
        """, unsafe_allow_html=True)
