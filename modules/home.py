"""Home — Dashboard con feature cards + estado del proyecto cargado."""

import streamlit as st

from shared.loader import get_project


def render(logger):
    """Render home dashboard."""

    # Title + subtitle with more prominence
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0 2rem;">
        <h1 style="font-family: 'Fira Sans', sans-serif; font-size: 2.8rem; font-weight: 800;
                   color: #E8ECF4; margin: 0 0 1rem; letter-spacing: -0.04em; line-height: 1.1;">
            PBI <span style="color: #0451E4;">Hub</span>
        </h1>
        <p style="font-family: 'Fira Sans', sans-serif; font-size: 1.15rem; font-weight: 400;
                  color: #CBD5E1; margin: 0; line-height: 1.6; max-width: 700px; margin: 0 auto;">
            Suite integrada de análisis, corrección y optimización de proyectos Power BI.
        </p>
    </div>
    """, unsafe_allow_html=True)

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

    _render_module_card(
        "📄 Documentation Generator",
        "Generación automática de documentación técnica-funcional en Word.",
        ["Template corporativo YPF", "Diagrama ER automático",
         "Campos autocompletados desde PBIP"],
        available=True,
    )

    _render_module_card(
        "🎨 Layout Organizer",
        "Organización automática del diagrama del modelo (star/grid layouts).",
        ["Star y Grid layouts", "Detección de snowflake dimensions",
         "Creación de tabs focalizados"],
        available=True,
    )

    _render_module_card(
        "🛠️ Tools",
        "Herramientas avanzadas de análisis y gestión del modelo.",
        ["Delta Analyzer (snapshots)", "Aggregation Suggester",
         "Perspectives + Translations"],
        available=True,
    )

    _render_module_card(
        "💾 Memory Estimator",
        "Proyección del tamaño del modelo VertiPaq en memoria.",
        ["Estimación por tabla/columna", "Impacto de tipos de datos",
         "Recomendaciones de compresión"],
        available=True,
    )

    _render_module_card(
        "📊 Usage Dashboard",
        "Métricas de uso de la suite (eventos, usuarios, apps más usadas).",
        ["Tracking de eventos por usuario", "Métricas de uso por módulo",
         "Análisis temporal"],
        available=True,
    )

    st.markdown("---")
    st.caption(
        "**🎉 Suite completa** — 11 módulos disponibles. "
        "Todos los módulos comparten el proyecto cargado en el sidebar."
    )


def _render_module_card(title, description, features, available=True):
    """Render a module feature card."""
    badge = "✅ Disponible" if available else "🔜 Próximamente"
    color = "#107C10" if available else "#5A6478"

    features_html = "".join(f"<li>{f}</li>" for f in features)

    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px; padding: 1.5rem; margin-bottom: 0.85rem;
                transition: all 0.2s ease; cursor: default;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
            <h3 style="margin: 0; color: #F1F5F9; font-family: 'Fira Sans', sans-serif;
                       font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em;">
                {title}
            </h3>
            <span style="background: {color}30; color: {color}; padding: 0.3rem 0.7rem;
                         border-radius: 5px; font-size: 0.72rem; font-weight: 700;
                         font-family: 'Fira Code', monospace; letter-spacing: 0.05em;">
                {badge}
            </span>
        </div>
        <p style="color: #CBD5E1; margin: 0.5rem 0 0.75rem; line-height: 1.55;
                  font-family: 'Fira Sans', sans-serif;">{description}</p>
        <ul style="color: #94A3B8; font-size: 0.88rem; margin: 0.5rem 0 0 1.25rem;
                   line-height: 1.65; font-family: 'Fira Sans', sans-serif;">
            {features_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)
