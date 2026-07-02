"""
DAX Optimizer - Integrado en YPF BI Monitor
Replica funcionalidad completa de DAX Optimizer v1.1
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
import os
import time

# Streamlit extras para componentes visuales mejorados (OPCIONAL)
try:
    from streamlit_extras.metric_cards import style_metric_cards
    from streamlit_extras.colored_header import colored_header
    STREAMLIT_EXTRAS_AVAILABLE = True
except ImportError:
    STREAMLIT_EXTRAS_AVAILABLE = False
    # Fallback: crear funciones dummy
    def style_metric_cards(*args, **kwargs):
        pass
    def colored_header(label, description="", color_name="blue-70"):
        st.markdown(f'<h1 class="main-header">{label}</h1>', unsafe_allow_html=True)
        if description:
            st.markdown(f'<p class="sub-header">{description}</p>', unsafe_allow_html=True)

# Streamlit Lottie para animaciones profesionales (OPCIONAL)
try:
    from streamlit_lottie import st_lottie
    import requests
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False

def render(logger):
    """DAX Optimizer module for PBI Hub."""

    # Imports absolutos - NO requiere manipular sys.path
    from apps_core.dax_core.core import (
        extract_measures_from_pbip,
        validate_pbip_file,
        get_pbip_info,
        parse_dax_code,
        analyze_dax,
        generate_suggestions,
        calculate_score,
        rank_measures,
        get_summary_stats,
        filter_measures_by_priority,
        get_top_issues,
        get_priority_color
    )

    # Variable para logger
    usage_logger = logger
    LOGGING_ENABLED = logger is not None
    
    
    # Import shared styles
    from apps_core.layout_core.shared_styles import render_app_header, render_footer

    # App-specific styles aligned to Industrial Data Observatory design system
    st.markdown("""
    <style>
        .metric-card {
            background: var(--surface-2);
            padding: 1.5rem;
            border-radius: var(--radius-lg);
            color: var(--text-primary);
            text-align: center;
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--brand-accent);
            transition: all var(--duration-normal) var(--ease-out);
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: var(--brand-accent);
        }
        .metric-value {
            font-family: var(--font-mono);
            font-size: 2.25rem;
            font-weight: 600;
            color: var(--brand-accent);
            margin: 0.5rem 0;
        }
        .metric-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 500;
        }
        .issue-badge {
            padding: 0.25rem 0.7rem;
            border-radius: var(--radius-full);
            font-weight: 600;
            font-size: 0.7rem;
            display: inline-block;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 1px solid transparent;
        }
        .critical-badge {
            background: var(--status-danger-bg);
            color: var(--status-danger);
            border-color: rgba(209,52,56,0.25);
        }
        .warning-badge {
            background: var(--status-warn-bg);
            color: var(--status-warn);
            border-color: rgba(245,158,11,0.25);
        }
        .info-badge {
            background: var(--brand-accent-muted);
            color: var(--brand-accent);
            border-color: rgba(242,200,17,0.25);
        }
        .measure-card {
            background: var(--surface-2);
            border-radius: var(--radius-md);
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--brand-accent);
            transition: all var(--duration-normal) var(--ease-out);
            color: var(--text-secondary);
        }
        .measure-card:hover {
            background: var(--surface-3);
            transform: translateX(2px);
            box-shadow: var(--shadow-md);
        }
        .developer-badge {
            background: var(--surface-3);
            color: var(--text-primary);
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--brand-accent);
            padding: 1rem;
            border-radius: var(--radius-md);
            text-align: center;
            margin-top: 0.5rem;
        }
        .how-it-works-box {
            background: var(--surface-2);
            border: 1px solid var(--border-subtle);
            border-left: 3px solid var(--brand-accent);
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }
    </style>
    """, unsafe_allow_html=True)
    
    
    def load_lottie_url(url: str):
        """Carga una animación Lottie desde una URL de manera segura"""
        if not LOTTIE_AVAILABLE:
            return None
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                return None
            return r.json()
        except Exception:
            return None
    
    
    def show_lottie_animation(lottie_json, height=200, key="lottie"):
        """Muestra una animación Lottie si está disponible"""
        if LOTTIE_AVAILABLE and lottie_json is not None:
            st_lottie(lottie_json, height=height, key=key)
    
    
    def render_header():
        """Renderiza el header de la aplicación"""
        st.markdown(
            '<h1 class="main-header">⚡ DAX Optimizer</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="sub-header">Análisis avanzado de medidas DAX con sistema de tolerancia y score de riesgo.</p>',
            unsafe_allow_html=True,
        )

        # Cómo funciona en el header
        with st.expander("📖 ¿Cómo funciona?", expanded=False):
            st.markdown("""
**🔄 Proceso de análisis:**

1. **📁 Carga del archivo PBIP** — Se extraen todas las medidas DAX del modelo
2. **🔍 Análisis individual** — Cada medida se analiza en busca de:
   - Problemas críticos de performance
   - Advertencias de mejores prácticas
   - Oportunidades de optimización
3. **📊 Cálculo de scores** — Se asigna un score de 0-100 a cada medida
4. **📈 Ranking y priorización** — Las medidas se ordenan por impacto
5. **💡 Recomendaciones** — Se generan sugerencias específicas de optimización

**📏 Criterios de evaluación (Score de Riesgo):**

- 🔴 **Crítico (76-100)** — Problemas severos que afectan significativamente la performance
- 🟠 **Alto (51-75)** — Múltiples warnings o complejidad alta
- 🟡 **Medio (26-50)** — Algunos problemas menores
- 🟢 **Bajo (0-25)** — Código bien optimizado

📌 *Mayor score = Mayor riesgo de impacto en performance.*
            """)
    
    
    def render_file_upload():
        """Renderiza la sección de carga de archivo PBIP (solo ZIP upload)"""
        with st.expander("📁 Cargar proyecto PBIP", expanded=True):
            st.info("""
            **ℹ️ Cómo subir tu proyecto Power BI:**

            1. En Power BI Desktop, guarda tu reporte como **Power BI Project (.pbip)**
            2. Esto genera una carpeta con archivos `.pbip`, `.Report/` y `.SemanticModel/`
            3. **Comprimí toda la carpeta en un archivo ZIP**
            4. Subilo abajo
            """)

            uploaded_file = st.file_uploader(
                "Selecciona el archivo .zip de tu proyecto PBIP",
                type=['zip'],
                help="ZIP conteniendo la carpeta .SemanticModel con definition/ y archivos .tmdl"
            )

        # Mantenemos compatibilidad con el resto del código (pbip_folder_path siempre None)
        return None, uploaded_file
    
    
    def export_measures_to_csv(ranked_measures):
        """Exporta las medidas analizadas a un archivo CSV"""
        data = []
        for measure in ranked_measures:
            row = {
                'Nombre': measure.name,
                'Tabla': measure.table,
                'Score de Riesgo': measure.impact_score,
                'Prioridad': measure.priority_label,
                'Complejidad': measure.complexity,
                'Issues Críticos': measure.critical_issues,
                'Warnings': measure.warnings,
                'Total Issues': measure.critical_issues + measure.warnings,
                'Funciones': measure.metrics.function_count if measure.metrics else 0,
                'Variables': measure.metrics.variables_used if measure.metrics else 0,
                'Iteradores Anidados': measure.metrics.nested_iterators if measure.metrics else 0,
                'Transiciones de Contexto': measure.metrics.context_transitions if measure.metrics else 0,
                'Impacto Estimado': measure.metrics.estimated_impact if measure.metrics else 'N/A',
                'Expresión DAX': measure.expression
            }
            data.append(row)
    
        df = pd.DataFrame(data)
        return df.to_csv(index=False).encode('utf-8')
    
    
    def export_measures_to_html(ranked_measures):
        """Exporta las medidas analizadas a un archivo HTML con formato"""
        data = []
        for measure in ranked_measures:
            row = {
                'Nombre': measure.name,
                'Tabla': measure.table,
                'Score de Riesgo': measure.impact_score,
                'Prioridad': measure.priority_label,
                'Complejidad': measure.complexity,
                'Issues Críticos': measure.critical_issues,
                'Warnings': measure.warnings,
                'Total Issues': measure.critical_issues + measure.warnings,
                'Funciones': measure.metrics.function_count if measure.metrics else 0,
                'Variables': measure.metrics.variables_used if measure.metrics else 0,
                'Iteradores Anidados': measure.metrics.nested_iterators if measure.metrics else 0,
                'Transiciones de Contexto': measure.metrics.context_transitions if measure.metrics else 0,
                'Impacto Estimado': measure.metrics.estimated_impact if measure.metrics else 'N/A'
            }
            data.append(row)
    
        df = pd.DataFrame(data)
    
        # Crear HTML con estilos
        html = df.to_html(index=False, escape=False, classes='table table-striped')
    
        # Agregar estilos CSS
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Análisis DAX - Reporte</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
                h1 {{ color: #0451E4; }}
                .table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .table th {{ background: #0451E4; color: white; padding: 12px; text-align: left; }}
                .table td {{ padding: 10px; border-bottom: 1px solid #dee2e6; }}
                .table tr:hover {{ background: #f1f3f5; }}
            </style>
        </head>
        <body>
            <h1>⚡ DAX Optimizer - Análisis de Medidas</h1>
            <p>Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            {html}
        </body>
        </html>
        """
    
        return styled_html.encode('utf-8')
    
    
    def render_summary_stats(stats: dict, tolerance: int = 50):
        """Renderiza estadísticas de resumen con score de tolerancia"""
        st.markdown("### 📊 Resumen del análisis")
    
        col1, col2, col3, col4, col5 = st.columns(5)
    
        with col1:
            st.metric("Medidas DAX analizadas", stats['total_measures'],
                      help="Solo medidas DAX (measures). No incluye columnas calculadas ni tablas calculadas. Esta cifra puede diferir del total mostrado en Power BI Analyzer, que incluye columnas calculadas.")
    
        with col2:
            st.metric("🔴 Riesgo crítico", stats['critical_measures'],
                     delta=None, delta_color="inverse")
    
        with col3:
            st.metric("🟠 Riesgo alto", stats['high_priority'],
                     delta=None, delta_color="inverse")
    
        with col4:
            st.metric("Issues críticos", stats['total_critical_issues'])
    
        with col5:
            # Comparar con tolerancia
            avg_score = stats['avg_score']
            delta = avg_score - tolerance
            delta_color = "inverse"  # Rojo si es positivo (por encima de tolerancia)
    
            if avg_score > tolerance:
                help_text = f"⚠️ El reporte está {delta:.1f} puntos por encima de la tolerancia"
            else:
                help_text = f"✅ El reporte está dentro de la tolerancia ({tolerance} puntos)"
    
            st.metric("Riesgo promedio", f"{avg_score:.1f}/100",
                     delta=f"{delta:+.1f} vs tolerancia",
                     delta_color=delta_color,
                     help=help_text)
    
        # Aplicar estilo mejorado a todas las métricas
        style_metric_cards(
            background_color="#FFFFFF",
            border_left_color="#0451E4",
            border_color="#e9ecef",
            box_shadow=True,
            border_size_px=2,
            border_radius_px=12
        )
    
    
    def render_tolerance_gauge(avg_score: float, tolerance: int):
        """Renderiza un gauge mostrando el score promedio vs tolerancia"""
        # Determinar color según si está dentro o fuera de tolerancia
        if avg_score <= tolerance * 0.5:
            gauge_color = "#2ed573"  # Verde
        elif avg_score <= tolerance:
            gauge_color = "#ffd32a"  # Amarillo
        elif avg_score <= tolerance * 1.5:
            gauge_color = "#ffa502"  # Naranja
        else:
            gauge_color = "#ff4757"  # Rojo
    
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Score Promedio del Reporte", 'font': {'size': 18}},
            delta={'reference': tolerance, 'increasing': {'color': "#ff4757"}, 'decreasing': {'color': "#2ed573"}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
                'bar': {'color': gauge_color, 'thickness': 0.75},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, tolerance], 'color': 'rgba(46, 213, 115, 0.2)'},
                    {'range': [tolerance, 100], 'color': 'rgba(255, 71, 87, 0.2)'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': tolerance
                }
            }
        ))
    
        fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=50, b=20),
            font={'color': "darkgray", 'family': "Arial"}
        )
    
        return fig
    
    
    def render_top_risky_measures_with_influence(ranked_measures, tolerance: int, top_n=10):
        """Renderiza gráfico de top medidas mostrando su influencia en el score total"""
        # Tomar las top N medidas con mayor riesgo
        top_measures = ranked_measures[:top_n]
    
        if not top_measures:
            return None
    
        # Calcular score total y contribución de cada medida
        total_measures = len(ranked_measures)
        avg_score = sum(m.impact_score for m in ranked_measures) / total_measures
    
        # Preparar datos
        names = [m.name[:35] + '...' if len(m.name) > 35 else m.name for m in top_measures]
        scores = [m.impact_score for m in top_measures]
        # Contribución: cuánto aporta esta medida al score promedio
        contributions = [(m.impact_score / total_measures) for m in top_measures]
        colors = [get_priority_color(m.impact_score) for m in top_measures]
    
        # Crear gráfico de barras horizontales
        fig = go.Figure()
    
        # Barra principal de score
        fig.add_trace(go.Bar(
            y=names[::-1],
            x=scores[::-1],
            orientation='h',
            name='Score de Riesgo',
            marker=dict(
                color=colors[::-1],
                line=dict(color='rgba(0,0,0,0.3)', width=1)
            ),
            text=[f"{s:.0f}" for s in scores[::-1]],
            textposition='inside',
            textfont=dict(color='white', size=12, family='Arial Black'),
            hovertemplate='<b>%{y}</b><br>Score: %{x:.1f}/100<br>Contribución al promedio: %{customdata:.2f}<extra></extra>',
            customdata=contributions[::-1]
        ))
    
        # Línea de tolerancia
        fig.add_vline(
            x=tolerance,
            line_dash="dash",
            line_color="red",
            line_width=3,
            annotation_text=f"Tolerancia ({tolerance})",
            annotation_position="top"
        )
    
        # Línea de score promedio
        fig.add_vline(
            x=avg_score,
            line_dash="dot",
            line_color="blue",
            line_width=2,
            annotation_text=f"Promedio ({avg_score:.1f})",
            annotation_position="bottom"
        )
    
        fig.update_layout(
            title=f"Top {top_n} Medidas con Mayor Riesgo e Influencia",
            xaxis_title="Score de Riesgo (0-100)",
            yaxis_title="",
            height=450,
            showlegend=False,
            margin=dict(l=20, r=20, t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                range=[0, 100],
                gridcolor='rgba(128,128,128,0.2)'
            ),
            font=dict(size=11)
        )
    
        return fig
    
    
    def render_top_issues(ranked_measures):
        """Renderiza los issues más comunes"""
        top_issues = get_top_issues(ranked_measures, top_n=5)
    
        if not top_issues:
            return
    
        st.markdown("### 🎯 Issues más frecuentes")
    
        for idx, issue in enumerate(top_issues, 1):
            severity_colors = {
                'critical': '🔴',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
    
            icon = severity_colors.get(issue['severity'], '•')
    
            with st.expander(f"{icon} **{issue['title']}** - Encontrado en {issue['count']} medida(s)"):
                st.write(f"**ID:** `{issue['id']}`")
                st.write(f"**Severidad:** {issue['severity'].upper()}")
                st.write(f"**Medidas afectadas:** {', '.join(issue['measures'][:5])}")
                if len(issue['measures']) > 5:
                    st.write(f"... y {len(issue['measures']) - 5} más")
    
    
    def render_measures_table(ranked_measures):
        """Renderiza tabla de medidas con ranking"""
        st.markdown("### 📋 Ranking de medidas")
    
        # Filtros
        col1, col2, col3 = st.columns([2, 2, 3])
    
        with col1:
            priority_filter = st.selectbox(
                "Filtrar por prioridad",
                ["Todas", "Crítico", "Alto", "Medio", "Bajo"]
            )
    
        with col2:
            sort_by = st.selectbox(
                "Ordenar por",
                ["Riesgo (mayor primero)", "Riesgo (menor primero)", "Nombre", "Complejidad"]
            )
    
        with col3:
            search = st.text_input("🔍 Buscar medida", placeholder="Nombre de la medida...")
    
        # Aplicar filtros
        filtered_measures = filter_measures_by_priority(ranked_measures, priority_filter)
    
        if search:
            filtered_measures = [
                m for m in filtered_measures
                if search.lower() in m.name.lower()
            ]
    
        # Aplicar ordenamiento
        if sort_by == "Riesgo (menor primero)":
            filtered_measures.sort(key=lambda m: m.impact_score)
        elif sort_by == "Nombre":
            filtered_measures.sort(key=lambda m: m.name)
        elif sort_by == "Complejidad":
            filtered_measures.sort(key=lambda m: m.complexity, reverse=True)
        # Por defecto ya está ordenado por riesgo (mayor primero)
    
        st.markdown(f"**Mostrando {len(filtered_measures)} de {len(ranked_measures)} medidas**")
    
        # Renderizar tabla
        for idx, measure in enumerate(filtered_measures):
            render_measure_row(measure, idx)
    
    
    def render_measure_row(measure, index):
        """Renderiza una fila de medida expandible con diseño mejorado"""
    
        # Color según prioridad
        border_color = get_priority_color(measure.impact_score)
    
        # Emoji según prioridad
        priority_emoji = {
            "Crítico": "🔴",
            "Alto": "🟠",
            "Medio": "🟡",
            "Bajo": "🟢"
        }
        emoji = priority_emoji.get(measure.priority_label, "⚪")
    
        # Contenedor de la medida con diseño mejorado
        st.markdown(f"""
        <div style="background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0, 102, 204, 0.15);
                    border-left: 6px solid {border_color};
                    border: 1px solid #e9ecef;">
        """, unsafe_allow_html=True)
    
        # Header con información principal
        col1, col2, col3, col4 = st.columns([4, 1.5, 1, 1])
    
        with col1:
            st.markdown(f"### {measure.name}")
            st.markdown(f"""
            <div style="background: rgba(4,81,228,0.10); color: #E8ECF4;
                        border: 1px solid rgba(4,81,228,0.25);
                        padding: 6px 12px; border-radius: 6px; display: inline-block; margin-top: 5px;
                        font-family: 'Fira Sans', sans-serif; font-size: 0.85rem;">
                📊 Tabla: <strong style="color: #F1F5F9;">{measure.table}</strong>
            </div>
            """, unsafe_allow_html=True)
    
        with col2:
            # Badge de prioridad grande y claro
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {border_color} 0%, {border_color}dd 100%);
                        color: white; padding: 12px 18px;
                        border-radius: 25px; text-align: center; font-weight: bold; font-size: 15px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                {emoji} {measure.priority_label.upper()}
            </div>
            """, unsafe_allow_html=True)
    
        with col3:
            st.metric("Score Riesgo", f"{measure.impact_score}/100",
                     help="Score de 0-100. Mayor = Mayor riesgo de performance")
    
        with col4:
            # Resumen de issues
            total_issues = measure.critical_issues + measure.warnings
            if total_issues > 0:
                st.metric("Issues", total_issues,
                         delta=f"{measure.critical_issues} críticos" if measure.critical_issues > 0 else None,
                         delta_color="inverse")
            else:
                st.metric("Issues", "0", help="Sin problemas detectados")
    
        # Expander con detalles
        with st.expander("🔍 Ver análisis completo de la medida"):
            render_measure_detail(measure)
    
        st.markdown("</div>", unsafe_allow_html=True)
    
    
    def render_measure_detail(measure):
        """Renderiza el análisis detallado de una medida"""
    
        # Tabs para organizar información
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Código DAX", "🔍 Análisis", "💡 Sugerencias", "📊 Métricas"])
    
        with tab1:
            st.markdown("#### Código completo")
            st.code(measure.expression, language='dax')
    
        with tab2:
            st.markdown("#### Problemas detectados")
    
            if not measure.issues:
                st.success("✅ No se detectaron problemas en esta medida")
            else:
                # Agrupar por severidad
                critical = [i for i in measure.issues if i.severity == 'critical']
                warnings = [i for i in measure.issues if i.severity == 'warning']
                infos = [i for i in measure.issues if i.severity == 'info']
    
                if critical:
                    st.markdown("##### 🔴 Problemas críticos")
                    for issue in critical:
                        render_issue_card(issue)
    
                if warnings:
                    st.markdown("##### ⚠️ Advertencias")
                    for issue in warnings:
                        render_issue_card(issue)
    
                if infos:
                    st.markdown("##### ℹ️ Información")
                    for issue in infos:
                        render_issue_card(issue)
    
        with tab3:
            st.markdown("#### Recomendaciones de optimización")
    
            if not measure.suggestions:
                st.info("No hay sugerencias específicas para esta medida")
            else:
                for suggestion in measure.suggestions:
                    render_suggestion_card(suggestion)
    
        with tab4:
            st.markdown("#### Métricas de performance")
    
            if measure.metrics is not None:
                col1, col2 = st.columns(2)
    
                with col1:
                    st.metric("Complejidad", measure.metrics.complexity)
                    st.metric("Funciones totales", measure.metrics.function_count)
                    st.metric("Variables usadas", measure.metrics.variables_used)
    
                with col2:
                    st.metric("Iteradores anidados", measure.metrics.nested_iterators)
                    st.metric("Transiciones de contexto", measure.metrics.context_transitions)
                    st.metric("Impacto estimado", measure.metrics.estimated_impact.upper())
            else:
                st.warning("⚠️ No se pudieron calcular las métricas de performance para esta medida debido a un error en el análisis.")
    
    
    def render_issue_card(issue):
        """Renderiza una tarjeta de issue"""
        severity_icons = {
            'critical': '🔴',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
    
        icon = severity_icons.get(issue.severity, '•')
    
        with st.container():
            st.markdown(f"**{icon} {issue.title}**")
            st.write(issue.description)
    
            if issue.snippet:
                st.code(issue.snippet, language='dax')
    
            if issue.learn_more:
                st.markdown(f"[📚 Más información]({issue.learn_more})")
    
            st.markdown("---")
    
    
    def render_suggestion_card(suggestion):
        """Renderiza una tarjeta de sugerencia"""
        impact_icons = {
            'high': '🔥',
            'medium': '💡',
            'low': 'ℹ️'
        }
    
        icon = impact_icons.get(suggestion.impact, '•')
    
        with st.container():
            st.markdown(f"**{icon} {suggestion.title}** - Impacto: {suggestion.impact.upper()}")
            st.write(suggestion.description)
    
            col1, col2 = st.columns(2)
    
            with col1:
                st.markdown("**❌ Código actual:**")
                st.code(suggestion.original_code, language='dax')
    
            with col2:
                st.markdown("**✅ Código sugerido:**")
                st.code(suggestion.suggested_code, language='dax')
    
            st.info(f"**Por qué:** {suggestion.reason}")
            st.markdown("---")
    
    
    def analyze_pbip_file(file_path: str):
        """Analiza un archivo PBIP completo con animación de progreso"""
    
        # ========================================
        # LOGGING: Registrar inicio de análisis
        # ========================================
        analysis_start = time.time()
    
        # Animación Lottie de inicio (si está disponible)
        lottie_analyzing = load_lottie_url("https://lottie.host/92769a14-9afe-4f06-b9a1-dfb8c16d88ab/IcWLmUNs9c.json")
    
        # Animación de inicio
        if lottie_analyzing:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                show_lottie_animation(lottie_analyzing, height=150, key="analyzing_start")
    
        with st.spinner("🔄 Iniciando análisis del archivo PBIP..."):
            time.sleep(0.5)  # Pequeño delay para dar sensación de análisis
    
        # Validar archivo
        is_valid, message = validate_pbip_file(file_path)
    
        if not is_valid:
            st.error(f"❌ Error: {message}")
            return None
    
        # Mostrar información del archivo
        with st.spinner("📂 Extrayendo información del archivo PBIP..."):
            pbip_info = get_pbip_info(file_path)
            time.sleep(0.5)
    
        st.success(f"✅ Archivo válido: {pbip_info['format']}")
    
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tablas", pbip_info['tables_count'])
        with col2:
            st.metric("Medidas DAX", pbip_info['measures_count'],
                      help="Solo medidas DAX (measures). No incluye columnas calculadas ni tablas calculadas.")
        with col3:
            file_size_mb = pbip_info['file_size'] / (1024 * 1024)
            st.metric("Tamaño", f"{file_size_mb:.2f} MB")
    
        # Extraer medidas
        with st.spinner("🔍 Extrayendo medidas DAX del modelo..."):
            measures = extract_measures_from_pbip(file_path)
            time.sleep(0.5)
    
        if not measures:
            st.warning("⚠️ No se encontraron medidas en el archivo PBIP")
            return None
    
        st.info(f"✅ Se encontraron {len(measures)} medidas para analizar")
    
        # Analizar cada medida
        analyzed_measures = []
        failed_measures = []
    
        progress_bar = st.progress(0)
        status_text = st.empty()
    
        for idx, measure in enumerate(measures):
            status_text.text(f"Analizando medida {idx + 1} de {len(measures)}: {measure['name']}")
    
            try:
                # Parsear y analizar
                parsed = parse_dax_code(measure['expression'])
                issues, metrics = analyze_dax(parsed)
                suggestions = generate_suggestions(parsed, issues)
                base_score = calculate_score(parsed, issues)
    
                analyzed_measures.append({
                    'name': measure['name'],
                    'table': measure['table'],
                    'expression': measure['expression'],
                    'issues': issues,
                    'metrics': metrics,
                    'suggestions': suggestions,
                    'base_score': base_score
                })
            except Exception as e:
                # Si falla el análisis de una medida, registrarla y continuar
                failed_measures.append({
                    'name': measure['name'],
                    'table': measure['table'],
                    'error': str(e)
                })
    
                # Agregar una entrada básica para que al menos aparezca en el reporte
                analyzed_measures.append({
                    'name': measure['name'],
                    'table': measure['table'],
                    'expression': measure['expression'],
                    'issues': [],
                    'metrics': None,
                    'suggestions': [],
                    'base_score': 100  # Score neutral para medidas que no se pudieron analizar
                })
    
            progress_bar.progress((idx + 1) / len(measures))
    
        progress_bar.empty()
        status_text.empty()
    
        # Mostrar advertencia si hubo medidas que fallaron
        if failed_measures:
            with st.expander(f"⚠️ {len(failed_measures)} medida(s) no se pudieron analizar completamente", expanded=False):
                for failed in failed_measures:
                    st.warning(f"**{failed['name']}** (Tabla: {failed['table']}): {failed['error']}")
                st.info("Estas medidas fueron incluidas en el reporte con un score neutral. Puedes revisarlas manualmente.")
    
        # Rankear medidas con animación
        with st.spinner("📊 Calculando ranking de medidas y generando estadísticas..."):
            ranked_measures = rank_measures(analyzed_measures)
            time.sleep(0.7)
    
        # Mensaje de éxito con animación
        success_placeholder = st.empty()
        success_placeholder.success("🎉 ¡Análisis completado exitosamente! Los resultados están listos.")
        time.sleep(1.5)
        success_placeholder.empty()
    
        # ========================================
        # LOGGING: Registrar análisis completado
        # ========================================
        analysis_duration = time.time() - analysis_start
    
        if LOGGING_ENABLED and usage_logger:
            try:
                # Obtener estadísticas de prioridades
                stats = get_summary_stats(ranked_measures)
    
                # Registrar análisis de archivo
                usage_logger.log_file_analyzed(
                    filename=Path(file_path).name,
                    file_size_mb=pbip_info.get('file_size', 0) / (1024 * 1024) if 'pbip_info' in locals() else 0,
                    file_type='pbip',
                    analysis_duration_seconds=analysis_duration,
                    score=None,  # DAX Optimizer no tiene score general
                    recommendations_count=len(ranked_measures)
                )
    
                # Registrar análisis de medidas DAX (específico)
                usage_logger.log_dax_measures_analyzed(
                    measures_count=len(ranked_measures),
                    critical_count=stats.get('critical', 0),
                    high_count=stats.get('high', 0),
                    medium_count=stats.get('medium', 0),
                    low_count=stats.get('low', 0)
                )
            except Exception as e:
                print(f"⚠️ Error al registrar análisis: {e}")
    
        return ranked_measures
    
    
    def main():
        """Función principal de la aplicación"""

        # Render header
        render_header()
    
        # ── Unified project source (sidebar) ─────────────────────────
        from shared.loader import get_project
        project = get_project()

        file_to_analyze = None
        temp_file_path = None

        if project is not None:
            file_to_analyze = project.report_path
        else:
            st.warning(
                "⚠️ **Sin proyecto cargado.** "
                "Cargá un archivo PBIP desde el sidebar para analizar sus medidas DAX."
            )
            st.stop()
    
        if file_to_analyze:
            try:
                # Analizar archivo
                with st.spinner('Analizando archivo PBIP...'):
                    ranked_measures = analyze_pbip_file(file_to_analyze)
    
                if ranked_measures:
                    st.success(f"✅ Análisis completado: {len(ranked_measures)} medidas encontradas")
    
                    # Botones de exportación
                    col_export1, col_export2, col_export3 = st.columns([1, 1, 4])
    
                    with col_export1:
                        csv_data = export_measures_to_csv(ranked_measures)
                        st.download_button(
                            label="📥 Exportar CSV",
                            data=csv_data,
                            file_name=f"dax_analysis_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            help="Descargar análisis completo en formato CSV"
                        )
    
                    with col_export2:
                        html_data = export_measures_to_html(ranked_measures)
                        st.download_button(
                            label="📥 Exportar HTML",
                            data=html_data,
                            file_name=f"dax_analysis_{time.strftime('%Y%m%d_%H%M%S')}.html",
                            mime="text/html",
                            help="Descargar análisis completo en formato HTML con estilos"
                        )
    
                    st.markdown("---")
    
                    # Control de tolerancia
                    st.markdown("### ⚙️ Configuración de Tolerancia")
                    tolerance = st.slider(
                        "Umbral de tolerancia de riesgo",
                        min_value=0,
                        max_value=100,
                        value=50,
                        step=5,
                        help="Define el nivel máximo aceptable de riesgo. Medidas por encima de este valor requieren optimización."
                    )
    
                    col_info1, col_info2 = st.columns([2, 1])
                    with col_info1:
                        st.info(f"""
                        **Tolerancia configurada: {tolerance} puntos**
                        - Medidas con score ≤ {tolerance}: Dentro de tolerancia ✅
                        - Medidas con score > {tolerance}: Requieren atención ⚠️
                        """)
                    with col_info2:
                        # Contar medidas fuera de tolerancia
                        measures_above = sum(1 for m in ranked_measures if m.impact_score > tolerance)
                        st.metric("Medidas fuera de tolerancia",
                                 f"{measures_above}/{len(ranked_measures)}",
                                 delta=f"{(measures_above/len(ranked_measures)*100):.1f}%",
                                 delta_color="inverse")
    
                    st.markdown("---")
    
                    # Estadísticas de resumen
                    stats = get_summary_stats(ranked_measures)
                    render_summary_stats(stats, tolerance=tolerance)
    
                    st.markdown("---")
    
                    # Visualizaciones
                    col1, col2 = st.columns([2, 1])
    
                    with col1:
                        fig = render_top_risky_measures_with_influence(ranked_measures, tolerance=tolerance, top_n=10)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
    
                    with col2:
                        # Gauge de score promedio vs tolerancia
                        fig_gauge = render_tolerance_gauge(stats['avg_score'], tolerance)
                        st.plotly_chart(fig_gauge, use_container_width=True)
    
                    st.markdown("---")
    
                    # Issues más frecuentes
                    render_top_issues(ranked_measures)
    
                    st.markdown("---")
    
                    # Tabla de medidas
                    render_measures_table(ranked_measures)
                else:
                    st.warning("⚠️ No se encontraron medidas en el archivo PBIP")
    
            except Exception as e:
                st.error(f"❌ Error al analizar el archivo: {str(e)}")
    
            finally:
                # Limpiar archivo temporal si se creó
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
    
        else:
            # Mostrar instrucciones si no hay archivo
            st.info("""
            👆 **¡Listo para analizar!** Proporciona la ruta al archivo .pbip para comenzar.
    
            **Recuerda:** Puedes pegar la ruta al archivo `.pbip` con o sin comillas.
            La aplicación se encargará de buscar la carpeta `.SemanticModel` automáticamente.
            """)
    
            # Ejemplo visual de cómo funciona
            st.markdown("""
            <div style="background: rgba(4,81,228,0.06); border: 1px solid rgba(4,81,228,0.20);
                        border-left: 3px solid #0451E4; border-radius: 6px;
                        padding: 1.15rem 1.5rem; margin-top: 1.5rem;
                        font-family: 'Fira Sans', sans-serif;">
                <h4 style="color: #F1F5F9; margin: 0 0 0.75rem 0; font-size: 1rem; font-weight: 700;">
                    💡 Ejemplo de uso
                </h4>
                <ol style="color: #CBD5E1; margin: 0; padding-left: 1.25rem; line-height: 1.75;">
                    <li><strong style="color:#F1F5F9;">Copia la ruta de tu archivo PBIP</strong> desde el explorador de Windows</li>
                    <li><strong style="color:#F1F5F9;">Pégala en el campo de arriba</strong> (con o sin comillas)</li>
                    <li><strong style="color:#F1F5F9;">La aplicación procesará automáticamente</strong> todas las medidas DAX</li>
                    <li><strong style="color:#F1F5F9;">Revisa los resultados</strong> y exporta el análisis</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)

    # Ejecutar la aplicación
    main()

    if __name__ == "__main__":
        main()
