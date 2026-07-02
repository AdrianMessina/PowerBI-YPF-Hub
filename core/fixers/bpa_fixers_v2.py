"""Best Practice Analyzer v2 - additional DAX and model quality rules."""

import os
import re
from collections import defaultdict
from core.fixers.base import BaseFixer


class FixMeasureFolders(BaseFixer):
    """Organize measures into display folders by table."""

    fixer_id = "fix_measure_folders"
    name = "Organizar medidas en carpetas"
    description = (
        "Detecta medidas sin displayFolder asignado. Las carpetas organizan "
        "las medidas en el panel de campos, mejorando la usabilidad."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            for measure in table.get("measures", []):
                if not measure.get("displayFolder"):
                    self.issues.append(
                        f"[{tname}] Medida '{measure.get('name', '')}': sin displayFolder"
                    )

        # TMDL check (excluye tablas automáticas por defecto)
        if not self.issues:
            for _, content, tname in self._iter_tmdl_table_files():
                blocks = re.split(r"(?=^\tmeasure\s+')", content, flags=re.MULTILINE)
                for block in blocks:
                    mm = re.match(r"^\tmeasure\s+'([^']+)'", block)
                    if mm and "displayFolder" not in block:
                        self.issues.append(
                            f"[{tname}] Medida '{mm.group(1)}': sin displayFolder"
                        )

    def fix(self):
        model_def = self._get_model_definition_path()

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
            changed = False
            for table in self._iter_user_tables(model):
                tname = table.get("name", "")
                for measure in table.get("measures", []):
                    if not measure.get("displayFolder"):
                        measure["displayFolder"] = "Measures"
                        changed = True
                        self.fixes_applied.append(
                            f"[{tname}] '{measure.get('name', '')}' -> displayFolder: 'Measures'"
                        )
            if changed:
                self._write_json_file(bim_path, data)
                return

        # TMDL format (excluye automáticas)
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            blocks = re.split(r"(?=^\tmeasure\s+')", content, flags=re.MULTILINE)
            new_blocks = []
            for block in blocks:
                mm = re.match(r"^\tmeasure\s+'([^']+)'", block)
                if mm and "displayFolder" not in block:
                    mname = mm.group(1)
                    lines = block.split("\n")
                    new_lines = [lines[0]]
                    inserted = False
                    for line in lines[1:]:
                        if not inserted and line.startswith("\t\t"):
                            new_lines.append("\t\tdisplayFolder: Measures")
                            inserted = True
                        new_lines.append(line)
                    if not inserted:
                        new_lines.insert(1, "\t\tdisplayFolder: Measures")
                    block = "\n".join(new_lines)
                    self.fixes_applied.append(
                        f"[{tname}] '{mname}' -> displayFolder: 'Measures'"
                    )
                new_blocks.append(block)

            new_content = "".join(new_blocks)
            if new_content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)


class FixColumnFolders(BaseFixer):
    """Organize columns into display folders."""

    fixer_id = "fix_column_folders"
    name = "Organizar columnas en carpetas"
    description = (
        "Detecta tablas con muchas columnas (>10) sin displayFolder. "
        "Organizar en carpetas mejora la navegación del modelo."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "threshold"

    MIN_COLUMNS = 10

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            cols = table.get("columns", [])
            if len(cols) <= self.MIN_COLUMNS:
                continue
            no_folder = [c for c in cols if not c.get("displayFolder")]
            if len(no_folder) > self.MIN_COLUMNS:
                self.issues.append(
                    f"[{tname}] {len(no_folder)}/{len(cols)} columnas sin displayFolder "
                    f"(tabla con muchas columnas)"
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixUnreferencedMeasures(BaseFixer):
    """Detect measures not referenced by any other measure or visual."""

    fixer_id = "fix_unreferenced_measures"
    name = "Detectar medidas sin referencias"
    description = (
        "Detecta medidas que no son referenciadas por otras medidas DAX. "
        "Pueden ser medidas huérfanas que se pueden eliminar."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = False
    is_manual = True
    detection_method = "heuristic"

    def scan(self):
        if not self.result.measures_detail:
            return

        # Build a set of all measure names
        all_measures = {m.name for m in self.result.measures_detail}
        # Build a concatenation of all expressions
        all_expressions = " ".join(
            m.expression for m in self.result.measures_detail if m.expression
        )

        for m in self.result.measures_detail:
            # Check if this measure is referenced in any other expression
            # Use [MeasureName] pattern (DAX convention)
            ref_pattern = f"[{m.name}]"
            # Count references (excluding self-reference in its own expression)
            other_expressions = " ".join(
                other.expression for other in self.result.measures_detail
                if other.name != m.name and other.expression
            )
            if ref_pattern not in other_expressions:
                # Could still be used in visuals, so mark as info only
                self.issues.append(
                    f"[{m.table}] Medida '{m.name}': no referenciada por otras medidas"
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"REVISION: {issue}")


class FixExpensiveDAXPatterns(BaseFixer):
    """Detect expensive DAX patterns that hurt performance."""

    fixer_id = "fix_expensive_dax"
    name = "Detectar patrones DAX costosos"
    description = (
        "Detecta patrones DAX conocidos por ser costosos: "
        "FILTER sobre tabla completa, COUNTROWS+FILTER vs CALCULATE, "
        "SUMX sobre tablas grandes, IF+HASONEVALUE vs SWITCH, etc."
    )
    category = "bpa"
    severity = "warning"
    requires_pbip = False
    is_manual = True
    detection_method = "pattern_match"

    EXPENSIVE_PATTERNS = [
        {
            "pattern": r"FILTER\s*\(\s*'?[A-Za-z]",
            "exclude": r"FILTER\s*\(\s*(ALL|VALUES|DISTINCT|SUMMARIZE)",
            "message": "FILTER() sobre tabla completa: use CALCULATE() con filtros directos",
            "id": "FILTER_TABLE",
        },
        {
            "pattern": r"COUNTROWS\s*\(\s*FILTER\s*\(",
            "exclude": None,
            "message": "COUNTROWS(FILTER(...)): reemplace con CALCULATE(COUNTROWS(...), ...)",
            "id": "COUNTROWS_FILTER",
        },
        {
            "pattern": r"IF\s*\(\s*HASONEVALUE\s*\(",
            "exclude": None,
            "message": "IF(HASONEVALUE(...)): considere SELECTEDVALUE() o SWITCH()",
            "id": "IF_HASONEVALUE",
        },
        {
            "pattern": r"SUMX\s*\(\s*FILTER\s*\(",
            "exclude": None,
            "message": "SUMX(FILTER(...)): puede ser costoso. Considere CALCULATE(SUM(...), ...)",
            "id": "SUMX_FILTER",
        },
        {
            "pattern": r"EARLIER\s*\(",
            "exclude": None,
            "message": "EARLIER(): patrón obsoleto, use VAR para mayor claridad y rendimiento",
            "id": "EARLIER",
        },
        {
            "pattern": r"VALUES\s*\(\s*'?[A-Za-z][^)]*\)\s*\)",
            "exclude": None,
            "message": "Contexto: revise si VALUES() necesita ser reemplazado por DISTINCT()",
            "id": "VALUES_CHECK",
        },
        # ── Context transition patterns (iterator + measure / CALCULATE) ──
        {
            "pattern": (
                r"(SUMX|AVERAGEX|COUNTX|MAXX|MINX|MEDIANX|PRODUCTX|RANKX|"
                r"GEOMEANX|STDEVX|VARX)\s*\([^,]+,\s*CALCULATE\s*\("
            ),
            "exclude": None,
            "message": (
                "Transicion de contexto en iterador: CALCULATE() dentro de SUMX/AVERAGEX/etc "
                "se ejecuta una vez por fila (10-100x mas lento). Considere reescribir con "
                "CALCULATE() externo + agregacion simple."
            ),
            "id": "ITERATOR_CALCULATE",
        },
        {
            "pattern": (
                r"(SUMX|AVERAGEX|COUNTX|MAXX|MINX|MEDIANX|PRODUCTX|RANKX|"
                r"GEOMEANX|STDEVX|VARX)\s*\([^,]+,\s*\[[^\]]+\]\s*\)"
            ),
            "exclude": None,
            "message": (
                "Posible transicion de contexto: medida referenciada dentro de un iterador "
                "(SUMX(t, [Medida])). Si [Medida] es una MEDIDA, fuerza CALCULATE implicito "
                "por fila (lento). Si es una columna, esta OK — verifique."
            ),
            "id": "ITERATOR_MEASURE_REF",
        },
    ]

    def scan(self):
        for m in self.result.measures_detail:
            if not m.expression:
                continue
            expr = m.expression
            for rule in self.EXPENSIVE_PATTERNS:
                if re.search(rule["pattern"], expr, re.IGNORECASE):
                    if rule["exclude"] and re.search(rule["exclude"], expr, re.IGNORECASE):
                        continue
                    self.issues.append(
                        f"[{m.table}] Medida '{m.name}': {rule['message']}"
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixMissingRelationships(BaseFixer):
    """Detect potential missing relationships based on column name matching."""

    fixer_id = "fix_missing_relationships"
    name = "Detectar relaciones faltantes"
    description = (
        "Detecta columnas con nombres similares en diferentes tablas que podrían "
        "necesitar una relación (e.g., ProductID en Fact y Dim tables)."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = False
    is_manual = True
    detection_method = "heuristic"

    FK_SUFFIXES = {"id", "key", "code", "fk", "sk"}

    def scan(self):
        # Build map of existing relationships
        existing_rels = set()
        for rel in self.result.relationships_detail:
            existing_rels.add((rel.from_table, rel.from_column))
            existing_rels.add((rel.to_table, rel.to_column))

        # Build map of columns by normalized name
        col_map = defaultdict(list)
        for col in self.result.columns_detail:
            name_lower = col.name.lower().replace(" ", "").replace("_", "")
            # Only consider potential key columns
            if any(name_lower.endswith(s) for s in self.FK_SUFFIXES):
                col_map[name_lower].append((col.table, col.name))

        # Find columns with same name in different tables without a relationship
        for norm_name, locations in col_map.items():
            if len(locations) < 2:
                continue
            for i, (table_a, col_a) in enumerate(locations):
                for table_b, col_b in locations[i + 1:]:
                    if table_a == table_b:
                        continue
                    # Check if relationship already exists
                    if ((table_a, col_a) in existing_rels or
                            (table_b, col_b) in existing_rels):
                        continue
                    self.issues.append(
                        f"'{table_a}'.{col_a} y '{table_b}'.{col_b} "
                        f"comparten nombre pero no tienen relación"
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"REVISION: {issue}")


class FixSortByColumn(BaseFixer):
    """Detect text columns that likely need SortByColumn (e.g., month names)."""

    fixer_id = "fix_sort_by_column"
    name = "Detectar columnas sin SortByColumn"
    description = (
        "Detecta columnas de texto que probablemente necesitan SortByColumn "
        "(e.g., nombres de meses, días de la semana) para ordenar correctamente."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    SORTABLE_PATTERNS = {
        "month": "month number",
        "mes": "numero de mes",
        "day": "day number",
        "dia": "numero de dia",
        "weekday": "day of week number",
        "quarter": "quarter number",
        "trimestre": "numero trimestre",
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            columns = table.get("columns", [])
            col_names = {c.get("name", "").lower() for c in columns}

            for col in columns:
                cname = col.get("name", "")
                dtype = col.get("dataType", "").lower()
                if dtype != "string":
                    continue
                if col.get("sortByColumn"):
                    continue

                cname_lower = cname.lower().replace("_", " ")
                for pattern, _hint in self.SORTABLE_PATTERNS.items():
                    if pattern in cname_lower and "number" not in cname_lower and "num" not in cname_lower:
                        self.issues.append(
                            f"[{tname}] Columna '{cname}': texto que podría necesitar SortByColumn"
                        )
                        break

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixDataCategoryGeo(BaseFixer):
    """Detect columns that should have geographic DataCategory."""

    fixer_id = "fix_data_category_geo"
    name = "Asignar categorías geográficas"
    description = (
        "Detecta columnas que por su nombre podrían ser geográficas "
        "(ciudad, país, latitud, etc.) y necesitan DataCategory para mapas."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    GEO_MAP = {
        "country": "Country", "pais": "Country", "país": "Country",
        "city": "City", "ciudad": "City",
        "state": "StateOrProvince", "estado": "StateOrProvince",
        "provincia": "StateOrProvince", "province": "StateOrProvince",
        "postal": "PostalCode", "zip": "PostalCode",
        "latitude": "Latitude", "latitud": "Latitude", "lat": "Latitude",
        "longitude": "Longitude", "longitud": "Longitude", "lng": "Longitude", "lon": "Longitude",
        "address": "Address", "direccion": "Address", "dirección": "Address",
        "continent": "Continent", "continente": "Continent",
        "region": "StateOrProvince",
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            for col in table.get("columns", []):
                if col.get("dataCategory"):
                    continue
                cname = col.get("name", "")
                cname_lower = cname.lower().replace("_", " ").replace("-", " ")
                words = cname_lower.split()
                for word in words:
                    if word in self.GEO_MAP:
                        self.issues.append(
                            f"[{tname}] Columna '{cname}': podría necesitar "
                            f"DataCategory='{self.GEO_MAP[word]}' para mapas"
                        )
                        break

    def fix(self):
        model_def = self._get_model_definition_path()

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
            changed = False
            for table in self._iter_user_tables(model):
                tname = table.get("name", "")
                for col in table.get("columns", []):
                    if col.get("dataCategory"):
                        continue
                    cname = col.get("name", "")
                    cname_lower = cname.lower().replace("_", " ").replace("-", " ")
                    words = cname_lower.split()
                    for word in words:
                        if word in self.GEO_MAP:
                            col["dataCategory"] = self.GEO_MAP[word]
                            changed = True
                            self.fixes_applied.append(
                                f"[{tname}] '{cname}' -> DataCategory: '{self.GEO_MAP[word]}'"
                            )
                            break
            if changed:
                self._write_json_file(bim_path, data)
                return

        # Fallback: report suggestions
        if not self.fixes_applied:
            self.scan()
            for issue in self.issues:
                self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixRLSPerformance(BaseFixer):
    """Detect Row-Level Security anti-patterns that hurt performance or security."""

    fixer_id = "fix_rls_performance"
    name = "Detectar anti-patrones de RLS"
    description = (
        "Analiza roles de Row-Level Security (RLS) y detecta anti-patrones: "
        "USERNAME() en lugar de USERPRINCIPALNAME(), 'Default Allow' (TRUE()), "
        "LOOKUPVALUE en filtros, RLS sobre tablas fact grandes, "
        "y relaciones bi-direccionales que cruzan tablas con RLS. "
        "Detección únicamente — los fixes requieren revisión manual de seguridad."
    )
    category = "bpa"
    severity = "warning"
    requires_pbip = True
    is_manual = True
    detection_method = "pattern_match"

    # Heuristic: name fragments commonly seen in fact tables
    FACT_TABLE_HINTS = ("fact", "fct_", "f_", "transaction", "ventas", "movimiento", "ledger", "sales")

    def scan(self):
        roles = self._collect_roles()
        if not roles:
            return

        fact_tables = self._guess_fact_tables()
        bidir_tables = self._tables_with_bidirectional_relationships()

        for role in roles:
            rname = role["name"]
            for tperm in role["tablePermissions"]:
                tname = tperm["table"]
                expr = tperm["expression"] or ""
                expr_compact = re.sub(r"\s+", " ", expr).strip()

                # 1) Default Allow — TRUE() as filter (security hole)
                if re.fullmatch(r"\s*TRUE\s*\(\s*\)\s*", expr, re.IGNORECASE):
                    self.issues.append(
                        f"[CRITICO][{rname}/{tname}] 'Default Allow' detectado: "
                        f"filtro = TRUE(). Cualquiera con el rol ve todos los datos. "
                        f"Use FALSE() como default o un filtro explicito."
                    )

                # 2) USERNAME() instead of USERPRINCIPALNAME() — cloud anti-pattern
                if re.search(r"\bUSERNAME\s*\(", expr, re.IGNORECASE) and \
                   not re.search(r"\bUSERPRINCIPALNAME\s*\(", expr, re.IGNORECASE):
                    self.issues.append(
                        f"[{rname}/{tname}] Usa USERNAME(): en Power BI Service devuelve UPN, "
                        f"pero en Desktop devuelve DOMAIN\\User. Use USERPRINCIPALNAME() "
                        f"para consistencia cloud y soporte B2B."
                    )

                # 3) LOOKUPVALUE — should use relationship instead
                if re.search(r"\bLOOKUPVALUE\s*\(", expr, re.IGNORECASE):
                    self.issues.append(
                        f"[{rname}/{tname}] LOOKUPVALUE en RLS: lento por ejecutarse por fila. "
                        f"Reemplace por relacion entre tabla de seguridad y tabla filtrada."
                    )

                # 4) Complex filter with CALCULATE/FILTER nesting — suggest security table
                has_calc = bool(re.search(r"\bCALCULATE\s*\(", expr, re.IGNORECASE))
                has_filter = bool(re.search(r"\bFILTER\s*\(", expr, re.IGNORECASE))
                if has_calc and has_filter:
                    self.issues.append(
                        f"[{rname}/{tname}] Filtro complejo (CALCULATE+FILTER): considere "
                        f"patron de tabla de seguridad con relacion en lugar de logica DAX."
                    )

                # 5) RLS on fact table — should be on dimension and propagate
                if self._looks_like_fact_table(tname, fact_tables):
                    self.issues.append(
                        f"[{rname}/{tname}] RLS aplicado sobre tabla fact: lento en tablas grandes. "
                        f"Aplique el filtro en la dimension correspondiente y deje que se propague."
                    )

                # 6) Bi-directional relationship touches the filtered table
                if tname in bidir_tables:
                    self.issues.append(
                        f"[{rname}/{tname}] Tabla con relacion bi-direccional + RLS: "
                        f"penalizacion de 5-10x en performance. Use relacion unidireccional."
                    )

    def fix(self):
        # Manual fixer: emit each issue as a suggestion, no file writes.
        if not self.issues:
            self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")

    # ── Helpers ──────────────────────────────────────────────────────

    def _collect_roles(self) -> list:
        """Return [{name, tablePermissions: [{table, expression}]}] from TMDL or BIM."""
        roles = []

        # BIM
        model = self.result._raw_model_data or {}
        model_data = model.get("model", model)
        for r in model_data.get("roles", []) or []:
            tps = []
            for tp in r.get("tablePermissions", []) or []:
                tps.append({
                    "table": tp.get("name", ""),
                    "expression": tp.get("filterExpression", "") or "",
                })
            roles.append({"name": r.get("name", ""), "tablePermissions": tps})

        if roles:
            return roles

        # TMDL: roles can live under definition/roles/*.tmdl
        model_def = self._get_model_definition_path()
        roles_dir = os.path.join(model_def, "roles")
        if not os.path.isdir(roles_dir):
            return roles

        for fname in os.listdir(roles_dir):
            if not fname.endswith(".tmdl"):
                continue
            try:
                with open(os.path.join(roles_dir, fname), "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            roles.extend(self._parse_tmdl_roles(content))

        return roles

    @staticmethod
    def _parse_tmdl_roles(content: str) -> list:
        """Parse one or more `role ...` blocks from a TMDL file."""
        out = []
        # Split on top-level `role <name>` lines
        role_blocks = re.split(r"(?m)^role\s+", content)
        for block in role_blocks[1:]:  # first chunk before any `role` is preamble
            name_match = re.match(r"'?([^'\n]+?)'?\s*\n", block)
            if not name_match:
                continue
            rname = name_match.group(1).strip()
            tps = []
            # tablePermission <Table> = <expression up to next tablePermission or end>
            # Expression can be inline (single line) or block (next indented lines).
            tp_iter = re.finditer(
                r"^\s*tablePermission\s+'?([^'=\n]+?)'?\s*=\s*(.*?)(?=^\s*tablePermission\s|\Z)",
                block, re.MULTILINE | re.DOTALL,
            )
            for m in tp_iter:
                tname = m.group(1).strip()
                expr = m.group(2).strip()
                # Strip role-level trailing metadata that may leak in (e.g. annotations)
                expr = re.sub(r"\n\s*annotation\s.*$", "", expr, flags=re.DOTALL)
                tps.append({"table": tname, "expression": expr})
            out.append({"name": rname, "tablePermissions": tps})
        return out

    def _guess_fact_tables(self) -> set:
        """Tables that look like facts by name OR by cardinality (>500k rows if known)."""
        out = set()
        model = self.result._raw_model_data or {}
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            tname_lower = tname.lower()
            if any(h in tname_lower for h in self.FACT_TABLE_HINTS):
                out.add(tname)
                continue
            # Cardinality hint when present in cached metadata
            row_count = table.get("rowCount") or 0
            if isinstance(row_count, (int, float)) and row_count > 500_000:
                out.add(tname)
        return out

    def _looks_like_fact_table(self, table_name: str, fact_tables: set) -> bool:
        if table_name in fact_tables:
            return True
        tn = table_name.lower()
        return any(h in tn for h in self.FACT_TABLE_HINTS)

    def _tables_with_bidirectional_relationships(self) -> set:
        """Tables that participate in a bi-directional relationship."""
        out = set()
        # Cached relationships
        for rel in self.result.relationships_detail or []:
            cross = (getattr(rel, "cross_filtering_behavior", "") or "").lower()
            if "both" in cross:
                for attr in ("from_table", "to_table"):
                    val = getattr(rel, attr, None)
                    if val:
                        out.add(val)

        if out:
            return out

        # TMDL fallback
        model_def = self._get_model_definition_path()
        rel_file = os.path.join(model_def, "relationships.tmdl")
        if not os.path.exists(rel_file):
            return out
        try:
            with open(rel_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return out

        blocks = re.split(r"(?m)^relationship\s", content)
        for block in blocks[1:]:
            if not re.search(r"crossFilteringBehavior:\s*bothDirections", block):
                continue
            for m in re.finditer(r"(?:fromColumn|toColumn):\s*'?([^'.\n]+)'?\.", block):
                out.add(m.group(1).strip())
        return out


class FixUnusedColumns(BaseFixer):
    """Detect columns never referenced by measures, visuals, relationships, or RLS.

    Estático: cruza columnas del modelo contra todas las fuentes de uso
    detectables sin conexión al modelo. Reduce falsos positivos exigiendo
    que la columna no aparezca en NINGUNA fuente.

    NOTA: Es heurística. No detecta uso vía bookmarks, drillthrough custom,
    ni columnas usadas únicamente como labels de slicers fuera del modelo.
    Marca como manual.
    """

    fixer_id = "fix_unused_columns"
    name = "Detectar columnas sin uso"
    description = (
        "Detecta columnas que no aparecen en ninguna medida DAX, visual, "
        "relacion, filtro RLS, sortByColumn ni jerarquia. Las columnas sin "
        "uso consumen memoria innecesariamente. Revisar antes de eliminar."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    # Columnas con estos nombres se asumen como ID/key y no se reportan
    # (suelen ser referenciadas implícitamente por SDK/ofuscación de drillthrough)
    KEY_NAME_HINTS = ("id", "key", "code", "sk", "pk", "fk", "uuid", "guid")

    def scan(self):
        # 1) Recolectar todas las columnas del modelo (excluyendo system tables)
        all_columns = self._collect_user_columns()
        if not all_columns:
            return

        # 2) Recolectar todos los textos donde una columna puede ser referenciada
        all_refs = self._collect_all_references()

        # 3) Recolectar columnas usadas en relaciones (from/to)
        rel_columns = self._columns_in_relationships()

        # 4) Recolectar columnas usadas como sortByColumn o en hierarchies (TMDL/BIM)
        meta_columns = self._columns_in_metadata()

        # 5) Para cada columna, decidir si es candidata a "sin uso"
        for (table_name, col_name, is_hidden) in all_columns:
            full_ref = f"{table_name}.{col_name}".lower()
            if full_ref in rel_columns:
                continue
            if full_ref in meta_columns:
                continue

            # Patrones de referencia DAX
            qualified = re.escape(f"{table_name}[{col_name}]")
            qualified_quoted = re.escape(f"'{table_name}'[{col_name}]")
            unqualified = re.escape(f"[{col_name}]")

            pattern = (
                rf"({qualified}|{qualified_quoted}|(?<![A-Za-z0-9_]){unqualified})"
            )
            if re.search(pattern, all_refs, re.IGNORECASE):
                continue

            # Ignorar nombres claramente de tipo key (alta tasa de FP)
            col_lower = col_name.lower()
            if any(h == col_lower or col_lower.endswith(h) for h in self.KEY_NAME_HINTS):
                continue

            hidden_tag = " (oculta)" if is_hidden else ""
            self.issues.append(
                f"[{table_name}] Columna '{col_name}'{hidden_tag}: sin referencias en "
                f"medidas/visuales/relaciones/RLS. Candidata a eliminar."
            )

    def fix(self):
        if not self.issues:
            self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"REVISION: {issue}")

    # ── Helpers ──────────────────────────────────────────────────────

    def _collect_user_columns(self) -> list:
        """Return [(table_name, column_name, is_hidden), ...] from BIM or TMDL."""
        out = []
        model = self.result._raw_model_data or {}
        model_data = model.get("model", model)

        # BIM path
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            for col in table.get("columns", []) or []:
                cname = col.get("name", "")
                if not cname or cname.startswith("RowNumber-"):
                    continue
                # Excluir columnas auto-generadas de Power BI (year/month/day variations)
                if col.get("isSystem") or col.get("type") == "rowNumber":
                    continue
                out.append((tname, cname, bool(col.get("isHidden", False))))

        if out:
            return out

        # TMDL fallback
        for _, content, tname in self._iter_tmdl_table_files():
            col_iter = re.finditer(
                r"^\tcolumn\s+'?([^'\n=]+?)'?\s*(?:=|$)",
                content, re.MULTILINE,
            )
            for m in col_iter:
                cname = m.group(1).strip()
                # is_hidden si el bloque de la columna contiene isHidden
                # (búsqueda local en las siguientes 10 lineas)
                start = m.end()
                snippet = content[start:start + 500]
                is_hidden = "isHidden" in snippet.split("\n\tcolumn ")[0]
                out.append((tname, cname, is_hidden))

        return out

    def _collect_all_references(self) -> str:
        """Concatena textos donde una columna puede ser referenciada."""
        chunks = []

        # Expresiones de medidas
        for m in self.result.measures_detail or []:
            if m.expression:
                chunks.append(m.expression)

        # Expresiones de columnas calculadas (pueden referenciar otras)
        for col in self.result.calculated_columns_detail or []:
            expr = getattr(col, "expression", "") or ""
            if expr:
                chunks.append(expr)

        # Filtros RLS (TMDL roles + BIM)
        chunks.extend(self._rls_expressions())

        # Contenido de TODOS los visual.json (incluye bindings, queries, filtros)
        try:
            for visual_path, data, _, _ in self._iter_visual_files():
                # Serializar el dict completo a texto para grep
                import json
                chunks.append(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

        # Contenido de page.json (filtros a nivel pagina)
        try:
            for _, data, _ in self._iter_page_files():
                import json
                chunks.append(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

        return " ".join(chunks)

    def _rls_expressions(self) -> list:
        """Devuelve todos los textos de filterExpression de roles RLS."""
        out = []
        model = self.result._raw_model_data or {}
        model_data = model.get("model", model)
        for r in model_data.get("roles", []) or []:
            for tp in r.get("tablePermissions", []) or []:
                expr = tp.get("filterExpression", "")
                if expr:
                    out.append(expr)

        # TMDL
        model_def = self._get_model_definition_path()
        roles_dir = os.path.join(model_def, "roles")
        if os.path.isdir(roles_dir):
            for fname in os.listdir(roles_dir):
                if fname.endswith(".tmdl"):
                    try:
                        with open(os.path.join(roles_dir, fname), "r", encoding="utf-8") as f:
                            out.append(f.read())
                    except Exception:
                        pass
        return out

    def _columns_in_relationships(self) -> set:
        """Devuelve {'table.column'} de columnas usadas en relaciones."""
        out = set()
        for rel in self.result.relationships_detail or []:
            ft = getattr(rel, "from_table", "")
            fc = getattr(rel, "from_column", "")
            tt = getattr(rel, "to_table", "")
            tc = getattr(rel, "to_column", "")
            if ft and fc:
                out.add(f"{ft}.{fc}".lower())
            if tt and tc:
                out.add(f"{tt}.{tc}".lower())
        return out

    def _columns_in_metadata(self) -> set:
        """Columnas referenciadas como sortByColumn o como hierarchy member."""
        out = set()
        model = self.result._raw_model_data or {}
        model_data = model.get("model", model)

        # BIM: si una columna tiene sortByColumn, AMBAS estan en uso
        # (la visible y la que ordena)
        for table in self._iter_user_tables(model_data):
            tname = table.get("name", "")
            for col in table.get("columns", []) or []:
                sort_by = col.get("sortByColumn", "")
                if sort_by:
                    out.add(f"{tname}.{sort_by}".lower())
                    cname = col.get("name", "")
                    if cname:
                        out.add(f"{tname}.{cname}".lower())
            for hier in table.get("hierarchies", []) or []:
                for level in hier.get("levels", []) or []:
                    lcol = level.get("column", "")
                    if lcol:
                        out.add(f"{tname}.{lcol}".lower())

        # TMDL
        for fpath, content, tname in self._iter_tmdl_table_files():
            # Bloques de columna: ^\tcolumn 'Name' ... hasta proxima ^\tcolumn o EOF
            col_blocks = re.split(r"(?m)^\tcolumn\s+", content)
            for block in col_blocks[1:]:
                # Nombre de la columna actual
                cm = re.match(r"'?([^'\n=]+?)'?\s*(?:=|\n)", block)
                if not cm:
                    continue
                cname = cm.group(1).strip()
                # Si tiene sortByColumn dentro del bloque, ambas estan en uso
                sb = re.search(r"sortByColumn:\s*'?([^'\n]+?)'?\s*$",
                               block, re.MULTILINE)
                if sb:
                    out.add(f"{tname}.{cname}".lower())
                    out.add(f"{tname}.{sb.group(1).strip()}".lower())

            # Hierarchy levels: column: 'Col'
            for m in re.finditer(r"^\s+column:\s*'?([^'\n]+?)'?\s*$",
                                 content, re.MULTILINE):
                out.add(f"{tname}.{m.group(1).strip()}".lower())

        return out
