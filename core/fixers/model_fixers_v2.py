"""Semantic model fixers v2 - calendar tables, calculation groups, and more."""

import os
import re
from core.fixers.base import BaseFixer


class FixInactiveRelationships(BaseFixer):
    """Detect inactive relationships that may be unnecessary."""

    fixer_id = "fix_inactive_relationships"
    name = "Detectar relaciones inactivas"
    description = (
        "Detecta relaciones marcadas como inactivas. Las relaciones inactivas "
        "solo se usan con USERELATIONSHIP() en DAX. Si no se usan, deben eliminarse."
    )
    category = "model"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    def scan(self):
        # Find inactive relationships
        inactive_rels = []
        for rel in self.result.relationships_detail:
            if not rel.is_active:
                inactive_rels.append(rel)

        if not inactive_rels:
            return

        # Check if USERELATIONSHIP references exist in measures
        all_expressions = " ".join(
            m.expression.upper() for m in self.result.measures_detail if m.expression
        )

        for rel in inactive_rels:
            ref_from = f"'{rel.from_table}'[{rel.from_column}]".upper()
            ref_to = f"'{rel.to_table}'[{rel.to_column}]".upper()
            # Simplified check: see if USERELATIONSHIP is used at all with these columns
            if "USERELATIONSHIP" in all_expressions:
                if ref_from in all_expressions or ref_to in all_expressions:
                    continue  # Likely referenced
            self.issues.append(
                f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}: "
                f"relación inactiva sin referencia USERELATIONSHIP() detectada"
            )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixAutoDateTime(BaseFixer):
    """Detect and recommend disabling Auto Date/Time tables."""

    fixer_id = "fix_auto_datetime"
    name = "Deshabilitar Auto Date/Time"
    description = (
        "Detecta tablas Auto Date/Time generadas automáticamente por Power BI. "
        "Estas tablas ocultas aumentan el tamaño del modelo y deben reemplazarse "
        "por una tabla de calendario explícita."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True
    is_manual = True
    detection_method = "pattern_match"

    AUTO_DT_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        # NO filtrar - este fixer NECESITA ver las tablas automáticas para detectarlas
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            if any(tname.startswith(p) for p in self.AUTO_DT_PREFIXES):
                self.issues.append(
                    f"Tabla Auto Date/Time: '{tname}'. "
                    f"Deshabilitá Auto Date/Time y usá una tabla de calendario."
                )

        # Also check TMDL files - include_system=True para ver las automáticas
        if not self.issues:
            for fpath, content, tname in self._iter_tmdl_table_files(include_system=True):
                if any(tname.startswith(p) for p in self.AUTO_DT_PREFIXES):
                    self.issues.append(
                        f"Tabla Auto Date/Time: '{tname}' en TMDL."
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixCalendarTable(BaseFixer):
    """Generate a Calendar table if none exists."""

    fixer_id = "fix_calendar_table"
    name = "Generar tabla Calendario"
    description = (
        "Detecta si el modelo carece de una tabla de calendario/fecha explícita. "
        "Puede generar una tabla de calendario como calculated table en TMDL o BIM."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True

    CALENDAR_INDICATORS = {
        "calendar", "calendario", "date", "fecha", "dim_date", "dim_fecha",
        "dim_calendar", "dim_calendario", "datetable", "dates",
    }

    CALENDAR_DAX = '''
\t\t\t\tADDCOLUMNS(
\t\t\t\t\tCALENDAR(DATE(2020, 1, 1), DATE(2030, 12, 31)),
\t\t\t\t\t"Year", YEAR([Date]),
\t\t\t\t\t"Month Number", MONTH([Date]),
\t\t\t\t\t"Month Name", FORMAT([Date], "MMMM"),
\t\t\t\t\t"Month Short", FORMAT([Date], "MMM"),
\t\t\t\t\t"Quarter", "Q" & FORMAT([Date], "Q"),
\t\t\t\t\t"Year-Month", FORMAT([Date], "YYYY-MM"),
\t\t\t\t\t"Day of Week", WEEKDAY([Date], 2),
\t\t\t\t\t"Day Name", FORMAT([Date], "DDDD"),
\t\t\t\t\t"Week Number", WEEKNUM([Date], 2),
\t\t\t\t\t"Is Weekend", IF(WEEKDAY([Date], 2) >= 6, TRUE(), FALSE()),
\t\t\t\t\t"Year-Quarter", FORMAT([Date], "YYYY") & "-Q" & FORMAT([Date], "Q")
\t\t\t\t)'''

    CALENDAR_TMDL = '''table Calendar
\tlineageTag: {cal-lineage-tag}

\tcolumn Date
\t\tdataType: dateTime
\t\tformatString: Short Date
\t\tlineageTag: {date-lineage-tag}
\t\tdataCategory: Date
\t\tisKey
\t\tsummarizeBy: none
\t\tsourceColumn: [Date]

\tcolumn Year
\t\tdataType: int64
\t\tlineageTag: {year-lineage-tag}
\t\tsummarizeBy: none
\t\tsourceColumn: [Year]

\tcolumn 'Month Number'
\t\tdataType: int64
\t\tlineageTag: {monthnum-lineage-tag}
\t\tsummarizeBy: none
\t\tsourceColumn: [Month Number]

\tcolumn 'Month Name'
\t\tdataType: string
\t\tlineageTag: {monthname-lineage-tag}
\t\tsortByColumn: 'Month Number'
\t\tsourceColumn: [Month Name]

\tcolumn Quarter
\t\tdataType: string
\t\tlineageTag: {quarter-lineage-tag}
\t\tsourceColumn: [Quarter]

\tcolumn 'Year-Month'
\t\tdataType: string
\t\tlineageTag: {yearmonth-lineage-tag}
\t\tsourceColumn: [Year-Month]

\tpartition Calendar = calculated
\t\tmode: import
\t\tsource =
\t\t\t''' + CALENDAR_DAX

    def scan(self):
        has_calendar = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            # IGNORAR tablas automáticas de Power BI (Auto Date/Time)
            # NO son calendarios "reales" del usuario
            if table.get("isSystemTable", False):
                continue
            tname_raw = table.get("name", "")
            if tname_raw.startswith("LocalDateTable_") or tname_raw.startswith("DateTableTemplate_"):
                continue

            tname = tname_raw.lower().replace(" ", "").replace("_", "")
            if tname in self.CALENDAR_INDICATORS:
                has_calendar = True
                break
            # Check if any column has DataCategory = Date
            for col in table.get("columns", []):
                if col.get("dataCategory", "").lower() == "date":
                    has_calendar = True
                    break
            if has_calendar:
                break

        # Also check TMDL
        if not has_calendar:
            for _, content, tname in self._iter_tmdl_table_files():
                # IGNORAR tablas automáticas
                if tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_"):
                    continue
                if "__PBI_TemplateDateTable" in content:
                    continue

                tname_clean = tname.lower().replace(" ", "").replace("_", "")
                if tname_clean in self.CALENDAR_INDICATORS:
                    has_calendar = True
                    break
                if "dataCategory: Date" in content:
                    has_calendar = True
                    break

        if not has_calendar:
            self.issues.append(
                "No se detectó tabla de calendario en el modelo. "
                "Se recomienda crear una para Time Intelligence."
            )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        # Try TMDL format first
        if os.path.isdir(tables_dir):
            cal_path = os.path.join(tables_dir, "Calendar.tmdl")
            if not os.path.exists(cal_path):
                content = self.CALENDAR_TMDL
                # Generate unique lineage tags
                for tag in ["{cal-lineage-tag}", "{date-lineage-tag}",
                            "{year-lineage-tag}", "{monthnum-lineage-tag}",
                            "{monthname-lineage-tag}", "{quarter-lineage-tag}",
                            "{yearmonth-lineage-tag}"]:
                    content = content.replace(tag, str(uuid.uuid4()))
                with open(cal_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied.append(
                    "Tabla 'Calendar' creada en TMDL con DAX calculated table"
                )
                return

        # Try BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)
            tables = model.get("tables", [])

            cal_table = {
                "name": "Calendar",
                "columns": [
                    {"name": "Date", "dataType": "dateTime",
                     "sourceColumn": "[Date]", "formatString": "Short Date",
                     "dataCategory": "Date", "isKey": True, "summarizeBy": "none"},
                    {"name": "Year", "dataType": "int64",
                     "sourceColumn": "[Year]", "summarizeBy": "none"},
                    {"name": "Month Number", "dataType": "int64",
                     "sourceColumn": "[Month Number]", "summarizeBy": "none"},
                    {"name": "Month Name", "dataType": "string",
                     "sourceColumn": "[Month Name]", "sortByColumn": "Month Number"},
                    {"name": "Quarter", "dataType": "string",
                     "sourceColumn": "[Quarter]"},
                    {"name": "Year-Month", "dataType": "string",
                     "sourceColumn": "[Year-Month]"},
                ],
                "partitions": [{
                    "name": "Calendar",
                    "mode": "import",
                    "source": {
                        "type": "calculated",
                        "expression": self.CALENDAR_DAX.split("\n"),
                    },
                }],
                "isCalculatedTable": True,
            }
            tables.append(cal_table)
            self._write_json_file(bim_path, data)
            self.fixes_applied.append(
                "Tabla 'Calendar' creada en BIM con DAX calculated table"
            )
            return


class FixCalendarRelationships(BaseFixer):
    """Auto-create relationships between Calendar table and fact tables."""

    fixer_id = "fix_calendar_relationships"
    name = "Crear relaciones con tabla Calendar"
    description = (
        "Detecta columnas de fecha en tablas de hechos y crea relaciones automáticas "
        "con la tabla Calendar. Marca Calendar[Date] como columna de fecha principal."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    FACT_TABLE_PREFIXES = ("fct_", "fact_", "dim_")
    DATE_COLUMN_NAMES = ("fecha", "date", "fechakey", "datekey", "timestamp")

    def scan(self):
        # Check if Calendar table exists
        has_calendar = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)

        for table in model_data.get("tables", []):
            if table.get("isSystemTable", False):
                continue
            tname = table.get("name", "").lower().replace(" ", "").replace("_", "")
            if tname in ("calendar", "calendario", "date", "fecha"):
                has_calendar = True
                break

        if not has_calendar:
            self.issues.append(
                "No se detectó tabla Calendar. Ejecutá primero 'Generar tabla Calendario'."
            )
            return

        # Find date columns in fact tables
        date_columns = []
        for table in model_data.get("tables", []):
            if table.get("isSystemTable", False):
                continue
            tname = table.get("name", "")
            # Check if it's a fact table
            if not any(tname.lower().startswith(p) for p in self.FACT_TABLE_PREFIXES):
                continue

            for col in table.get("columns", []):
                cname = col.get("name", "").lower()
                ctype = col.get("dataType", "")
                if ctype == "dateTime" and any(dt in cname for dt in self.DATE_COLUMN_NAMES):
                    date_columns.append((tname, col.get("name")))

        if not date_columns:
            self.issues.append(
                "No se detectaron columnas de fecha en tablas de hechos para relacionar."
            )
            return

        # Check which relationships already exist
        existing_rels = set()
        for rel in model_data.get("relationships", []):
            from_t = rel.get("fromTable", "")
            from_c = rel.get("fromColumn", "")
            existing_rels.add((from_t, from_c))

        for tname, cname in date_columns:
            if (tname, cname) not in existing_rels:
                self.issues.append(
                    f"Crear relación: {tname}[{cname}] → Calendar[Date]"
                )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        rels_file = os.path.join(model_def, "relationships.tmdl")

        # For TMDL format
        if os.path.isdir(model_def):
            # Find date columns to relate
            model = self.result._raw_model_data
            model_data = model.get("model", model)

            date_columns = []
            for table in model_data.get("tables", []):
                if table.get("isSystemTable", False):
                    continue
                tname = table.get("name", "")
                if not any(tname.lower().startswith(p) for p in self.FACT_TABLE_PREFIXES):
                    continue

                for col in table.get("columns", []):
                    cname = col.get("name", "")
                    ctype = col.get("dataType", "")
                    if ctype == "dateTime" and any(dt in cname.lower() for dt in self.DATE_COLUMN_NAMES):
                        date_columns.append((tname, cname))

            # Read existing relationships
            existing_content = ""
            if os.path.exists(rels_file):
                with open(rels_file, "r", encoding="utf-8") as f:
                    existing_content = f.read()

            # Append new relationships
            new_rels = []
            for tname, cname in date_columns:
                rel_name = f"rel_{tname}_{cname}_Calendar"
                if rel_name not in existing_content:
                    new_rels.append(f"""
relationship {rel_name}
\tfromColumn: {tname}.{cname}
\ttoColumn: Calendar.Date
""")

            if new_rels:
                with open(rels_file, "a", encoding="utf-8") as f:
                    f.write("\n".join(new_rels))
                self.fixes_applied.append(
                    f"Creadas {len(new_rels)} relaciones con Calendar table en TMDL"
                )
                return

        # For BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)

            # Find date columns
            date_columns = []
            for table in model.get("tables", []):
                if table.get("isSystemTable", False):
                    continue
                tname = table.get("name", "")
                if not any(tname.lower().startswith(p) for p in self.FACT_TABLE_PREFIXES):
                    continue

                for col in table.get("columns", []):
                    cname = col.get("name", "")
                    ctype = col.get("dataType", "")
                    if ctype == "dateTime" and any(dt in cname.lower() for dt in self.DATE_COLUMN_NAMES):
                        date_columns.append((tname, cname))

            # Create relationships
            if "relationships" not in model:
                model["relationships"] = []

            new_count = 0
            for tname, cname in date_columns:
                # Check if relationship already exists
                exists = any(
                    r.get("fromTable") == tname and r.get("fromColumn") == cname
                    for r in model["relationships"]
                )
                if not exists:
                    model["relationships"].append({
                        "name": f"rel_{tname}_{cname}_Calendar",
                        "fromTable": tname,
                        "fromColumn": cname,
                        "toTable": "Calendar",
                        "toColumn": "Date",
                    })
                    new_count += 1

            if new_count > 0:
                self._write_json_file(bim_path, data)
                self.fixes_applied.append(
                    f"Creadas {new_count} relaciones con Calendar table en BIM"
                )
            return


class FixTimeIntelligenceMeasures(BaseFixer):
    """Generate Time Intelligence measures for existing measures."""

    fixer_id = "fix_time_intelligence_measures"
    name = "Generar medidas Time Intelligence"
    description = (
        "Genera medidas de Time Intelligence (YTD, Prior Year, MTD, YoY%) "
        "para las medidas principales del modelo. Requiere tabla Calendar."
    )
    category = "model"
    severity = "info"
    requires_pbip = True
    is_manual = True

    # Common measure patterns to detect
    MEASURE_PATTERNS = ("total", "sum", "promedio", "average", "count", "cantidad")

    def scan(self):
        # Check if Calendar table exists
        has_calendar = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)

        for table in model_data.get("tables", []):
            if table.get("isSystemTable", False):
                continue
            tname = table.get("name", "").lower().replace(" ", "").replace("_", "")
            if tname in ("calendar", "calendario", "date", "fecha"):
                has_calendar = True
                break

        if not has_calendar:
            self.issues.append(
                "No se detectó tabla Calendar. Ejecutá primero 'Generar tabla Calendario'."
            )
            return

        # Find main measures
        main_measures = []
        for measure in self.result.measures_detail:
            mname_lower = measure.name.lower()
            if any(pattern in mname_lower for pattern in self.MEASURE_PATTERNS):
                # Skip if it's already a TI measure
                if any(suffix in mname_lower for suffix in ("ytd", "mtd", "py", "yoy", "mom")):
                    continue
                main_measures.append(measure.name)

        if not main_measures:
            self.issues.append(
                "No se detectaron medidas principales para generar Time Intelligence."
            )
            return

        self.issues.append(
            f"Se generarán medidas TI para: {', '.join(main_measures[:5])}"
            + (f" y {len(main_measures) - 5} más..." if len(main_measures) > 5 else "")
        )

    def fix(self):
        if not self.issues:
            self.scan()
        if "No se detectó tabla Calendar" in str(self.issues):
            self.fixes_applied.append("MANUAL: Crear tabla Calendar primero")
            return
        if "No se detectaron medidas" in str(self.issues):
            self.fixes_applied.append("MANUAL: No hay medidas principales")
            return

        import uuid
        model_def = self._get_model_definition_path()

        # Find main measures
        main_measures = []
        for measure in self.result.measures_detail:
            mname_lower = measure.name.lower()
            if any(pattern in mname_lower for pattern in self.MEASURE_PATTERNS):
                if any(suffix in mname_lower for suffix in ("ytd", "mtd", "py", "yoy", "mom")):
                    continue
                main_measures.append(measure.name)

        # Generate TI measures for TMDL
        tables_dir = os.path.join(model_def, "tables")
        if os.path.isdir(tables_dir):
            ti_table_path = os.path.join(tables_dir, "_Time Intelligence.tmdl")

            measures_tmdl = [f"table '_Time Intelligence'\n\tlineageTag: {uuid.uuid4()}\n"]

            for mname in main_measures:
                # YTD
                measures_tmdl.append(f"""
\tmeasure '{mname} YTD' = TOTALYTD([{mname}], Calendar[Date])
\t\tlineageTag: {uuid.uuid4()}
\t\tformatString: #,0
""")
                # Prior Year
                measures_tmdl.append(f"""
\tmeasure '{mname} PY' = CALCULATE([{mname}], SAMEPERIODLASTYEAR(Calendar[Date]))
\t\tlineageTag: {uuid.uuid4()}
\t\tformatString: #,0
""")
                # YoY %
                measures_tmdl.append(f"""
\tmeasure '{mname} YoY %' =
\t\tVAR CurrentValue = [{mname}]
\t\tVAR PriorValue = [{mname} PY]
\t\tRETURN
\t\tDIVIDE(CurrentValue - PriorValue, PriorValue)
\t\tlineageTag: {uuid.uuid4()}
\t\tformatString: 0.0%;-0.0%;0.0%
""")

            with open(ti_table_path, "w", encoding="utf-8") as f:
                f.write("\n".join(measures_tmdl))

            self.fixes_applied.append(
                f"Creadas {len(main_measures) * 3} medidas Time Intelligence en tabla '_Time Intelligence'"
            )
            return

        # For BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)
            tables = model.get("tables", [])

            # Find or create _Time Intelligence table
            ti_table = None
            for table in tables:
                if table.get("name") == "_Time Intelligence":
                    ti_table = table
                    break

            if not ti_table:
                ti_table = {
                    "name": "_Time Intelligence",
                    "columns": [],
                    "measures": [],
                }
                tables.append(ti_table)

            if "measures" not in ti_table:
                ti_table["measures"] = []

            # Generate TI measures
            new_count = 0
            for mname in main_measures:
                # YTD
                ti_table["measures"].append({
                    "name": f"{mname} YTD",
                    "expression": f"TOTALYTD([{mname}], Calendar[Date])",
                    "formatString": "#,0",
                })
                # Prior Year
                ti_table["measures"].append({
                    "name": f"{mname} PY",
                    "expression": f"CALCULATE([{mname}], SAMEPERIODLASTYEAR(Calendar[Date]))",
                    "formatString": "#,0",
                })
                # YoY %
                ti_table["measures"].append({
                    "name": f"{mname} YoY %",
                    "expression": [
                        f"VAR CurrentValue = [{mname}]",
                        f"VAR PriorValue = [{mname} PY]",
                        "RETURN",
                        "DIVIDE(CurrentValue - PriorValue, PriorValue)",
                    ],
                    "formatString": "0.0%;-0.0%;0.0%",
                })
                new_count += 3

            self._write_json_file(bim_path, data)
            self.fixes_applied.append(
                f"Creadas {new_count} medidas Time Intelligence en BIM"
            )
            return


class FixMeasureTable(BaseFixer):
    """Create an empty '_Measures' table with a Last Refresh timestamp measure."""

    fixer_id = "fix_measure_table"
    name = "Crear tabla de medidas"
    description = (
        "Crea una tabla '_Measures' dedicada para organizar medidas DAX. "
        "Incluye una medida 'Last Refresh' con timestamp del último refresh."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    MEASURE_TABLE_NAMES = {
        "_measures", "measures", "_medidas", "medidas",
        "_kpis", "kpis", "_calc", "calculations",
    }

    TMDL_CONTENT = '''table _Measures
\tlineageTag: {table-tag}

\t/// Fecha y hora del ultimo refresh del modelo
\tmeasure 'Last Refresh' = NOW()
\t\tformatString: dd/MM/yyyy HH:mm:ss
\t\tlineageTag: {measure-tag}

\tcolumn Value
\t\tdataType: int64
\t\tlineageTag: {col-tag}
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: [Value]

\tpartition _Measures = calculated
\t\tmode: import
\t\tsource = ROW("Value", 0)
'''

    def scan(self):
        has_measure_table = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            # IGNORAR tablas automáticas (no son tablas de medidas reales)
            if table.get("isSystemTable", False):
                continue
            tname_raw = table.get("name", "")
            if tname_raw.startswith("LocalDateTable_") or tname_raw.startswith("DateTableTemplate_"):
                continue

            tname = tname_raw.lower().replace(" ", "")
            if tname in self.MEASURE_TABLE_NAMES:
                has_measure_table = True
                break

        if not has_measure_table:
            for _, _, tname in self._iter_tmdl_table_files():
                if tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_"):
                    continue
                if tname.lower().replace(" ", "") in self.MEASURE_TABLE_NAMES:
                    has_measure_table = True
                    break

        if not has_measure_table and self.result.total_measures > 0:
            self.issues.append(
                "No se detectó tabla dedicada de medidas. "
                "Se recomienda '_Measures' para organizar KPIs y agregar Last Refresh."
            )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "_Measures.tmdl")
            if not os.path.exists(path):
                content = self.TMDL_CONTENT
                for tag in ["{table-tag}", "{measure-tag}", "{col-tag}"]:
                    content = content.replace(tag, str(uuid.uuid4()))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied.append(
                    "Tabla '_Measures' creada con medida 'Last Refresh'"
                )
                return

        # BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)
            tables = model.get("tables", [])
            tables.append({
                "name": "_Measures",
                "columns": [{
                    "name": "Value", "dataType": "int64",
                    "isHidden": True, "summarizeBy": "none",
                    "sourceColumn": "[Value]",
                }],
                "measures": [{
                    "name": "Last Refresh",
                    "expression": "NOW()",
                    "formatString": "dd/MM/yyyy HH:mm:ss",
                    "description": "Fecha y hora del ultimo refresh del modelo",
                }],
                "partitions": [{
                    "name": "_Measures",
                    "mode": "import",
                    "source": {"type": "calculated", "expression": ['ROW("Value", 0)']},
                }],
                "isCalculatedTable": True,
            })
            self._write_json_file(bim_path, data)
            self.fixes_applied.append(
                "Tabla '_Measures' creada con medida 'Last Refresh'"
            )
            return


class FixTimeIntelligenceGroup(BaseFixer):
    """Create a Time Intelligence calculation group."""

    fixer_id = "fix_time_intelligence"
    name = "Crear Calculation Group: Time Intelligence"
    description = (
        "Crea un Calculation Group de Time Intelligence con items: "
        "YTD, QTD, MTD, PY (año anterior), PY YTD, YoY, YoY%. "
        "Requiere tabla de calendario con columna Date marcada."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    CALC_ITEMS = {
        "Current": "SELECTEDMEASURE()",
        "YTD": "CALCULATE(SELECTEDMEASURE(), DATESYTD('Calendar'[Date]))",
        "QTD": "CALCULATE(SELECTEDMEASURE(), DATESQTD('Calendar'[Date]))",
        "MTD": "CALCULATE(SELECTEDMEASURE(), DATESMTD('Calendar'[Date]))",
        "PY": "CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))",
        "PY YTD": "CALCULATE(SELECTEDMEASURE(), DATESYTD(SAMEPERIODLASTYEAR('Calendar'[Date])))",
        "YoY": (
            "VAR _Current = SELECTEDMEASURE()\n"
            "VAR _PY = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))\n"
            "RETURN _Current - _PY"
        ),
        "YoY %": (
            "VAR _Current = SELECTEDMEASURE()\n"
            "VAR _PY = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))\n"
            "RETURN DIVIDE(_Current - _PY, _PY)"
        ),
    }

    @staticmethod
    def _ensure_discourage_implicit_measures(model_def: str, model_base_path: str) -> bool:
        """Ensure the model has `discourageImplicitMeasures: true`.

        Power BI rejects any model that contains a calculation group unless
        this property is set to true. Must be called BEFORE writing a
        calc-group .tmdl file. Returns True if a change was made.

        Handles both TMDL (`definition/model.tmdl`) and BIM (`model.bim`).
        """
        import json as _json

        # TMDL: definition/model.tmdl
        tmdl_path = os.path.join(model_def, "model.tmdl")
        if os.path.exists(tmdl_path):
            try:
                with open(tmdl_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return False
            # If already true, nothing to do
            if re.search(r"^\s*discourageImplicitMeasures:\s*true\b", content, re.MULTILINE):
                return False
            # If set to false, flip to true
            if re.search(r"^\s*discourageImplicitMeasures:\s*\w+", content, re.MULTILINE):
                new_content = re.sub(
                    r"^(\s*)discourageImplicitMeasures:\s*\w+",
                    r"\1discourageImplicitMeasures: true",
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                # Insert as a property of the `model` block. The model declaration
                # is `model <Name>` on the first non-empty non-comment line; its
                # properties are the indented lines immediately following.
                lines = content.split("\n")
                out = []
                inserted = False
                for i, ln in enumerate(lines):
                    out.append(ln)
                    if inserted:
                        continue
                    if re.match(r"^model\s+\S+", ln):
                        # Find first indented property line after this and
                        # insert before any of the model-level child blocks.
                        # Simplest: insert right after the model declaration.
                        out.append("\tdiscourageImplicitMeasures: true")
                        inserted = True
                if not inserted:
                    return False
                new_content = "\n".join(out)

            with open(tmdl_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        # BIM: model.bim / dataset.bim
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue
            try:
                with open(bim_path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
            except Exception:
                continue
            model = data.get("model", data)
            if model.get("discourageImplicitMeasures") is True:
                return False
            model["discourageImplicitMeasures"] = True
            with open(bim_path, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2, ensure_ascii=False)
            return True

        return False

    # Heuristic to detect calc-group files generated by an OLDER buggy version
    # of this fixer (contained `lineageTag` inside calculationItem, which is
    # NOT valid TMDL and breaks Power BI Desktop on open).
    @staticmethod
    def _has_invalid_calcitem_lineagetag(content: str) -> bool:
        in_item = False
        for ln in content.split("\n"):
            stripped = ln.strip()
            if stripped.startswith("calculationItem "):
                in_item = True
                continue
            if in_item:
                if stripped.startswith("calculationItem ") or stripped.startswith("calculationGroup") \
                        or stripped.startswith("column ") or stripped.startswith("table "):
                    in_item = False
                    continue
                if stripped.startswith("lineageTag:"):
                    return True
        return False

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            if table.get("calculationGroup"):
                tname = table.get("name", "").lower()
                if any(kw in tname for kw in ("time", "periodo", "temporal", "intelligence")):
                    return  # Already exists with valid metadata

        # TMDL — only return early if the existing file is VALID
        for _, content, tname in self._iter_tmdl_table_files():
            if "calculationGroup" not in content:
                continue
            if not any(kw in tname.lower() for kw in ("time", "periodo", "temporal", "intelligence")):
                continue
            if self._has_invalid_calcitem_lineagetag(content):
                self.issues.append(
                    f"'{tname}' tiene lineageTag inválido en calculationItem — regenerar"
                )
                return
            return  # valid existing file, nothing to do

        self.issues.append(
            "No se detectó Calculation Group de Time Intelligence. "
            "Se puede crear con YTD, QTD, MTD, PY, YoY, YoY%."
        )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "Time Intelligence.tmdl")
            # If a broken version exists, overwrite it.
            broken = False
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = f.read()
                    broken = self._has_invalid_calcitem_lineagetag(existing)
                except Exception:
                    broken = False
                if not broken:
                    # File is valid, but still make sure the model has
                    # discourageImplicitMeasures: true (required for any calc
                    # group). Older runs may have skipped this.
                    if self._ensure_discourage_implicit_measures(
                        model_def, self.result._model_base_path
                    ):
                        self.fixes_applied.append(
                            "model.tmdl: discourageImplicitMeasures: true "
                            "(requerido para calculation groups)"
                        )
                    return

            # About to write the calc group — enforce the model flag first.
            if self._ensure_discourage_implicit_measures(
                model_def, self.result._model_base_path
            ):
                self.fixes_applied.append(
                    "model.tmdl: discourageImplicitMeasures: true "
                    "(requerido para calculation groups)"
                )

            lines = [f"table 'Time Intelligence'"]
            lines.append(f"\tlineageTag: {uuid.uuid4()}")
            lines.append("")
            lines.append(f"\tcolumn 'Time Calculation'")
            lines.append(f"\t\tdataType: string")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\tsourceColumn: Name")
            lines.append(f"\t\tsummarizeBy: none")
            lines.append("")
            lines.append(f"\tcalculationGroup")
            lines.append(f"\t\tprecedence: 10")
            lines.append("")
            # calculationItem in TMDL: 'Name' = <expression>. NO lineageTag —
            # not allowed by the schema. Multi-line expressions use triple
            # backticks; single-line goes inline after =.
            for item_name, expr in self.CALC_ITEMS.items():
                expr_clean = expr.strip()
                if "\n" in expr_clean:
                    lines.append(f"\t\tcalculationItem '{item_name}' = ```")
                    for el in expr_clean.split("\n"):
                        lines.append(f"\t\t\t{el}")
                    lines.append(f"\t\t\t```")
                else:
                    lines.append(f"\t\tcalculationItem '{item_name}' = {expr_clean}")
                lines.append("")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.fixes_applied.append(
                ("Regenerado" if broken else "Creado")
                + f" Calculation Group 'Time Intelligence' con "
                + f"{len(self.CALC_ITEMS)} items"
            )
            return

        self.fixes_applied.append(
            "MANUAL: Crear Calculation Group 'Time Intelligence' manualmente"
        )


class FixUnitsCalcGroup(BaseFixer):
    """Create a Units calculation group for currency/unit conversion."""

    fixer_id = "fix_units_calc_group"
    name = "Crear Calculation Group: Unidades"
    description = (
        "Crea un Calculation Group de Unidades con items: "
        "Valor, Miles (K), Millones (M), Porcentaje. "
        "Permite cambiar la escala de cualquier medida dinámicamente."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    CALC_ITEMS = {
        "Valor": ("SELECTEDMEASURE()", "#,0.00"),
        "Miles (K)": ("DIVIDE(SELECTEDMEASURE(), 1000)", "#,0.0 K"),
        "Millones (M)": ("DIVIDE(SELECTEDMEASURE(), 1000000)", "#,0.00 M"),
        "Porcentaje": ("SELECTEDMEASURE()", "0.0%"),
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            if table.get("calculationGroup"):
                tname = table.get("name", "").lower()
                if any(kw in tname for kw in ("unit", "unidad", "scale", "escala", "format")):
                    return

        # TMDL — only return early if the existing file is VALID.
        # See FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag for context.
        for _, content, tname in self._iter_tmdl_table_files():
            if "calculationGroup" not in content:
                continue
            if not any(kw in tname.lower() for kw in ("unit", "unidad", "scale", "escala")):
                continue
            if FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag(content):
                self.issues.append(
                    f"'{tname}' tiene lineageTag inválido en calculationItem — regenerar"
                )
                return
            return  # valid existing file

        self.issues.append(
            "No se detectó Calculation Group de Unidades. "
            "Permite cambiar escala (K, M, %) dinámicamente."
        )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "Units.tmdl")
            broken = False
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = f.read()
                    broken = FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag(existing)
                except Exception:
                    broken = False
                if not broken:
                    if FixTimeIntelligenceGroup._ensure_discourage_implicit_measures(
                        model_def, self.result._model_base_path
                    ):
                        self.fixes_applied.append(
                            "model.tmdl: discourageImplicitMeasures: true "
                            "(requerido para calculation groups)"
                        )
                    return

            # About to write the calc group — enforce the model flag first.
            if FixTimeIntelligenceGroup._ensure_discourage_implicit_measures(
                model_def, self.result._model_base_path
            ):
                self.fixes_applied.append(
                    "model.tmdl: discourageImplicitMeasures: true "
                    "(requerido para calculation groups)"
                )

            lines = [f"table Units"]
            lines.append(f"\tlineageTag: {uuid.uuid4()}")
            lines.append("")
            lines.append(f"\tcolumn 'Display Unit'")
            lines.append(f"\t\tdataType: string")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\tsourceColumn: Name")
            lines.append(f"\t\tsummarizeBy: none")
            lines.append("")
            lines.append(f"\tcalculationGroup")
            lines.append(f"\t\tprecedence: 5")
            lines.append("")
            # calculationItem: 'Name' = <expression>. NO lineageTag (invalid TMDL).
            for item_name, (expr, fmt) in self.CALC_ITEMS.items():
                lines.append(f"\t\tcalculationItem '{item_name}' = {expr}")
                lines.append(f"\t\t\tformatStringDefinition = \"{fmt}\"")
                lines.append("")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.fixes_applied.append(
                ("Regenerado" if broken else "Creado")
                + f" Calculation Group 'Units' con "
                + f"{len(self.CALC_ITEMS)} items"
            )
            return

        self.fixes_applied.append(
            "MANUAL: Crear Calculation Group 'Units' manualmente"
        )
