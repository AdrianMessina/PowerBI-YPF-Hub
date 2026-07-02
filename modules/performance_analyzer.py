"""Performance Analyzer — parsea exports JSON de Power BI Performance Analyzer.

Workflow del usuario:
  1. En Power BI Desktop: View → Performance Analyzer → Start recording
  2. Interactuar con el reporte (filtros, navegar páginas, etc)
  3. Stop → Export → guarda JSON
  4. Subir el JSON acá → ver ranking de visuales por tiempo y recomendaciones
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from apps_core.performance_core.parser import parse


SEVERITY_COLORS = {
    'good': '#107C10',
    'warning': '#F59E0B',
    'critical': '#D13438',
}

SEVERITY_ICONS = {
    'good': '🟢',
    'warning': '🟡',
    'critical': '🔴',
}


def render(logger):
    """Performance Analyzer module for PBI Hub."""

    st.markdown(
        '<h1 class="main-header">📈 Performance Analyzer</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Analizá los exports JSON del Performance Analyzer '
        'de Power BI Desktop para identificar visuales lentos y consultas DAX costosas.</p>',
        unsafe_allow_html=True,
    )

    # ── Info banner: different input type ────────────────────────────
    st.info(
        "ℹ️ **Este módulo requiere un input diferente** al del sidebar: "
        "un archivo JSON exportado desde el Performance Analyzer de Power BI Desktop "
        "(View → Performance Analyzer → Export). "
        "El proyecto del sidebar **no se usa** acá."
    )

    # ── Instrucciones plegables ────────────────────────────────────
    with st.expander("📖 ¿Cómo obtengo el JSON desde Power BI Desktop?", expanded=False):
        st.markdown("""
1. En Power BI Desktop, abrí el reporte que querés analizar
2. Andá a la pestaña **Vista** → **Analizador de rendimiento** (Performance Analyzer)
3. Click **Iniciar grabación**
4. Refrescá los visuales (botón refresh o presioná F5) e interactuá con filtros/páginas
5. Click **Detener**
6. Click **Exportar** → guarda un `.json`
7. Subilo abajo

> 💡 El JSON contiene el tiempo de cada query DAX y render por visual.
> Visuales >500ms son sospechosos, >1000ms requieren acción.
        """)

    # ── Upload ────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Subí el JSON exportado del Performance Analyzer",
        type=["json"],
        help="Power BI Desktop → Vista → Analizador de rendimiento → Exportar",
    )

    if uploaded is None:
        st.info("Esperando JSON…")
        return

    # Logging
    try:
        logger.log("performance_analyzer", "upload", filename=uploaded.name)
    except Exception:
        pass

    # ── Parse ─────────────────────────────────────────────────────
    try:
        text = uploaded.read().decode("utf-8")
    except UnicodeDecodeError:
        st.error("El archivo no parece estar en UTF-8.")
        return

    result = parse(text)

    if result.get('errors'):
        for err in result['errors']:
            st.error(err)
        return

    if not result['visuals']:
        st.warning(
            "No se detectaron visuales con duración medible en el JSON. "
            f"({result['raw_event_count']} eventos analizados)"
        )
        return

    # ── Métricas resumen ──────────────────────────────────────────
    totals = result['totals']
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Visuales analizados", totals['n_visuals'])
    with c2:
        st.metric(
            "Lentos (≥500ms)",
            totals['slow_count'],
            delta=None if totals['slow_count'] == 0 else f"{totals['slow_count']} a revisar",
            delta_color="inverse",
        )
    with c3:
        st.metric(
            "Muy lentos (≥1s)",
            totals['very_slow_count'],
            delta=None if totals['very_slow_count'] == 0 else "Críticos",
            delta_color="inverse",
        )
    with c4:
        st.metric("Tiempo total", f"{totals['total_ms']/1000:.1f}s")

    if totals['top_offender']:
        st.caption(f"🏆 Visual más lento: **{totals['top_offender']}**")

    # ── Gráfico de barras Top N ────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Top visuales por tiempo de render")

    df_vis = pd.DataFrame(result['visuals'])
    top_n = min(15, len(df_vis))
    df_top = df_vis.head(top_n).copy()

    # Stack bar: dax + render + other
    df_long = df_top.melt(
        id_vars=['name', 'severity', 'page'],
        value_vars=['dax_ms', 'render_ms', 'other_ms'],
        var_name='component',
        value_name='ms',
    )
    df_long['component'] = df_long['component'].map({
        'dax_ms': 'DAX query',
        'render_ms': 'Visual render',
        'other_ms': 'Other',
    })

    fig = px.bar(
        df_long,
        x='ms',
        y='name',
        color='component',
        orientation='h',
        height=max(360, 28 * top_n),
        color_discrete_map={
            'DAX query': '#3B82F6',
            'Visual render': '#8B5CF6',
            'Other': '#5A6478',
        },
        labels={'ms': 'Tiempo (ms)', 'name': 'Visual', 'component': 'Componente'},
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E8ECF4'),
        legend=dict(orientation='h', y=-0.15),
    )
    fig.add_vline(x=500, line_dash="dot", line_color="#F59E0B", opacity=0.4,
                  annotation_text="500ms", annotation_position="top")
    fig.add_vline(x=1000, line_dash="dot", line_color="#D13438", opacity=0.4,
                  annotation_text="1s", annotation_position="top")
    st.plotly_chart(fig, use_container_width=True)

    # ── Tabla detallada ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Detalle por visual")

    df_show = df_vis[['name', 'type', 'page', 'total_ms', 'dax_ms', 'render_ms',
                      'other_ms', 'severity']].copy()
    df_show['estado'] = df_show['severity'].map(SEVERITY_ICONS)
    df_show = df_show[['estado', 'name', 'type', 'page', 'total_ms',
                       'dax_ms', 'render_ms', 'other_ms']]
    df_show.columns = ['', 'Visual', 'Tipo', 'Página', 'Total (ms)',
                       'DAX (ms)', 'Render (ms)', 'Other (ms)']
    st.dataframe(df_show, use_container_width=True, hide_index=True)

    # ── Queries DAX de los visuales lentos ────────────────────────
    slow_visuals = [v for v in result['visuals'] if v['severity'] != 'good' and v['queries']]
    if slow_visuals:
        st.markdown("---")
        st.markdown("#### Queries DAX de visuales lentos")
        st.caption("Las queries detectadas en visuales con tiempo ≥ 500ms.")
        for v in slow_visuals[:10]:
            icon = SEVERITY_ICONS[v['severity']]
            with st.expander(f"{icon} {v['name']} — {v['total_ms']}ms"):
                st.caption(f"Página: {v['page']} | Tipo: {v['type']} | DAX: {v['dax_ms']}ms")
                for i, q in enumerate(v['queries'], 1):
                    st.code(q, language='dax')
                    if i >= 3:
                        break

    # ── Recomendaciones ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💡 Recomendaciones")

    recs = _build_recommendations(result)
    for rec in recs:
        icon = {'P0': '🔴', 'P1': '🟠', 'P2': '🟡', 'P3': '🟢'}.get(rec['priority'], '⚪')
        st.markdown(f"{icon} **{rec['title']}**")
        st.caption(rec['body'])


def _build_recommendations(result):
    """Heurísticas para emitir recomendaciones según el patrón del JSON."""
    recs = []
    visuals = result['visuals']
    totals = result['totals']

    if not visuals:
        return [{'title': 'Sin datos', 'body': 'No hay visuales para analizar.', 'priority': 'P3'}]

    # Crítico: visuales > 1s
    if totals['very_slow_count'] > 0:
        offenders = [v['name'] for v in visuals if v['total_ms'] >= 1000][:5]
        recs.append({
            'title': f"{totals['very_slow_count']} visual(es) muy lentos (≥1s)",
            'body': (f'Visuales que requieren acción inmediata: {", ".join(offenders)}. '
                     'Revisá las queries DAX abajo — suelen necesitar reescritura o '
                     'columnas pre-calculadas.'),
            'priority': 'P0',
        })

    # DAX domina vs render
    dax_heavy = sum(1 for v in visuals if v['dax_ms'] > v['render_ms'] * 2 and v['total_ms'] >= 500)
    if dax_heavy >= 3:
        recs.append({
            'title': f'{dax_heavy} visuales con cuello de botella en DAX',
            'body': ('DAX domina sobre render — el modelo es el problema, no el visual. '
                     'Considerá: medidas con CALCULATE más simples, agregaciones en el origen, '
                     'columnas calculadas movidas a Power Query.'),
            'priority': 'P1',
        })

    # Render domina vs DAX
    render_heavy = sum(1 for v in visuals if v['render_ms'] > v['dax_ms'] * 2 and v['total_ms'] >= 500)
    if render_heavy >= 3:
        recs.append({
            'title': f'{render_heavy} visuales con cuello de botella en render',
            'body': ('Render domina sobre DAX — el visual tiene demasiados puntos de datos o '
                     'es un tipo de visual costoso (matrix con muchas filas, scatter denso, '
                     'visuales custom no optimizados). Considerá TopN o tablas más chicas.'),
            'priority': 'P1',
        })

    # Page outliers
    by_page = {}
    for v in visuals:
        by_page.setdefault(v['page'], []).append(v['total_ms'])
    worst_page = max(by_page.items(),
                     key=lambda kv: sum(kv[1])) if by_page else None
    if worst_page and sum(worst_page[1]) > 3000:
        recs.append({
            'title': f'Página más pesada: "{worst_page[0]}" ({sum(worst_page[1])/1000:.1f}s acumulados)',
            'body': ('Esta página tiene el mayor tiempo total. Si los usuarios la abren seguido, '
                     'priorizá su optimización.'),
            'priority': 'P2',
        })

    # Todo OK
    if not recs:
        recs.append({
            'title': 'Performance OK',
            'body': f'Todos los visuales bajo 500ms. {totals["n_visuals"]} visuales en '
                    f'{totals["total_ms"]/1000:.1f}s totales.',
            'priority': 'P3',
        })

    return recs
