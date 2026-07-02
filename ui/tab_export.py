"""Export tab - generate HTML/JSON reports."""

import json
import streamlit as st
from datetime import datetime

from core.models import AnalysisResult, Severity


def render_export_tab(result: AnalysisResult):
    """Render the export tab."""

    st.markdown("#### Exportar Resultados")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Reporte HTML")
        st.markdown("Genera un reporte HTML completo con todos los hallazgos.")
        html_content = _generate_html_report(result)
        st.download_button(
            label="Descargar Reporte HTML",
            data=html_content,
            file_name=f"PBI_Analysis_{_safe_name(result.report_name)}_{datetime.now():%Y%m%d}.html",
            mime="text/html",
            use_container_width=True,
        )

    with col2:
        st.markdown("##### Datos JSON")
        st.markdown("Exporta los datos crudos del analisis en formato JSON.")
        json_content = _generate_json_export(result)
        st.download_button(
            label="Descargar JSON",
            data=json_content,
            file_name=f"PBI_Analysis_{_safe_name(result.report_name)}_{datetime.now():%Y%m%d}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Preview
    with st.expander("Vista previa del reporte HTML"):
        st.components.v1.html(html_content, height=600, scrolling=True)


def _generate_html_report(result: AnalysisResult) -> str:
    """Generate a standalone HTML report."""
    critical = [r for r in result.recommendations if r.severity == Severity.CRITICAL]
    warnings = [r for r in result.recommendations if r.severity == Severity.WARNING]
    info = [r for r in result.recommendations if r.severity == Severity.INFO]

    recs_html = ""
    for rec in result.recommendations:
        sev = rec.severity.value if isinstance(rec.severity, Severity) else rec.severity
        color = {"critical": "#D13438", "warning": "#F59E0B", "info": "#0078D4"}.get(sev, "#5A6478")
        bg = {"critical": "rgba(209,52,56,0.08)", "warning": "rgba(245,158,11,0.08)", "info": "rgba(0,120,212,0.08)"}.get(sev, "#181D2A")
        fix_badge = ' <span style="background:rgba(16,185,129,0.15);color:#10B981;padding:2px 6px;border-radius:4px;font-size:0.75rem;">Auto-fix</span>' if rec.fixable else ""
        recs_html += f"""
        <div style="padding:8px 12px;margin:4px 0;border-left:3px solid {color};background:{bg};border-radius:6px;">
            <strong style="color:#E8ECF4;">{rec.message}</strong>{fix_badge}
            <div style="font-size:0.85rem;color:#8B95A8;">Actual: {rec.current_value} | Objetivo: {rec.target_value}</div>
        </div>
        """

    pages_rows = ""
    for p in result.pages_detail:
        pages_rows += f"<tr><td>{p.name}</td><td>{p.visuals_count}</td><td>{p.filters_count}</td><td>{p.width}x{p.height}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Power BI Analysis - {result.report_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; color: #E8ECF4; background: #0B0E14; }}
        h1 {{ color: #F2C811; border-bottom: 2px solid #252D3D; padding-bottom: 0.5rem; }}
        h2 {{ color: #F2C811; margin-top: 2rem; }}
        .score {{ font-size: 3rem; font-weight: 800; text-align: center; padding: 1rem; color: #E8ECF4; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem 0; }}
        .metric {{ background: #181D2A; padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid #252D3D; }}
        .metric .value {{ font-size: 1.5rem; font-weight: 700; color: #E8ECF4; }}
        .metric .label {{ font-size: 0.8rem; color: #8B95A8; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #252D3D; color: #E8ECF4; }}
        th {{ background: #181D2A; font-weight: 600; color: #8B95A8; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #252D3D; color: #5A6478; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <h1>Power BI Fixer - Reporte</h1>
    <p><strong>Archivo:</strong> {result.report_name} | <strong>Fecha:</strong> {datetime.now():%Y-%m-%d %H:%M}</p>

    <div class="score">
        Score: {result.overall_score}/100 ({result.score_category.value})
    </div>

    <h2>Metricas Clave</h2>
    <div class="metrics-grid">
        <div class="metric"><div class="value">{result.total_pages}</div><div class="label">Paginas</div></div>
        <div class="metric"><div class="value">{result.total_visuals}</div><div class="label">Visuals</div></div>
        <div class="metric"><div class="value">{result.total_tables}</div><div class="label">Tablas</div></div>
        <div class="metric"><div class="value">{result.total_measures}</div><div class="label">Medidas</div></div>
        <div class="metric"><div class="value">{result.total_relationships}</div><div class="label">Relaciones</div></div>
        <div class="metric"><div class="value">{result.bidirectional_relationships}</div><div class="label">Bidireccionales</div></div>
        <div class="metric"><div class="value">{result.calculated_columns}</div><div class="label">Col. Calculadas</div></div>
        <div class="metric"><div class="value">{result.custom_visuals_count}</div><div class="label">Custom Vis.</div></div>
    </div>

    <h2>Recomendaciones ({len(result.recommendations)})</h2>
    <p>Criticos: {len(critical)} | Advertencias: {len(warnings)} | Informativos: {len(info)}</p>
    {recs_html}

    <h2>Detalle por Pagina</h2>
    <table>
        <tr><th>Pagina</th><th>Visuals</th><th>Filtros</th><th>Tamano</th></tr>
        {pages_rows}
    </table>

    <div class="footer">
        Generado por Power BI Fixer | YPF S.A. - Data Analytics
    </div>
</body>
</html>"""


def _generate_json_export(result: AnalysisResult) -> str:
    """Generate JSON export of analysis results."""
    data = {
        "report_name": result.report_name,
        "report_path": result.report_path,
        "file_type": result.file_type.value,
        "analysis_date": datetime.now().isoformat(),
        "score": {
            "overall": result.overall_score,
            "category": result.score_category.value,
        },
        "metrics": {
            "total_pages": result.total_pages,
            "total_visuals": result.total_visuals,
            "total_tables": result.total_tables,
            "total_tables_note": "Solo tablas del usuario (excluye Auto Date/Time)",
            "tables_by_type": getattr(result, "tables_by_type", {}),
            "total_measures": result.total_measures,
            "total_relationships": result.total_relationships,
            "total_columns": result.total_columns,
            "complex_dax_measures": result.complex_dax_measures,
            "calculated_columns": result.calculated_columns,
            "calculated_tables": result.calculated_tables,
            "bidirectional_relationships": result.bidirectional_relationships,
            "custom_visuals_count": result.custom_visuals_count,
            "embedded_images_mb": round(result.embedded_images_mb, 2),
            "slicers_count": result.slicers_count,
            "bookmarks_count": result.bookmarks_count,
            "auto_date_time_enabled": result.auto_date_time_enabled,
            "auto_date_time_tables_count": getattr(result, "auto_date_time_tables_count", 0),
            "model_size_mb": result.model_size_mb,
            "model_size_source": getattr(result, "model_size_source", "unknown"),
        },
        "metric_scores": {
            k: {"value": ms.value, "status": ms.status, "score": ms.score}
            for k, ms in result.metric_scores.items()
        },
        "recommendations": [
            {
                "metric": r.metric,
                "severity": r.severity.value if isinstance(r.severity, Severity) else r.severity,
                "message": r.message,
                "current_value": str(r.current_value),
                "target_value": str(r.target_value),
                "fixable": r.fixable,
                "fixer_id": r.fixer_id,
            }
            for r in result.recommendations
        ],
        "visual_types": result.visual_types,
        "measures_by_table": result.measures_by_table,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def _safe_name(name: str) -> str:
    """Sanitize filename."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:50]
