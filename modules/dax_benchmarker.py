"""DAX Benchmarker — ejecución estadística de queries DAX con análisis de performance.

Permite ejecutar una query DAX N veces, mide tiempos, calcula percentiles,
detecta outliers, y genera recomendaciones basadas en distribución estadística.

Workflow:
  1. Usuario pega query DAX
  2. Configura N iteraciones (default: 20)
  3. Click "Benchmark" → ejecuta N veces
  4. Muestra: box plot, percentiles, outliers, stats, recomendaciones
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from apps_core.dax_benchmarker_core.executor import (
    execute_dax_query, check_pbi_cli_available
)
from apps_core.dax_benchmarker_core.stats import (
    analyze_results, format_duration, get_distribution_buckets
)


# Default query template
DEFAULT_QUERY = """EVALUATE
SUMMARIZECOLUMNS (
    'Date'[Year],
    "Total Sales", SUM ( Sales[Amount] )
)"""


PERF_CLASS_COLORS = {
    'excellent': '#107C10',
    'good': '#10893E',
    'warning': '#F59E0B',
    'critical': '#D13438',
}


def render(logger):
    """DAX Benchmarker module for PBI Hub."""

    st.markdown(
        '<h1 class="main-header">⚡ DAX Benchmarker</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Ejecuta queries DAX múltiples veces y analiza performance estadística '
        'con percentiles, outliers y distribución de tiempos.</p>',
        unsafe_allow_html=True,
    )

    # ── Check pbi-cli availability ────────────────────────────────────
    pbi_status = check_pbi_cli_available()

    if not pbi_status['available']:
        use_simulation = True
    elif not pbi_status['connected']:
        st.info(
            f"ℹ️ **pbi-cli disponible pero no conectado a dataset**: {pbi_status['error']}\n\n"
            "Conectá a un dataset para ejecutar queries reales:\n"
            "```bash\n"
            "pbi connect\n"
            "```\n\n"
            "Modo de simulación disponible para testing."
        )
        use_simulation = True
    else:
        st.success(f"✅ pbi-cli conectado — {pbi_status['version']}")
        use_simulation = False

    # ── Configuration ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Configuración")

    col_query, col_config = st.columns([3, 1])

    with col_query:
        query = st.text_area(
            "Query DAX",
            value=DEFAULT_QUERY,
            height=180,
            help="Query DAX a ejecutar. Debe comenzar con EVALUATE.",
        )

    with col_config:
        iterations = st.number_input(
            "Iteraciones",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            help="Número de veces a ejecutar la query. Más iteraciones = más precisión estadística.",
        )

        if use_simulation:
            st.caption("🔧 **Modo simulación** — tiempos sintéticos para testing")
        else:
            st.caption(f"🔗 **Conectado a dataset** — ejecutará query real {iterations}x")

        run_btn = st.button(
            "🚀 Ejecutar Benchmark",
            type="primary",
            use_container_width=True,
            disabled=not query.strip(),
        )

    # ── Execution ──────────────────────────────────────────────────────
    if run_btn:
        # Log event
        try:
            logger.log("dax_benchmarker", "run", iterations=iterations, simulation=use_simulation)
        except Exception:
            pass

        # Validate query
        query_stripped = query.strip()
        if not query_stripped.upper().startswith('EVALUATE'):
            st.error("❌ La query debe comenzar con `EVALUATE`.")
            return

        # Execute benchmark
        with st.spinner(f"Ejecutando {iterations} iteraciones..."):
            results = execute_dax_query(query_stripped, iterations, use_simulation)

        # Analyze
        stats = analyze_results(results)

        # Store in session state
        st.session_state['benchmark_results'] = results
        st.session_state['benchmark_stats'] = stats

    # ── Results view ───────────────────────────────────────────────────
    if 'benchmark_stats' not in st.session_state:
        st.info("Configure la query y presione 'Ejecutar Benchmark' para comenzar.")
        return

    stats = st.session_state['benchmark_stats']
    results = st.session_state['benchmark_results']

    st.markdown("---")

    # ── Summary metrics ────────────────────────────────────────────────
    st.markdown("#### Resultados")

    if stats.failed_executions > 0:
        st.error(
            f"⚠️ {stats.failed_executions} de {stats.total_executions} ejecuciones fallaron. "
            "Ver detalles abajo."
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Ejecuciones", f"{stats.successful_executions}/{stats.total_executions}")
    with c2:
        st.metric("p50 (mediana)", format_duration(stats.p50))
    with c3:
        st.metric("p95", format_duration(stats.p95))
    with c4:
        st.metric("p99", format_duration(stats.p99))
    with c5:
        st.metric("Outliers", stats.outlier_count)

    # Performance class badge
    perf_color = PERF_CLASS_COLORS.get(stats.performance_class, '#5A6478')
    st.markdown(
        f'<div style="background: {perf_color}; color: white; padding: 0.5rem 1rem; '
        f'border-radius: var(--radius-sm); display: inline-block; margin-top: 0.5rem; '
        f'font-weight: 600;">{stats.performance_class.upper()}</div>',
        unsafe_allow_html=True,
    )

    # ── Recommendation ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💡 Recomendación")
    st.markdown(stats.recommendation)

    # Cold vs warm cache
    if stats.successful_executions > 1:
        cold_warm_diff = stats.first_execution_ms - stats.avg_warm_ms
        if cold_warm_diff > stats.avg_warm_ms * 0.3:  # >30% slower
            st.caption(
                f"❄️ **Cold cache penalty detectado**: primera ejecución {format_duration(stats.first_execution_ms)} "
                f"vs promedio warm cache {format_duration(stats.avg_warm_ms)} "
                f"({cold_warm_diff/stats.avg_warm_ms*100:.0f}% más lenta)."
            )

    # ── Box plot (distribución) ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Distribución de tiempos")

    successful = [r for r in results if r.error is None]
    durations = [r.duration_ms for r in successful]

    if len(durations) > 1:
        fig = go.Figure()

        fig.add_trace(go.Box(
            y=durations,
            name='Duración',
            boxmean='sd',  # Show mean and std dev
            marker_color='#3B82F6',
        ))

        # Reference lines
        fig.add_hline(
            y=stats.p95,
            line_dash="dot",
            line_color="#F59E0B",
            annotation_text=f"p95: {format_duration(stats.p95)}",
            annotation_position="right",
        )

        fig.add_hline(
            y=stats.outlier_threshold,
            line_dash="dash",
            line_color="#D13438",
            annotation_text=f"Outlier threshold",
            annotation_position="right",
        )

        fig.update_layout(
            yaxis_title="Duración (ms)",
            height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8ECF4'),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Se necesitan múltiples ejecuciones exitosas para mostrar distribución.")

    # ── Histogram ──────────────────────────────────────────────────────
    st.markdown("#### Histograma")

    dist = get_distribution_buckets(durations, num_buckets=15)

    if dist['buckets']:
        df_hist = pd.DataFrame(dist['buckets'])

        fig_hist = px.bar(
            df_hist,
            x='range',
            y='count',
            labels={'range': 'Rango de tiempo', 'count': 'Frecuencia'},
            color='count',
            color_continuous_scale='Blues',
        )

        fig_hist.update_layout(
            height=350,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8ECF4'),
            showlegend=False,
        )

        st.plotly_chart(fig_hist, use_container_width=True)

    # ── Detailed stats table ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Estadísticas detalladas")

    col_stats1, col_stats2 = st.columns(2)

    with col_stats1:
        st.markdown("**Tiempos:**")
        st.caption(f"Min: {format_duration(stats.min)}")
        st.caption(f"Mean: {format_duration(stats.mean)}")
        st.caption(f"Median: {format_duration(stats.median)}")
        st.caption(f"Max: {format_duration(stats.max)}")
        st.caption(f"StdDev: {format_duration(stats.stddev)}")

    with col_stats2:
        st.markdown("**Percentiles:**")
        st.caption(f"p50: {format_duration(stats.p50)}")
        st.caption(f"p95: {format_duration(stats.p95)}")
        st.caption(f"p99: {format_duration(stats.p99)}")
        st.markdown("**Otros:**")
        st.caption(f"Avg rows: {stats.avg_row_count:,}")

    # ── Execution details table ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Detalle de ejecuciones")

    df = pd.DataFrame([
        {
            '#': r.iteration + 1,
            'Duración': format_duration(r.duration_ms),
            'Filas': r.row_count,
            'Estado': '✅ OK' if r.error is None else f'❌ {r.error}',
            'Outlier': '🔴' if r.error is None and r.duration_ms > stats.outlier_threshold else '',
        }
        for r in results
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Failed executions ──────────────────────────────────────────────
    failed = [r for r in results if r.error is not None]
    if failed:
        st.markdown("---")
        st.markdown("#### ⚠️ Ejecuciones fallidas")
        for r in failed:
            with st.expander(f"Ejecución #{r.iteration + 1}"):
                st.code(r.error, language='text')
