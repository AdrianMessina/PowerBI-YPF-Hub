# PBI Hub — Unified Power BI Suite

Unificación de **Power BI Fixer** + **YPF BI Monitor** en una sola app.

## Reglas de deploy (Cloudera)

**El launcher que funciona (NO modificar):**

```python
# launch.py
import os, subprocess, sys
subprocess.run([
    sys.executable, "-m", "streamlit", "run", "app.py",
    "--server.port", os.environ.get("CDSW_APP_PORT", "8501"),
    "--server.address", "127.0.0.1",
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
])
```

Aplican las mismas reglas que Fixer/Monitor:
- `sys.executable -m streamlit` (NO `"streamlit"` directo)
- `127.0.0.1` (NO `0.0.0.0`)
- Sin `--server.enableCORS=false`
- Sin `--server.enableXsrfProtection=false`
- `subprocess.run()` (NO `os.execvp()`)

## Arquitectura

```
pbi_hub/
├── app.py                ← Entry point con sidebar unificado
├── launch.py             ← Cloudera launcher
├── requirements.txt
├── core/                 ← Copia física del core del Fixer
│   ├── parsers/          ← PBIP, PBIX, TMDL
│   ├── analyzers/        ← PowerBIAnalyzer, DeltaAnalyzer, MemoryEstimator
│   ├── fixers/           ← 37 fixers
│   ├── validators/       ← PBIRValidator (post-fix)
│   ├── models.py         ← AnalysisResult
│   ├── environment.py    ← is_cloud(), get_current_user()
│   ├── usage_logger.py
│   └── aggregation_suggester.py
├── ui/                   ← UI del Fixer copiada (styles.py, components.py, tab_*.py)
├── modules/              ← Módulos del Hub (uno por sección del sidebar)
│   ├── home.py
│   ├── analyzer.py       ← Wrapper de tab_overview + tab_metrics + tab_recommendations + tab_export
│   ├── fixer.py          ← Wrapper de tab_fixer (37 auto-fixers)
│   └── (próximos)
├── shared/               ← Utilities compartidas
│   └── loader.py         ← Carga PBIP en session_state, compartido entre módulos
├── config/               ← thresholds.yaml (del Fixer)
└── assets/               ← Logos (del Monitor)
```

## Modelo de carga (session_state)

Un solo upload del PBIP en el sidebar → `st.session_state.project` (AnalysisResult).
Todos los módulos leen desde ahí con `shared.loader.require_project()`.

## Roadmap de módulos

**Sesión 1 (MVP)**: Home, Analyzer, Fixer
**Sesión 2**: DAX Optimizer, Performance Analyzer, DAX Benchmarker
**Sesión 3**: Documentation Generator, Layout Organizer
**Sesión 4**: Tools (Delta, Aggregation, Perspectives, Translations), Memory Estimator, Usage Dashboard

## Reglas de convivencia con Fixer/Monitor

- **NO modificar** `powerbi_fixer_v2` ni `ypf_bi_monitor` — quedan operativos
- El core del Hub es **copia física** (no import cross-project)
- Bug fixes en Fixer/Monitor deben portarse manualmente al Hub

## Para el agente futuro

- El core está copiado del Fixer (más maduro que el del Monitor)
- Los módulos son **wrappers thin** sobre `ui/tab_*.py` — evitan duplicar lógica de renderizado
- Session state: siempre usar `shared.loader` (no acceder a `st.session_state.project` directo desde módulos)
- Al agregar módulos nuevos: crear `modules/<name>.py`, agregar entrada en `app.py` (import + nav + routing)
