"""UI components for Power BI Fixer — Design System v3.0
Uses native Streamlit elements + minimal HTML for branding.
No emojis as UI icons — uses CSS-styled indicators.
"""

import streamlit as st
import plotly.graph_objects as go

from core.models import AnalysisResult, ScoreCategory, Severity


def render_header():
    """Render app header with YPF branding."""
    st.markdown("""
    <div class="app-header">
        <h1><span class="highlight">Power BI</span> Fixer</h1>
        <p>Analiza, detecta y corrige problemas en reportes Power BI</p>
    </div>
    """, unsafe_allow_html=True)


def render_score_gauge(result: AnalysisResult) -> go.Figure:
    """Create a modern score gauge — dark theme, minimal chrome."""
    score = result.overall_score
    category = result.score_category

    color_map = {
        ScoreCategory.EXCELLENT: "#34D399",
        ScoreCategory.GOOD: "#60A5FA",
        ScoreCategory.WARNING: "#FBBF24",
        ScoreCategory.POOR: "#F87171",
    }
    color = color_map.get(category, "#63636B")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={
            "suffix": "/100",
            "font": {"size": 38, "family": "Space Grotesk, DM Sans, sans-serif", "color": "#E8ECF4"},
        },
        title={
            "text": f"<b>{category.value}</b>",
            "font": {"size": 16, "family": "Space Grotesk, DM Sans, sans-serif", "color": "#8B95A8"},
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#252D3D",
                "dtick": 25,
                "tickfont": {"color": "#5A6478", "size": 10},
            },
            "bar": {"color": color, "thickness": 0.7},
            "bgcolor": "#181D2A",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "rgba(209, 52, 56, 0.06)"},
                {"range": [60, 75], "color": "rgba(245, 158, 11, 0.06)"},
                {"range": [75, 90], "color": "rgba(0, 120, 212, 0.06)"},
                {"range": [90, 100], "color": "rgba(16, 185, 129, 0.06)"},
            ],
            "threshold": {
                "line": {"color": "#E8ECF4", "width": 2},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Sans, sans-serif"},
    )
    return fig


def render_metric_card(label: str, value, status: str = "good", help: str | None = None):
    """Render a metric using native Streamlit."""
    st.metric(label=label, value=value, help=help)


def render_recommendation(rec):
    """Render a recommendation using native Streamlit alerts."""
    severity = rec.severity.value if isinstance(rec.severity, Severity) else rec.severity

    severity_label = {"critical": "CRITICO", "warning": "AVISO", "info": "INFO"}.get(severity, "")
    fixable_text = " | Auto-fix disponible" if rec.fixable else ""

    msg = f"**{severity_label}** {rec.message}{fixable_text}\n\n`Actual: {rec.current_value}` | `Objetivo: {rec.target_value}`"

    if severity == "critical":
        st.error(msg)
    elif severity == "warning":
        st.warning(msg)
    else:
        st.info(msg)


def render_summary_metrics(result: AnalysisResult):
    """Render sidebar summary — clean metrics layout."""
    st.sidebar.markdown("#### Resumen del Analisis")
    st.sidebar.divider()

    metrics = [
        ("Paginas", result.total_pages, None),
        ("Visuals", result.total_visuals, None),
        ("Tablas", result.total_tables,
         "Solo tablas del usuario. Excluye LocalDateTable_* auto-generadas."),
        ("Medidas", result.total_measures, None),
        ("Relaciones", result.total_relationships, None),
    ]

    for label, value, tip in metrics:
        st.sidebar.metric(label, value, help=tip)

    # Indicador de Auto Date/Time en sidebar si está activo
    auto_count = getattr(result, "auto_date_time_tables_count", 0)
    if auto_count > 0:
        st.sidebar.caption(
            f"+ {auto_count} tablas auto-datetime ocultas"
        )

    st.sidebar.divider()

    critical = sum(1 for r in result.recommendations if r.severity == Severity.CRITICAL)
    warning = sum(1 for r in result.recommendations if r.severity == Severity.WARNING)
    info = sum(1 for r in result.recommendations if r.severity == Severity.INFO)

    # Auto-fix count: prefer live FixerEngine scan from session_state when
    # available so the sidebar matches the Auto-Fix tab card. Fall back to
    # recommendation.fixable before the user runs a scan.
    scan_key = f"scan_{result.report_path}"
    scans = st.session_state.get(scan_key)
    if scans is not None:
        fixable = sum(
            1 for s in scans
            if s.issues_found > 0 and not getattr(s, "is_manual", False)
        )
    else:
        fixable = sum(1 for r in result.recommendations if r.fixable)

    st.sidebar.markdown("#### Problemas")

    if critical:
        st.sidebar.error(f"Criticos: {critical}")
    if warning:
        st.sidebar.warning(f"Advertencias: {warning}")
    if info:
        st.sidebar.info(f"Informativos: {info}")

    if fixable:
        st.sidebar.divider()
        st.sidebar.success(f"**{fixable}** con auto-fix disponible")


def render_feature_card(icon_letter: str, title: str, description: str):
    """Render a feature card — uses CSS icon instead of emoji."""
    st.markdown(f"""
    <div class="feature-card">
        <div class="feature-icon">{icon_letter}</div>
        <h4>{title}</h4>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)
