"""Fixer tab — User-friendly, trust-focused auto-fix engine.

Design principles applied:
- Progressive disclosure (summary → category → detail on demand)
- Only show fixers WITH issues
- Compact buttons, not giant bars
- Tooltips on metrics explaining what they mean
- Each fixer explains WHAT it does and HOW it will fix
- Validation after every fix
"""

import io
import os
import re
import zipfile
import streamlit as st
from core.models import AnalysisResult, FileType, FixMode
from core.fixers.base import FixerEngine
from core.environment import is_cloud


def _reanalyze_and_rescan(engine, result, scan_key):
    """Re-run analysis from disk so model fixers see updated state, then re-scan.

    Model-side fixers (descriptions, divide, FK, summarizeBy, folders, ...)
    scan `result.measures_detail` / `.relationships_detail` / `.tables_detail`,
    which are snapshots from the INITIAL analysis. Without a re-analysis, the
    re-scan reports the same issues even though the files on disk were fixed.
    """
    analyzer = st.session_state.get("analyzer")
    target_path = (
        getattr(result, "_report_base_path", None)
        or getattr(result, "report_path", None)
    )
    new_result = None
    if analyzer and target_path:
        try:
            new_result = analyzer.analyze(target_path)
            st.session_state.analysis_result = new_result
        except Exception:
            new_result = None

    active = new_result or result
    new_scans = engine.scan_all(active)
    if not active.model_analysis_available:
        new_scans = [s for s in new_scans if s.category != "model"]
    st.session_state[scan_key] = new_scans
    return active


_DOWNLOAD_EXCLUDE_FILE_SUFFIXES = (
    ".bak",
    ".tmp",
    ".swp",
    ".pyc",
)
_DOWNLOAD_EXCLUDE_FILE_NAMES = {
    ".backup_metadata.json",
    "Thumbs.db",
    ".DS_Store",
    "desktop.ini",
}
_DOWNLOAD_EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".vs",
    ".vscode",
}


def _should_exclude_from_download(rel_path: str, name: str) -> bool:
    """Skip junk that piles up between fix runs and bloats the ZIP.

    Matches:
    - .bak / .bak_<timestamp> backups left by editors or older fixers
    - .tmp / .swp scratch files
    - Python / OS metadata (Thumbs.db, .DS_Store, desktop.ini)
    - sibling backup folders that landed inside the project by mistake
      (e.g. *.Report_backup_YYYYMMDD_HHMMSS/...)
    """
    # Path inside any excluded directory?
    parts = rel_path.replace("\\", "/").split("/")
    for p in parts:
        if p in _DOWNLOAD_EXCLUDE_DIR_NAMES:
            return True
        if "_backup_" in p and (p.endswith(".Report") is False):
            # Nested backup directory (e.g. Foo.Report_backup_20260617_*)
            # Sibling backups are outside base_path so won't appear, but if
            # one was accidentally nested, skip it.
            if any(part.startswith(p[:-1]) for part in parts):
                pass  # fallthrough — only block if path starts with a backup dir
            return True
    # Specific file names
    if name in _DOWNLOAD_EXCLUDE_FILE_NAMES:
        return True
    # Suffix match (.bak, .bak_TIMESTAMP both end in .bak* — use startswith on suffix)
    lower = name.lower()
    for suf in _DOWNLOAD_EXCLUDE_FILE_SUFFIXES:
        if lower.endswith(suf):
            return True
    # .bak followed by anything: foo.json.bak_20260616_1140
    if ".bak" in lower:
        # Match a .bak token that's a real suffix marker, not part of a real name
        if re.search(r"\.bak(?:[._-]|$)", lower):
            return True
    return False


def _build_project_zip(base_path: str) -> bytes:
    """Build a ZIP from a project folder for download.

    Includes .Report AND .SemanticModel (siblings in a PBIP layout) but
    EXCLUDES junk files that accumulate between fix runs (.bak*, __pycache__,
    OS metadata) so each download is a clean snapshot of the project.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_path):
            # Prune excluded directories in-place so os.walk doesn't descend
            dirs[:] = [d for d in dirs if d not in _DOWNLOAD_EXCLUDE_DIR_NAMES]
            for f in files:
                fpath = os.path.join(root, f)
                arcname = os.path.relpath(fpath, os.path.dirname(base_path))
                if _should_exclude_from_download(arcname, f):
                    continue
                zf.write(fpath, arcname)
    return buf.getvalue()


def _project_source_path(result) -> str | None:
    """Return the folder to ZIP for download.

    Cloud: the extracted temp dir (contains .Report, .SemanticModel, .pbip).
    Local: the PARENT of the .Report folder, so the ZIP also captures the
    sibling .SemanticModel where the model TMDL lives. Falls back to the
    .Report folder if no sibling exists.
    """
    if is_cloud():
        return st.session_state.get("extracted_path")

    report_base = getattr(result, "_report_base_path", None) or result.report_path
    if not report_base:
        return None
    if not os.path.isdir(report_base):
        report_base = os.path.dirname(report_base)

    model_base = getattr(result, "_model_base_path", None)
    if model_base and os.path.isdir(model_base):
        parent = os.path.dirname(report_base)
        if parent and os.path.dirname(model_base) == parent:
            return parent
    return report_base


# ── Fixer descriptions: what each fixer does in plain language ──
FIXER_EXPLANATIONS = {
    "fix_pie_charts": {
        "what": "Los graficos de torta/dona dificultan comparar valores.",
        "action": "Reemplaza el tipo de visual de pieChart/donutChart a barChart en cada visual.json.",
    },
    "fix_page_size": {
        "what": "Paginas con resolucion menor a Full HD desaprovechan pantallas modernas.",
        "action": "Cambia width/height a 1920x1080 en page.json y escala posiciones de visuals proporcionalmente.",
    },
    "fix_visual_alignment": {
        "what": "Visuals desalineados se ven desprolijos.",
        "action": "Redondea x/y/width/height al multiplo de 8px mas cercano en cada visual.json.",
    },
    "fix_unused_custom_visuals": {
        "what": "Custom visuals registrados pero sin usar agregan peso al archivo.",
        "action": "Elimina la carpeta del custom visual de definition/customVisuals/.",
    },
    "fix_hide_visual_filters": {
        "what": "ShowItemsWithNoData genera queries innecesarias.",
        "action": "Remueve la propiedad showItemsWithNoData de cada visual.json afectado.",
    },
    "fix_duplicate_visuals": {
        "what": "Visuals con misma posicion y tipo son probablemente duplicados accidentales.",
        "action": "Solo reporta. Debe eliminarse manualmente en Power BI Desktop.",
    },
    "fix_overlapping_visuals": {
        "what": "Visuals superpuestos >50% pueden indicar errores de diseno.",
        "action": "Solo reporta. Reposicionar manualmente en Power BI Desktop.",
    },
    "fix_empty_pages": {
        "what": "Paginas sin visuals de datos confunden a los usuarios.",
        "action": "Solo reporta. Evaluar si la pagina debe eliminarse o completarse.",
    },
    "fix_visual_tab_order": {
        "what": "Tab order desordenado afecta accesibilidad (navegacion con teclado).",
        "action": "Reasigna tabOrder en cada visual.json siguiendo patron izquierda-derecha, arriba-abajo.",
    },
    "fix_large_card_count": {
        "what": "Mas de 10 cards por pagina genera muchas queries DAX simultaneas.",
        "action": "Solo reporta. Considere consolidar KPIs en menos cards o usar matrix.",
    },
    "fix_slicer_sync": {
        "what": "Paginas con cantidad de slicers muy distinta al promedio.",
        "action": "Solo reporta. Considere usar sync slicers para consistencia.",
    },
    "fix_bidirectional": {
        "what": "Relaciones bidireccionales causan ambiguedad y bajo rendimiento.",
        "action": "Cambia crossFilteringBehavior de bothDirections a oneDirection en TMDL/BIM.",
    },
    "fix_calculated_columns": {
        "what": "Columnas calculadas con agregaciones podrian ser medidas (menos memoria).",
        "action": "Solo reporta. Convertir manualmente a medida en Power BI Desktop.",
    },
    "fix_inactive_relationships": {
        "what": "Relaciones inactivas sin USERELATIONSHIP() son innecesarias.",
        "action": "Solo reporta. Eliminar manualmente si no se usa con USERELATIONSHIP().",
    },
    "fix_auto_datetime": {
        "what": "Tablas Auto Date/Time ocultas aumentan el tamano del modelo.",
        "action": "Solo reporta. Deshabilitar en Opciones > Carga de datos > Auto Date/Time.",
    },
    "fix_calendar_table": {
        "what": "Sin tabla calendario explicita no se puede usar Time Intelligence.",
        "action": "Crea un archivo Calendar.tmdl con tabla calculada DAX (2020-2030) con Year, Month, Quarter.",
    },
    "fix_measure_table": {
        "what": "Sin tabla dedicada las medidas quedan dispersas entre tablas de datos.",
        "action": "Crea _Measures.tmdl con una medida 'Last Refresh' = NOW().",
    },
    "fix_time_intelligence": {
        "what": "Sin Calculation Group de Time Intelligence hay que duplicar medidas YTD/PY.",
        "action": "Crea 'Time Intelligence.tmdl' con items: YTD, QTD, MTD, PY, YoY, YoY%.",
    },
    "fix_units_calc_group": {
        "what": "Sin Calculation Group de Unidades no se puede cambiar escala dinamicamente.",
        "action": "Crea 'Units.tmdl' con items: Valor, Miles (K), Millones (M), Porcentaje.",
    },
    "fix_divide_operator": {
        "what": "El operador / puede causar errores de division por cero.",
        "action": "Reemplaza patrones [A] / [B] por DIVIDE([A], [B]) en expresiones TMDL/BIM.",
    },
    "fix_measure_descriptions": {
        "what": "Medidas sin descripcion dificultan el mantenimiento del modelo.",
        "action": "Agrega description: 'Medida: [nombre]' en cada medida sin descripcion en TMDL/BIM.",
    },
    "fix_measure_formats": {
        "what": "Medidas sin formato se muestran con decimales arbitrarios.",
        "action": "Solo sugiere formatos basados en el nombre (pct->%, count->#,0).",
    },
    "fix_column_naming": {
        "what": "Nombres con espacios extra se ven mal en el panel de campos.",
        "action": "Elimina espacios al inicio/final de nombres de tablas, columnas y medidas en BIM.",
    },
    "fix_hide_foreign_keys": {
        "what": "Columnas FK visibles confunden a usuarios que no necesitan verlas.",
        "action": "Establece isHidden=true en columnas usadas como fromColumn en relaciones.",
    },
    "fix_summarize_by": {
        "what": "Columnas de texto/fecha con SummarizeBy permiten agregaciones accidentales.",
        "action": "Establece summarizeBy='none' en columnas string/dateTime/boolean en BIM.",
    },
    "fix_floating_point": {
        "what": "Columnas Double para IDs/keys causan errores de precision.",
        "action": "Solo sugiere cambiar tipo a Int64 o Decimal segun el nombre de la columna.",
    },
    "fix_measure_folders": {
        "what": "Medidas sin carpeta se acumulan en la raiz de la tabla.",
        "action": "Agrega displayFolder='Measures' a cada medida sin folder en TMDL/BIM.",
    },
    "fix_column_folders": {
        "what": "Tablas con +10 columnas sin carpetas son dificiles de navegar.",
        "action": "Solo reporta. Organizar manualmente en carpetas logicas.",
    },
    "fix_unreferenced_measures": {
        "what": "Medidas no referenciadas por otras pueden ser huerfanas.",
        "action": "Solo reporta. Verificar si se usan en visuals antes de eliminar.",
    },
    "fix_expensive_dax": {
        "what": "Patrones como FILTER(tabla), COUNTROWS(FILTER(...)) son costosos.",
        "action": "Solo sugiere alternativas mas eficientes (CALCULATE, SELECTEDVALUE, etc).",
    },
    "fix_missing_relationships": {
        "what": "Columnas con nombre similar sin relacion pueden necesitar una.",
        "action": "Solo reporta. Evaluar si la relacion es necesaria para el modelo.",
    },
    "fix_sort_by_column": {
        "what": "Columnas de texto como 'Mes' sin SortByColumn se ordenan alfabeticamente.",
        "action": "Solo sugiere agregar SortByColumn a columnas de nombres temporales.",
    },
    "fix_data_category_geo": {
        "what": "Columnas geograficas sin DataCategory no funcionan con mapas.",
        "action": "Asigna DataCategory (Country, City, etc.) basado en el nombre en BIM.",
    },
}


def render_fixer_tab(result: AnalysisResult):

    if result.file_type == FileType.PBIX:
        st.warning(
            "Auto-fix requiere formato **PBIP/PBIR**. "
            "En Power BI Desktop: Archivo > Guardar como > Proyecto (.pbip)"
        )
        _render_scan_only(result)
        return

    engine = FixerEngine()
    scan_key = f"scan_{result.report_path}"

    if scan_key not in st.session_state:
        st.session_state[scan_key] = None

    # ── Compact action bar ──────────────────────────────────────
    if is_cloud():
        col_scan, col_space = st.columns([1, 3])
        do_restore = False
    else:
        col_scan, col_restore, col_space = st.columns([1, 1, 2])
        with col_restore:
            do_restore = st.button("Restaurar Backup", use_container_width=True)

    with col_scan:
        do_scan = st.button("Escanear", type="primary", use_container_width=True)

    if do_scan:
        with st.spinner("Escaneando..."):
            scans = engine.scan_all(result)
            if not result.model_analysis_available:
                scans = [s for s in scans if s.category != "model"]
            st.session_state[scan_key] = scans
        st.rerun()

    if do_restore:
        _render_restore_ui(engine, result)
        return

    scans = st.session_state.get(scan_key)
    if scans is None:
        st.caption("Presione Escanear para detectar problemas corregibles.")
        return

    # ── Classify ────────────────────────────────────────────────
    with_issues = [s for s in scans if s.issues_found > 0]
    passing = [s for s in scans if s.issues_found == 0]
    total_issues = sum(s.issues_found for s in with_issues)

    if not with_issues:
        st.success(f"Sin problemas. {len(passing)} fixers escaneados, todos OK.")
        return

    auto_fixable = [s for s in with_issues if not getattr(s, "is_manual", False)]
    manual_only = [s for s in with_issues if getattr(s, "is_manual", False)]

    # ── Bulk actions: Fix All + Download ────────────────────────
    if auto_fixable or _project_source_path(result):
        col_all, col_dl, _ = st.columns([1.4, 1.4, 1.2])

        with col_all:
            if auto_fixable:
                total_auto = sum(s.issues_found for s in auto_fixable)
                if st.button(
                    f"Aplicar todos ({len(auto_fixable)} fixers · {total_auto} issues)",
                    type="primary",
                    key="fix_all_btn",
                    use_container_width=True,
                ):
                    _apply_all_fixes(engine, auto_fixable, result, scan_key)

        with col_dl:
            src = _project_source_path(result)
            if src and os.path.isdir(src):
                try:
                    zip_bytes = _build_project_zip(src)
                    st.download_button(
                        "Descargar ZIP corregido",
                        data=zip_bytes,
                        file_name=f"{result.report_name}_fixed.zip",
                        mime="application/zip",
                        key="fix_dl_btn",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.caption(f"Descarga no disponible: {e}")

        st.divider()

    # ── Filter state ────────────────────────────────────────────
    filter_key = f"filter_{result.report_path}"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = "all"  # "all" | "auto" | "manual"

    active_filter = st.session_state[filter_key]

    # ── Clickable summary cards ─────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Problemas detectados", total_issues,
            help="Total de issues. Click para ver todos.",
        )
        if st.button(
            "Ver todos" if active_filter != "all" else "Mostrando todos",
            key="filter_all", use_container_width=True,
            disabled=(active_filter == "all"),
        ):
            st.session_state[filter_key] = "all"
            st.rerun()

    with c2:
        st.metric(
            "Auto-corregibles", f"{len(auto_fixable)} fixers",
            help="Fixers que modifican archivos automaticamente. Se crea backup antes de cada correccion.",
        )
        if st.button(
            "Filtrar" if active_filter != "auto" else "Filtro activo",
            key="filter_auto", use_container_width=True,
            disabled=(active_filter == "auto"),
        ):
            st.session_state[filter_key] = "auto"
            st.rerun()

    with c3:
        st.metric(
            "Requieren revision", f"{len(manual_only)} fixers",
            help="Problemas que requieren accion manual en Power BI Desktop.",
        )
        if st.button(
            "Filtrar" if active_filter != "manual" else "Filtro activo",
            key="filter_manual", use_container_width=True,
            disabled=(active_filter == "manual"),
        ):
            st.session_state[filter_key] = "manual"
            st.rerun()

    st.divider()

    # ── Apply filter ────────────────────────────────────────────
    if active_filter == "auto":
        visible = auto_fixable
        st.caption(f"Mostrando {len(visible)} fixers auto-corregibles")
    elif active_filter == "manual":
        visible = manual_only
        st.caption(f"Mostrando {len(visible)} fixers que requieren revision manual")
    else:
        visible = with_issues

    # ── Group by severity → then by category ──────────────────
    by_sev = {"critical": [], "warning": [], "info": []}
    for s in visible:
        sev = getattr(s, "severity", "warning")
        by_sev.get(sev, by_sev["warning"]).append(s)

    cat_labels = {
        "report": "Reporte / Visuals",
        "model": "Modelo Semantico",
        "bpa": "Best Practices",
    }
    cat_order = ["report", "model", "bpa"]

    for sev_key, label in [("critical", "Criticos"), ("warning", "Advertencias"), ("info", "Informativos")]:
        fixers = by_sev[sev_key]
        if not fixers:
            continue

        count = sum(s.issues_found for s in fixers)
        st.markdown(f"**{label}** ({count} issues en {len(fixers)} fixers)")

        # Sub-group by category
        by_cat = {}
        for s in fixers:
            cat = s.category if s.category in cat_labels else "bpa"
            by_cat.setdefault(cat, []).append(s)

        for cat_key in cat_order:
            cat_fixers = by_cat.get(cat_key)
            if not cat_fixers:
                continue

            cat_count = sum(s.issues_found for s in cat_fixers)
            st.caption(f"{cat_labels[cat_key]} ({cat_count})")

            for sr in cat_fixers:
                _render_fixer_item(sr, engine, result, scan_key)

        st.markdown("")

    # ── Passing (collapsed) ─────────────────────────────────────
    if passing and active_filter == "all":
        with st.expander(f"{len(passing)} fixers sin problemas"):
            names = [s.fixer_name for s in passing]
            st.caption(" | ".join(names))


def _render_fixer_item(sr, engine, result, scan_key):
    """Render one fixer as a compact expander with explanation."""
    is_manual = getattr(sr, "is_manual", False)
    explanation = FIXER_EXPLANATIONS.get(sr.fixer_id, {})
    what = explanation.get("what", "")
    action = explanation.get("action", "")

    # Track applied state per fixer in this session
    applied_key = f"applied_{result.report_path}_{sr.fixer_id}"
    was_applied = st.session_state.get(applied_key, False)

    # Build expander label with applied badge
    tag = " [manual]" if is_manual else ""
    applied_badge = " ✓ Aplicado" if was_applied else ""
    label = f"{sr.fixer_name} — {sr.issues_found}{tag}{applied_badge}"

    with st.expander(label):
        # ── Explanation block ───────────────────────────────────
        if what:
            st.markdown(f"**Problema:** {what}")
        if action:
            st.markdown(f"**Correccion:** {action}")

        st.caption(
            f"Categoria: {sr.category.upper()} | "
            f"Confianza: {getattr(sr, 'confidence', 'high').upper()} | "
            f"Deteccion: {getattr(sr, 'detection_method', 'pattern_match')}"
        )

        # ── Issue details (compact, max 8) ──────────────────────
        st.markdown("---")
        shown = min(8, len(sr.details))
        for d in sr.details[:shown]:
            text = d
            for prefix in ("MANUAL:", "SUGERENCIA:", "REVISION:"):
                text = text.replace(prefix, "").strip()
            st.caption(f"  {text}")

        remaining = len(sr.details) - shown
        if remaining > 0:
            st.caption(f"  ... y {remaining} mas")

        # ── Action ──────────────────────────────────────────────
        if not is_manual and result.file_type == FileType.PBIP:
            st.markdown("")
            # Show success indicator if already applied
            if was_applied:
                st.success("✓ Este fix ya fue aplicado en esta sesión")
            if st.button("Corregir", key=f"fix_{sr.fixer_id}", disabled=was_applied):
                _apply_fix(engine, sr, result, scan_key, applied_key)


def _apply_all_fixes(engine, auto_fixable, result, scan_key):
    """Run every auto-fixable fixer in sequence with a single re-scan at the end."""
    if not is_cloud():
        with st.spinner("Creando backup..."):
            try:
                bk = engine.create_backup(
                    result,
                    fixer_ids=[sr.fixer_id for sr in auto_fixable],
                )
                st.caption(f"Backup: `{bk.backup_path}`")
            except Exception as e:
                st.error(f"Error en backup: {e}")
                return

    total = len(auto_fixable)
    applied_ok = 0
    applied_partial = 0
    failed = 0
    total_resolved = 0
    progress = st.progress(0, text=f"Aplicando 0/{total}...")

    for i, sr in enumerate(auto_fixable, start=1):
        progress.progress(i / total, text=f"Aplicando {i}/{total}: {sr.fixer_name}")
        try:
            fr = engine.run_single(sr.fixer_id, result, FixMode.SCAN_AND_FIX)
        except Exception:
            fr = None

        if not fr:
            failed += 1
            continue

        val = fr.validation_result or {}
        if val.get("passed", False):
            applied_ok += 1
            total_resolved += val.get("issues_resolved", fr.issues_fixed or 0)
        elif fr.issues_fixed and fr.issues_fixed > 0:
            applied_partial += 1
            total_resolved += fr.issues_fixed
        else:
            failed += 1

    progress.empty()

    if applied_ok:
        st.success(
            f"Aplicados OK: {applied_ok}/{total} · {total_resolved} issue(s) resueltos."
        )
    if applied_partial:
        st.warning(f"Parciales: {applied_partial}")
    if failed:
        st.error(f"Fallidos: {failed}")

    # Mark all auto-fixable as applied in this session
    for sr in auto_fixable:
        applied_key = f"applied_{result.report_path}_{sr.fixer_id}"
        st.session_state[applied_key] = True

    with st.spinner("Re-analizando..."):
        active = _reanalyze_and_rescan(engine, result, scan_key)

    _render_post_fix_validation(active)

    if is_cloud():
        st.info("Use 'Descargar ZIP corregido' arriba para obtener el proyecto.")
    else:
        st.info("Recargue el proyecto en Power BI Desktop para ver los cambios.")
    st.rerun()


def _render_post_fix_validation(result):
    """Run schema validator on the fixed project; surface blocking issues
    BEFORE the user downloads/opens in Power BI Desktop."""
    try:
        from core.validators import PBIRValidator
    except Exception:
        return
    report_base = getattr(result, "_report_base_path", None)
    model_base = getattr(result, "_model_base_path", None)
    if not report_base and not model_base:
        return
    try:
        validation = PBIRValidator(report_base, model_base).validate()
    except Exception as e:
        st.caption(f"Validador no pudo correr: {e}")
        return

    if validation.is_clean:
        st.success("Validacion de schema: OK. El proyecto deberia abrir en Power BI Desktop sin errores.")
        return

    if validation.blocking:
        st.error(
            f"Validacion encontro {len(validation.blocking)} problema(s) bloqueante(s). "
            f"Power BI Desktop va a rechazar este proyecto al abrirlo."
        )
        with st.expander(f"Ver {len(validation.blocking)} bloqueantes", expanded=True):
            for i in validation.blocking[:30]:
                loc = f"{i.file}:{i.line}" if i.line else i.file
                st.markdown(f"- `{loc}` — {i.message}")
                if i.hint:
                    st.caption(f"  Sugerencia: {i.hint}")
            if len(validation.blocking) > 30:
                st.caption(f"... y {len(validation.blocking) - 30} mas")
    if validation.soft:
        st.warning(f"Validacion: {len(validation.soft)} advertencia(s) no bloqueante(s).")


def _apply_fix(engine, sr, result, scan_key, applied_key=None):
    if not is_cloud():
        with st.spinner("Creando backup..."):
            try:
                bk = engine.create_backup(result, fixer_ids=[sr.fixer_id])
                st.caption(f"Backup: `{bk.backup_path}`")
            except Exception as e:
                st.error(f"Error en backup: {e}")
                return

    with st.spinner("Aplicando..."):
        fr = engine.run_single(sr.fixer_id, result, FixMode.SCAN_AND_FIX)

    if not fr:
        st.error("Error aplicando fix")
        return

    val = fr.validation_result
    if val.get("passed", False):
        st.success(f"Corregido: {val.get('issues_resolved', 0)} problema(s). Validacion OK.")
    else:
        st.warning(
            f"Parcial: {fr.issues_fixed}/{fr.issues_found} corregidos. "
            f"{val.get('issues_remaining', '?')} restantes."
        )

    # Mark as applied in this session
    if applied_key:
        st.session_state[applied_key] = True

    with st.spinner("Re-analizando..."):
        active = _reanalyze_and_rescan(engine, result, scan_key)

    _render_post_fix_validation(active)

    if is_cloud():
        st.info("Use el boton 'Descargar' en el sidebar para obtener el proyecto corregido.")
    else:
        st.info("Recargue en Power BI Desktop para ver los cambios.")
    st.rerun()


def _render_restore_ui(engine, result):
    st.markdown("#### Restaurar Backup")
    backups = engine.list_backups(result.report_path)
    if not backups:
        st.info("No hay backups disponibles.")
        return

    for i, bk in enumerate(backups[:5]):
        with st.expander(f"{bk.created_at[:19]} — {bk.size_mb:.1f} MB", expanded=(i == 0)):
            st.caption(f"`{bk.backup_path}`")
            if bk.applied_fixers:
                st.caption(f"Fixers: {', '.join(bk.applied_fixers[:5])}")
            if st.button("Restaurar", key=f"restore_{i}"):
                target = result._report_base_path or result.report_path
                ok = engine.restore_backup(bk.backup_path, target)
                st.success("Restaurado.") if ok else st.error("Error.")


def _render_scan_only(result):
    engine = FixerEngine()
    if st.button("Escanear (solo lectura)", type="primary"):
        with st.spinner("Escaneando..."):
            scans = engine.scan_all(result)
        with_issues = [s for s in scans if s.issues_found > 0]
        total = sum(s.issues_found for s in with_issues)
        st.markdown(f"**{total} problemas** ({len(with_issues)} fixers, no corregibles en PBIX)")
        for sr in with_issues:
            exp = FIXER_EXPLANATIONS.get(sr.fixer_id, {})
            with st.expander(f"{sr.fixer_name} ({sr.issues_found})"):
                if exp.get("what"):
                    st.markdown(f"**Problema:** {exp['what']}")
                for d in sr.details[:10]:
                    st.caption(f"  {d}")
