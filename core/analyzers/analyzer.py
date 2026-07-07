"""Main Power BI analyzer - orchestrates parsing, analysis and scoring."""

import json
import os

import yaml

from core.models import (
    AnalysisResult, ColumnDetail, FileType, MeasureDetail, MetricScore,
    PageDetail, Recommendation, RelationshipDetail, ScoreCategory, Severity,
    VisualDetail,
)
from core.analyzers.storage_mode import analyze_storage
from core.parsers.pbip_parser import PBIPParser
from core.parsers.pbix_parser import PBIXParser


class PowerBIAnalyzer:
    """Unified analyzer for PBIX and PBIP files."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config", "thresholds.yaml",
            )
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def analyze(self, path: str) -> AnalysisResult:
        """Analyze a Power BI file or project folder."""
        file_type = self._detect_file_type(path)

        if file_type == FileType.PBIX:
            parser = PBIXParser(path)
            parsed = parser.parse()
            model_size = parser.get_model_size_mb()
            model_size_source = "pbix_zip"
        else:
            parser = PBIPParser(path)
            parsed = parser.parse()
            # NOTA: En PBIP la carpeta solo contiene metadatos (TMDL/JSON), NO los datos.
            # El tamaño real del modelo (datos comprimidos VertiPaq) NO está disponible.
            # Reportamos None para no engañar - el usuario debe verificarlo en el servicio.
            model_size = None
            model_size_source = "pbip_metadata_only"

        result = AnalysisResult(
            report_name=os.path.basename(path),
            report_path=path,
            file_type=file_type,
            model_analysis_available=parsed.get("model_available", False),
            model_analysis_note=parsed.get("model_note", ""),
            model_size_mb=model_size if model_size is not None else 0,
            model_size_source=model_size_source,
        )

        # Store raw data for fixers
        result._raw_report_data = parsed.get("layout", {})
        result._raw_model_data = parsed.get("model", {})
        if file_type == FileType.PBIP:
            result._report_base_path = parsed.get("report_base_path", "")
            result._model_base_path = parsed.get("model_base_path", "")

        # Analyze report
        layout = parsed.get("layout", {})
        if layout:
            self._analyze_report(result, layout, parsed)

        # Analyze model
        model = parsed.get("model", {})
        if model and parsed.get("model_available", False):
            self._analyze_model(result, model)

        # Calculate scores and recommendations
        self._calculate_scores(result)
        self._generate_recommendations(result)

        return result

    def _detect_file_type(self, path: str) -> FileType:
        if os.path.isfile(path) and path.lower().endswith(".pbix"):
            return FileType.PBIX
        return FileType.PBIP

    @staticmethod
    def resolve_path(raw_path: str) -> str:
        """Intelligently resolve any user-provided path to the correct analysis target.

        Accepts:
        - .pbix file path
        - .pbip file path (finds sibling .Report folder)
        - .Report folder path (direct)
        - Parent folder containing .Report subfolder
        - Any folder with definition/pages structure (PBIR)
        """
        path = raw_path.strip().strip('"').strip("'").strip()
        path = path.replace("\\", "/").rstrip("/")

        if not os.path.exists(path):
            return path  # Let caller handle the error

        # Direct .pbix file
        if os.path.isfile(path) and path.lower().endswith(".pbix"):
            return path

        # Direct .Report folder
        if os.path.isdir(path) and path.lower().endswith(".report"):
            return path

        # .pbip file — find sibling .Report folder
        if os.path.isfile(path) and path.lower().endswith(".pbip"):
            parent = os.path.dirname(path)
            for item in os.listdir(parent):
                full = os.path.join(parent, item)
                if os.path.isdir(full) and item.lower().endswith(".report"):
                    return full
            return parent  # Fallback to parent

        # Folder — search for .Report subfolder or definition/pages
        if os.path.isdir(path):
            # Check immediate children for .Report
            for item in os.listdir(path):
                full = os.path.join(path, item)
                if os.path.isdir(full) and item.lower().endswith(".report"):
                    return full

            # Check if this IS a PBIR structure (has definition/pages)
            defn = os.path.join(path, "definition")
            if os.path.isdir(defn):
                pages = os.path.join(defn, "pages")
                if os.path.isdir(pages):
                    return path

            # Check for .pbip file in this folder
            for item in os.listdir(path):
                if item.lower().endswith(".pbip"):
                    # Recurse — find .Report sibling
                    for sub in os.listdir(path):
                        full = os.path.join(path, sub)
                        if os.path.isdir(full) and sub.lower().endswith(".report"):
                            return full

            # Check for .pbix in folder
            for item in os.listdir(path):
                if item.lower().endswith(".pbix"):
                    return os.path.join(path, item)

        return path

    # ── Report Analysis ──────────────────────────────────────────────

    def _analyze_report(self, result: AnalysisResult, layout: dict, parsed: dict):
        sections = layout.get("sections", [])
        result.total_pages = len(sections)

        all_visual_types = {}
        total_visuals = 0
        total_filters = 0
        max_vis = 0
        max_vis_page = ""
        max_filt = 0
        max_filt_page = ""

        for section in sections:
            page_name = section.get("displayName", section.get("name", ""))
            containers = section.get("visualContainers", [])
            vis_count = len(containers)
            total_visuals += vis_count

            # Count page-level filters
            page_filters = self._count_filters(section)
            total_filters += page_filters

            # Track max
            if vis_count > max_vis:
                max_vis = vis_count
                max_vis_page = page_name
            if page_filters > max_filt:
                max_filt = page_filters
                max_filt_page = page_name

            # Page visibility
            visibility = section.get("visibility", 0)
            is_hidden = visibility == 1
            # Tooltip detection
            page_config = self._safe_json(section.get("config", "{}"))
            is_tooltip = page_config.get("visibility", 0) == 1 or \
                         str(page_config.get("type", "")).lower() == "tooltip"

            if is_hidden:
                result.hidden_pages_count += 1
            if is_tooltip:
                result.tooltip_pages_count += 1

            page_visual_types = {}
            page_visuals = []

            for container in containers:
                vtype, visual_detail = self._analyze_visual(container, page_name)
                page_visuals.append(visual_detail)
                result.visuals_detail.append(visual_detail)
                if vtype:
                    all_visual_types[vtype] = all_visual_types.get(vtype, 0) + 1
                    page_visual_types[vtype] = page_visual_types.get(vtype, 0) + 1
                    # Count specific types
                    vtype_lower = vtype.lower()
                    if "slicer" in vtype_lower:
                        result.slicers_count += 1
                    elif "button" in vtype_lower or "actionButton" in vtype_lower:
                        result.buttons_count += 1
                    elif "shape" in vtype_lower:
                        result.shapes_count += 1
                    elif "textbox" in vtype_lower:
                        result.textboxes_count += 1
                    elif "image" in vtype_lower:
                        result.images_count += 1

            result.pages_detail.append(PageDetail(
                name=page_name,
                visuals_count=vis_count,
                filters_count=page_filters,
                hidden=is_hidden,
                tooltip=is_tooltip,
                width=section.get("width", 0),
                height=section.get("height", 0),
                visual_types=page_visual_types,
            ))

        result.total_visuals = total_visuals
        result.total_filters = total_filters
        result.max_visuals_per_page = max_vis
        result.max_visuals_page_name = max_vis_page
        result.max_filters_per_page = max_filt
        result.max_filters_page_name = max_filt_page
        result.visual_types = all_visual_types

        if result.total_pages > 0:
            result.avg_visuals_per_page = round(total_visuals / result.total_pages, 1)
            result.avg_filters_per_page = round(total_filters / result.total_pages, 1)

        # Custom visuals
        result.custom_visuals_list = parsed.get("custom_visuals", [])
        result.custom_visuals_count = len(result.custom_visuals_list)

        # Embedded images
        result.embedded_images_list = parsed.get("embedded_images", [])
        result.embedded_images_count = len(result.embedded_images_list)
        result.embedded_images_mb = sum(
            img.get("size_kb", 0) for img in result.embedded_images_list
        ) / 1024

        # Bookmarks
        bookmarks = layout.get("bookmarks", [])
        if isinstance(bookmarks, list):
            result.bookmarks_count = len(bookmarks)
            result.bookmarks_detail = bookmarks

        # Theme
        config = self._safe_json(layout.get("config", "{}"))
        theme_data = config.get("theme", config.get("themeData", {}))
        if theme_data:
            result.has_custom_theme = True
            if isinstance(theme_data, dict):
                result.theme_name = theme_data.get("name", "Custom")

    def _analyze_visual(self, container: dict, page_name: str) -> tuple:
        """Analyze a single visual container. Returns (visual_type, VisualDetail)."""
        config = self._safe_json(container.get("config", "{}"))

        # Extract visual type
        vtype = ""
        single_visual = config.get("singleVisual", {})
        if single_visual:
            vtype = single_visual.get("visualType", "")
        elif config.get("singleVisualGroup"):
            vtype = "visualGroup"

        # Extract position
        x = container.get("x", config.get("layouts", [{}])[0].get("position", {}).get("x", 0) if config.get("layouts") else 0)
        y = container.get("y", 0)
        w = container.get("width", container.get("w", 0))
        h = container.get("height", container.get("h", 0))

        # For PBIR format, position might be nested
        pos = config.get("position", {})
        if pos:
            x = pos.get("x", x)
            y = pos.get("y", y)
            w = pos.get("width", w)
            h = pos.get("height", h)

        filters = self._safe_json(container.get("filters", "[]"))
        filter_count = len(filters) if isinstance(filters, list) else 0

        detail = VisualDetail(
            visual_id=container.get("_visual_id", ""),
            visual_type=vtype,
            page_name=page_name,
            x=x, y=y, width=w, height=h,
            filters=filters if isinstance(filters, list) else [],
        )

        return vtype, detail

    def _count_filters(self, section: dict) -> int:
        """Count filters on a page section."""
        filters = self._safe_json(section.get("filters", "[]"))
        return len(filters) if isinstance(filters, list) else 0

    # ── Model Analysis ───────────────────────────────────────────────

    def _analyze_model(self, result: AnalysisResult, model: dict):
        model_data = model.get("model", model)
        all_tables = model_data.get("tables", [])
        relationships = model_data.get("relationships", [])

        # Categorizar tablas con precisión
        tables_by_type = {
            "user": [],
            "calculated": [],
            "auto_datetime_template": [],
            "auto_datetime_local": [],
            "system_hidden": [],
        }
        for t in all_tables:
            ttype = t.get("tableType", "user")
            # Si tmdl_parser no categorizó (fallback por nombre)
            tname = t.get("name", "")
            if ttype == "user":
                if tname.startswith("LocalDateTable_"):
                    ttype = "auto_datetime_local"
                    t["tableType"] = ttype
                    t["isSystemTable"] = True
                elif tname.startswith("DateTableTemplate_"):
                    ttype = "auto_datetime_template"
                    t["tableType"] = ttype
                    t["isSystemTable"] = True
                elif t.get("isCalculatedTable"):
                    ttype = "calculated"
                    t["tableType"] = ttype
            tables_by_type.setdefault(ttype, []).append(t)

        # Tablas de usuario reales = user + calculated (creadas por el usuario)
        tables = tables_by_type["user"] + tables_by_type["calculated"]

        result.total_tables = len(tables)
        result.total_relationships = len(relationships)

        # Guardar desglose para reporte y debugging
        result.tables_by_type = {
            "user": len(tables_by_type["user"]),
            "calculated": len(tables_by_type["calculated"]),
            "auto_datetime_template": len(tables_by_type["auto_datetime_template"]),
            "auto_datetime_local": len(tables_by_type["auto_datetime_local"]),
            "system_hidden": len(tables_by_type["system_hidden"]),
        }

        total_measures = 0
        total_columns = 0
        complex_measures = 0
        calc_columns = 0
        calc_tables = 0

        # Iterar SOLO sobre tablas reales del usuario (no automáticas)
        for table in tables:
            tname = table.get("name", "")
            measures = table.get("measures", [])
            columns = table.get("columns", [])

            total_measures += len(measures)
            total_columns += len(columns)
            result.measures_by_table[tname] = [m.get("name", "") for m in measures]
            result.columns_by_table[tname] = len(columns)

            # Analyze measures
            for m in measures:
                expr = m.get("expression", "")
                detail = MeasureDetail(
                    name=m.get("name", ""),
                    table=tname,
                    expression=expr,
                    description=m.get("description", ""),
                    format_string=m.get("formatString", ""),
                )
                result.measures_detail.append(detail)
                if self._is_complex_measure(expr):
                    complex_measures += 1

            # Analyze columns
            for c in columns:
                col_type = c.get("type", "data")
                is_calc = col_type == "calculated" or bool(c.get("expression"))
                detail = ColumnDetail(
                    name=c.get("name", ""),
                    table=tname,
                    data_type=c.get("dataType", ""),
                    is_calculated=is_calc,
                    is_hidden=c.get("isHidden", False),
                    expression=c.get("expression", ""),
                    summarize_by=c.get("summarizeBy", c.get("summarizeBy", "")),
                )
                result.columns_detail.append(detail)
                if is_calc:
                    calc_columns += 1
                    result.calculated_columns_detail.append({
                        "name": c.get("name", ""),
                        "table": tname,
                        "expression_length": len(c.get("expression", "")),
                    })

            # Check calculated table
            if table.get("isCalculatedTable"):
                calc_tables += 1

        result.total_measures = total_measures
        result.total_columns = total_columns
        result.complex_dax_measures = complex_measures
        result.calculated_columns = calc_columns
        result.calculated_tables = calc_tables

        # Analyze relationships
        bidi_count = 0
        for rel in relationships:
            is_bidi = rel.get("crossFilteringBehavior", "").lower() == "bothdirections"
            is_active = rel.get("isActive", True)
            detail = RelationshipDetail(
                from_table=rel.get("fromTable", ""),
                from_column=rel.get("fromColumn", ""),
                to_table=rel.get("toTable", ""),
                to_column=rel.get("toColumn", ""),
                is_bidirectional=is_bidi,
                is_active=is_active,
            )
            result.relationships_detail.append(detail)
            if is_bidi:
                bidi_count += 1
                result.bidirectional_relationships_detail.append({
                    "from": f"{rel.get('fromTable', '')}.{rel.get('fromColumn', '')}",
                    "to": f"{rel.get('toTable', '')}.{rel.get('toColumn', '')}",
                })

        result.bidirectional_relationships = bidi_count

        # Auto date/time detection - usar lista completa de tablas, no solo las filtradas
        auto_dt_count = (tables_by_type["auto_datetime_template"].__len__()
                         + tables_by_type["auto_datetime_local"].__len__())
        result.auto_date_time_enabled = auto_dt_count > 0
        result.auto_date_time_tables_count = auto_dt_count

        # ── Storage mode analysis (Import/DirectQuery/Dual + validaciones) ──
        try:
            storage = analyze_storage(all_tables)
            result.tables_by_mode = storage["tables_by_mode"]
            result.storage_mode_type = storage["storage_mode_type"]
            result.directquery_tables_detail = storage["directquery_tables_detail"]
            result.directquery_issues = storage["directquery_issues"]
            result.query_folding_warnings = storage["query_folding_warnings"]
        except Exception:
            # No dejar que un fallo acá tire el análisis entero
            pass

    def _is_complex_measure(self, expression: str) -> bool:
        """A measure is 'complex' if it uses VAR, CALCULATE with filters, or nested functions."""
        if not expression:
            return False
        expr_upper = expression.upper()
        complexity_keywords = ["VAR ", "CALCULATE(", "CALCULATETABLE(", "SUMX(", "AVERAGEX(",
                               "FILTER(", "ADDCOLUMNS(", "GENERATE(", "SWITCH("]
        return any(kw in expr_upper for kw in complexity_keywords)

    # ── Scoring ──────────────────────────────────────────────────────

    def _calculate_scores(self, result: AnalysisResult):
        thresholds = self.config["thresholds"]
        score_values = self.config["score_values"]

        metric_map = {
            "visualizations_per_page": result.max_visuals_per_page,
            "filters_per_page": result.max_filters_per_page,
            "custom_visuals": result.custom_visuals_count,
            "embedded_images_mb": result.embedded_images_mb,
            "total_pages": result.total_pages,
            "dax_measures_complex": result.complex_dax_measures,
            "tables_in_model": result.total_tables,
            "relationships": result.total_relationships,
            "bidirectional_relationships": result.bidirectional_relationships,
            "calculated_columns": result.calculated_columns,
            "model_size_mb": result.model_size_mb,
        }

        weighted_sum = 0
        total_weight = 0

        for key, thresh in thresholds.items():
            value = metric_map.get(key, 0) or 0
            weight = thresh["weight"]
            good = thresh["good"]
            warning = thresh["warning"]

            if value <= good:
                status = "good"
                score = score_values["good"]
            elif value <= warning:
                status = "warning"
                score = score_values["warning"]
            else:
                status = "critical"
                score = score_values["critical"]

            result.metric_scores[key] = MetricScore(
                value=value,
                status=status,
                score=score,
                threshold_good=good,
                threshold_warning=warning,
                threshold_critical=thresh["critical"],
            )

            # Only include in scoring if model analysis is available (or if it's a report metric)
            model_metrics = {"dax_measures_complex", "tables_in_model", "relationships",
                             "bidirectional_relationships", "calculated_columns", "model_size_mb"}
            if key in model_metrics and not result.model_analysis_available:
                continue

            weighted_sum += score * weight
            total_weight += weight

        if total_weight > 0:
            result.overall_score = round(weighted_sum / total_weight, 1)

        scoring = self.config["scoring"]
        if result.overall_score >= scoring["excellent"]:
            result.score_category = ScoreCategory.EXCELLENT
        elif result.overall_score >= scoring["good"]:
            result.score_category = ScoreCategory.GOOD
        elif result.overall_score >= scoring["warning"]:
            result.score_category = ScoreCategory.WARNING
        else:
            result.score_category = ScoreCategory.POOR

    # ── Recommendations ──────────────────────────────────────────────

    def _generate_recommendations(self, result: AnalysisResult):
        recs = []

        # Threshold-based recommendations
        for key, ms in result.metric_scores.items():
            display_value = round(ms.value, 1) if isinstance(ms.value, float) else ms.value
            if ms.status == "critical":
                desc = self.config["thresholds"][key]["description"]
                recs.append(Recommendation(
                    metric=key, severity=Severity.CRITICAL,
                    message=f"{desc}: valor actual ({display_value}) excede el umbral crítico ({ms.threshold_critical})",
                    current_value=display_value, target_value=ms.threshold_good,
                    fixable=key in self._fixable_metrics(),
                    fixer_id=self._fixer_for_metric(key),
                ))
            elif ms.status == "warning":
                desc = self.config["thresholds"][key]["description"]
                recs.append(Recommendation(
                    metric=key, severity=Severity.WARNING,
                    message=f"{desc}: valor actual ({display_value}) excede el umbral de advertencia ({ms.threshold_warning})",
                    current_value=display_value, target_value=ms.threshold_good,
                    fixable=key in self._fixable_metrics(),
                    fixer_id=self._fixer_for_metric(key),
                ))

        # Additional rules
        if result.bidirectional_relationships > 0:
            recs.append(Recommendation(
                metric="bidirectional_relationships",
                severity=Severity.WARNING,
                message=f"Se detectaron {result.bidirectional_relationships} relaciones bidireccionales. "
                        "Pueden causar ambiguedad y bajo rendimiento.",
                current_value=result.bidirectional_relationships, target_value=0,
                fixable=True, fixer_id="fix_bidirectional",
            ))

        if result.auto_date_time_enabled:
            recs.append(Recommendation(
                metric="auto_date_time",
                severity=Severity.WARNING,
                message="Auto Date/Time está habilitado. Genera tablas ocultas que aumentan el tamaño del modelo.",
                current_value="Habilitado", target_value="Deshabilitado",
            ))

        # ── DirectQuery issues (crítico) ────────────────────────────
        dq_critical = [i for i in result.directquery_issues if i.get("severity") == "critical"]
        if dq_critical:
            recs.append(Recommendation(
                metric="directquery_errors",
                severity=Severity.CRITICAL,
                message=(
                    f"{len(dq_critical)} error(es) crítico(s) en tablas DirectQuery — "
                    "columnas/tablas calculadas que rompen el modelo. Ver sección "
                    "'Storage Mode' del análisis para el detalle."
                ),
                current_value=len(dq_critical), target_value=0,
            ))

        dq_warnings = [i for i in result.directquery_issues if i.get("severity") == "warning"]
        if dq_warnings:
            recs.append(Recommendation(
                metric="directquery_warnings",
                severity=Severity.WARNING,
                message=(
                    f"{len(dq_warnings)} función(es) DAX con soporte limitado en DirectQuery. "
                    "Verificá compatibilidad con tu fuente."
                ),
                current_value=len(dq_warnings), target_value=0,
            ))

        # ── Query folding anti-patterns (crítico para DirectQuery) ──
        if result.query_folding_warnings:
            recs.append(Recommendation(
                metric="query_folding",
                severity=Severity.WARNING,
                message=(
                    f"{len(result.query_folding_warnings)} anti-pattern(s) en M code "
                    "que rompen query folding. En DirectQuery esto es crítico: obliga "
                    "a materializar toda la tabla en memoria."
                ),
                current_value=len(result.query_folding_warnings), target_value=0,
            ))

        # Excessive slicers
        if result.slicers_count > 25:
            recs.append(Recommendation(
                metric="slicers", severity=Severity.CRITICAL,
                message=f"Exceso de slicers ({result.slicers_count}). Impacta rendimiento significativamente.",
                current_value=result.slicers_count, target_value=15,
            ))
        elif result.slicers_count > 15:
            recs.append(Recommendation(
                metric="slicers", severity=Severity.WARNING,
                message=f"Alto número de slicers ({result.slicers_count}). Considere consolidar.",
                current_value=result.slicers_count, target_value=15,
            ))

        # Missing navigation
        if result.total_pages > 5 and result.bookmarks_count == 0 and result.buttons_count == 0:
            recs.append(Recommendation(
                metric="navigation", severity=Severity.INFO,
                message=f"Reporte con {result.total_pages} páginas sin navegación (bookmarks o botones).",
                current_value=0, target_value=1,
            ))

        # No custom theme
        if not result.has_custom_theme and result.total_pages > 1:
            recs.append(Recommendation(
                metric="theme", severity=Severity.INFO,
                message="No se detectó tema personalizado. Use un tema corporativo para consistencia.",
                current_value="Sin tema", target_value="Tema corporativo",
            ))

        # Embedded images
        if result.embedded_images_mb > 5:
            recs.append(Recommendation(
                metric="embedded_images",
                severity=Severity.WARNING,
                message=f"Imágenes embebidas pesan {result.embedded_images_mb:.1f} MB. Considere usar URLs.",
                current_value=f"{result.embedded_images_mb:.1f} MB", target_value="< 1 MB",
            ))

        # Measures without description (BPA)
        measures_no_desc = [m for m in result.measures_detail if not m.description]
        if measures_no_desc and len(measures_no_desc) > 3:
            recs.append(Recommendation(
                metric="measure_descriptions",
                severity=Severity.INFO,
                message=f"{len(measures_no_desc)} medidas sin descripción. Documente para mantenibilidad.",
                current_value=len(measures_no_desc), target_value=0,
                fixable=True, fixer_id="fix_measure_descriptions",
            ))

        # DAX with division operator (BPA)
        measures_with_division = [
            m for m in result.measures_detail
            if m.expression and "/" in m.expression and "DIVIDE(" not in m.expression.upper()
            and "://" not in m.expression
        ]
        if measures_with_division:
            recs.append(Recommendation(
                metric="dax_divide",
                severity=Severity.WARNING,
                message=f"{len(measures_with_division)} medidas usan '/' en vez de DIVIDE(). "
                        "DIVIDE() maneja división por cero automáticamente.",
                current_value=len(measures_with_division), target_value=0,
                fixable=True, fixer_id="fix_divide_operator",
            ))

        # Pie/donut charts (Report BPA)
        pie_types = {"pieChart", "donutChart"}
        pie_count = sum(result.visual_types.get(t, 0) for t in pie_types)
        if pie_count > 0:
            recs.append(Recommendation(
                metric="pie_charts",
                severity=Severity.WARNING,
                message=f"{pie_count} gráficos de torta/dona detectados. "
                        "Barras/columnas son más efectivos para comparar valores.",
                current_value=pie_count, target_value=0,
                fixable=True, fixer_id="fix_pie_charts",
            ))

        # Non-Full HD pages
        non_fhd_pages = [
            p for p in result.pages_detail
            if p.width < 1920 or p.height < 1080
        ]
        if non_fhd_pages and not all(p.tooltip for p in non_fhd_pages):
            regular_non_fhd = [p for p in non_fhd_pages if not p.tooltip]
            if regular_non_fhd:
                recs.append(Recommendation(
                    metric="page_size",
                    severity=Severity.INFO,
                    message=f"{len(regular_non_fhd)} páginas no están en resolución Full HD (1920x1080).",
                    current_value=f"{regular_non_fhd[0].width}x{regular_non_fhd[0].height}",
                    target_value="1920x1080",
                    fixable=True, fixer_id="fix_page_size",
                ))

        # Sort by severity
        severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
        recs.sort(key=lambda r: severity_order.get(r.severity, 99))
        result.recommendations = recs

    def _fixable_metrics(self) -> set:
        return {"bidirectional_relationships", "calculated_columns"}

    def _fixer_for_metric(self, key: str) -> str:
        mapping = {
            "bidirectional_relationships": "fix_bidirectional",
            "calculated_columns": "fix_calculated_columns",
        }
        return mapping.get(key, "")

    @staticmethod
    def _safe_json(data) -> dict | list:
        if isinstance(data, (dict, list)):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}
