"""Home — Dashboard con feature cards + estado del proyecto cargado."""

import streamlit as st

from shared.loader import get_project


def render(logger):
    """Render home dashboard."""

    st.markdown(
        '<h1 class="main-header">PBI <span style="color: #F2C811;">Hub</span></h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Suite integrada de análisis, corrección '
        'y optimización de proyectos Power BI.</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Project status ───────────────────────────────────────────────
    project = get_project()

    if project is not None:
        st.markdown("### 📊 Proyecto activo")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Score", f"{project.overall_score:.0f}/100")
        with c2:
            st.metric("Páginas", project.total_pages)
        with c3:
            st.metric("Visuales", project.total_visuals)
        with c4:
            n = project.total_measures if project.model_analysis_available else "--"
            st.metric("Medidas DAX", n)

        st.caption(f"📁 `{project.report_name}` · Tipo: {project.file_type.value}")

        st.markdown("---")
        st.markdown("### 🚀 Acciones rápidas")

        c1, c2 = st.columns(2)
        with c1:
            st.info(
                "**🔍 Analyzer** — ver score, métricas detalladas y "
                "recomendaciones priorizadas del proyecto."
            )
        with c2:
            st.info(
                "**🔧 Auto-Fixer** — aplicar correcciones automáticas "
                "(37 fixers disponibles) sin abrir Power BI Desktop."
            )
    else:
        st.info(
            "👈 **Cargá un proyecto PBIP desde el sidebar** para comenzar. "
            "Todos los módulos usarán el mismo proyecto."
        )

    st.markdown("---")

    # ── Modules overview ─────────────────────────────────────────────
    st.markdown("### 🧩 Módulos disponibles")

    _render_module_card(
        "🔍 Analyzer",
        "Análisis completo del proyecto: score, métricas, recomendaciones.",
        ["Score 0-100 basado en 60+ reglas BPA", "Métricas de reporte y modelo",
         "Recomendaciones priorizadas por severidad"],
        available=True,
    )

    _render_module_card(
        "🔧 Auto-Fixer",
        "Corrección automática de 37 problemas comunes sin abrir Desktop.",
        ["11 fixers de reporte", "10 fixers de modelo", "16 fixers BPA"],
        available=True,
    )

    _render_module_card(
        "⚡ DAX Optimizer",
        "Ranking de medidas DAX por complejidad y riesgo con recomendaciones.",
        ["Score de complejidad por medida", "Detección de patrones costosos",
         "Visualizaciones de análisis"],
        available=True,
    )

    _render_module_card(
        "📈 Performance Analyzer",
        "Parser de exports JSON del Performance Analyzer de Power BI Desktop.",
        ["Ranking de visuales por tiempo", "Separación DAX/Render/Other",
         "Recomendaciones priorizadas P0-P3"],
        available=True,
    )

    _render_module_card(
        "🎯 DAX Benchmarker",
        "Ejecución estadística de queries DAX con análisis de performance.",
        ["Percentiles p50/p95/p99", "Detección de outliers y cold cache",
         "Box plot y histograma de distribución"],
        available=True,
    )

    st.markdown("---")
    st.markdown("### 📅 Módulos próximos")

    coming = [
        ("📄 Documentation Generator", "Doc .docx técnico-funcional automática"),
        ("🎨 Layout Organizer", "Reorganización del diagrama del modelo"),
        ("🛠️ Tools", "Delta Analyzer, Aggregation Suggester, Perspectives, Translations"),
        ("💾 Memory Estimator", "Proyección de tamaño VertiPaq"),
        ("📊 Usage Dashboard", "Métricas de uso de la suite (admin)"),
    ]

    for name, desc in coming:
        st.caption(f"**{name}** — {desc}")


def _render_module_card(title, description, features, available=True):
    """Render a module feature card."""
    badge = "✅ Disponible" if available else "🔜 Próximamente"
    color = "#107C10" if available else "#5A6478"

    features_html = "".join(f"<li>{f}</li>" for f in features)

    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; padding: 1.25rem; margin-bottom: 0.75rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <h3 style="margin: 0; color: #E8ECF4; font-family: 'Space Grotesk', sans-serif;">
                {title}
            </h3>
            <span style="background: {color}22; color: {color}; padding: 0.2rem 0.6rem;
                         border-radius: 4px; font-size: 0.7rem; font-weight: 600;">
                {badge}
            </span>
        </div>
        <p style="color: #8B95A8; margin: 0.5rem 0;">{description}</p>
        <ul style="color: #B8C0D0; font-size: 0.85rem; margin: 0.5rem 0 0 1rem;">
            {features_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)
