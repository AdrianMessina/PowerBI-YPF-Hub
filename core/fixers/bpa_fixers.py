"""Best Practice Analyzer (BPA) auto-fixers for semantic model."""

import os
import re
from core.fixers.base import BaseFixer


class FixDivideOperator(BaseFixer):
    """Replace '/' division operator with DIVIDE() function in DAX measures."""

    fixer_id = "fix_divide_operator"
    name = "Reemplazar '/' con DIVIDE()"
    description = (
        "Reemplaza el operador de división '/' por la función DIVIDE() en medidas DAX. "
        "DIVIDE() maneja automáticamente la división por cero sin errores."
    )
    category = "bpa"
    severity = "warning"
    requires_pbip = True

    def scan(self):
        for m in self.result.measures_detail:
            if not m.expression:
                continue
            if self._has_raw_division(m.expression):
                self.issues.append(
                    f"[{m.table}] Medida '{m.name}': usa '/' en vez de DIVIDE()"
                )

    def fix(self):
        # Fix in TMDL files
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            content = self._fix_divisions_in_tmdl(content)
            if content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied.append(
                    f"[{tname}] Operadores '/' reemplazados por DIVIDE()"
                )

        # Fix in BIM files
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
                for measure in table.get("measures", []):
                    expr = measure.get("expression", "")
                    if self._has_raw_division(expr):
                        measure["expression"] = self._replace_division(expr)
                        changed = True
                        self.fixes_applied.append(
                            f"[{table.get('name', '')}] Medida '{measure.get('name', '')}': '/' -> DIVIDE()"
                        )
            if changed:
                self._write_json_file(bim_path, data)

    def _strip_noise(self, expr: str) -> str:
        """Strip strings, comments, URLs, and bracketed column refs so the
        remaining text contains only structural DAX. Column refs like
        `Table[USD/BBL]` carry slashes that are NOT division operators."""
        cleaned = re.sub(r'"[^"]*"', '', expr)
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        # Bracketed names: [Column With/Slash], [USD/BBL], etc.
        cleaned = re.sub(r'\[[^\]]*\]', '[]', cleaned)
        # Quoted table names: 'Some/Table'
        cleaned = re.sub(r"'[^']*'", "''", cleaned)
        return cleaned

    def _has_raw_division(self, expr: str) -> bool:
        """Check if expression uses / as a division operator."""
        if not expr:
            return False
        cleaned = self._strip_noise(expr)
        if "DIVIDE(" in cleaned.upper():
            return False
        return bool(re.search(r'[^/]\s*/\s*[^/\*]', cleaned))

    def _replace_division(self, expr: str) -> str:
        """Replace simple A / B patterns with DIVIDE(A, B).

        Handles common DAX patterns:
        - `[Measure] / [Measure]`
        - `[Measure] / 1000000`
        - `SUM(Table[Col]) / NUMBER`
        - `Table[Col] / NUMBER`
        Complex multi-line or nested-function divisors are left alone — the
        fixer should not produce broken DAX from a guess. Those cases get
        reported but require manual review.
        """
        operand = (
            r'(?:'
            r'[\w.]+\[[^\]]+\]'           # Table[Col]
            r'|\[[^\]]+\]'                # [Measure]
            r'|[A-Z_][\w]*\([^()]*\)'     # FUNC(simple args)
            r'|\d+(?:\.\d+)?'             # numeric literal
            r')'
        )
        pattern = rf'({operand})\s*/\s*({operand})'
        prev = None
        out = expr
        # Apply repeatedly so newly-formed DIVIDE() doesn't block adjacent matches
        while prev != out:
            prev = out
            out = re.sub(pattern, r'DIVIDE(\1, \2)', out)
        return out

    def _fix_divisions_in_tmdl(self, content: str) -> str:
        """Fix divisions in TMDL file content."""
        # Find measure blocks and fix divisions in expressions
        lines = content.split("\n")
        result_lines = []
        in_measure = False
        measure_expr_lines = []

        for line in lines:
            if re.match(r"^\tmeasure\s+'", line):
                in_measure = True
            if in_measure and (line.startswith("\tcolumn ") or line.startswith("\tpartition ") or
                               (line.startswith("\tmeasure ") and measure_expr_lines)):
                in_measure = False

            if in_measure and "/" in line and "DIVIDE(" not in line.upper() and "://" not in line:
                line = self._replace_division(line)

            result_lines.append(line)

        return "\n".join(result_lines)


class FixMeasureDescriptions(BaseFixer):
    """Add placeholder descriptions to measures that lack them."""

    fixer_id = "fix_measure_descriptions"
    name = "Agregar descripciones a medidas"
    description = (
        "Agrega descripciones placeholder a medidas DAX que no tienen descripción. "
        "Las descripciones mejoran la documentación y mantenibilidad del modelo."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    def scan(self):
        for m in self.result.measures_detail:
            if not m.description:
                self.issues.append(
                    f"[{m.table}] Medida '{m.name}': sin descripción"
                )

    def fix(self):
        model_def = self._get_model_definition_path()

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
            changed = False
            for table in self._iter_user_tables(model):
                for measure in table.get("measures", []):
                    if not measure.get("description"):
                        measure["description"] = f"Medida: {measure.get('name', '')}"
                        changed = True
                        self.fixes_applied.append(
                            f"[{table.get('name', '')}] Medida '{measure.get('name', '')}': descripción agregada"
                        )
            if changed:
                self._write_json_file(bim_path, data)
                return

        # Try TMDL format — descriptions in TMDL use /// before the object,
        # NOT a `description:` property (which is invalid and breaks Power BI).
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                mm = re.match(r"^\tmeasure\s+'([^']+)'", line)
                if mm:
                    mname = mm.group(1)
                    prev = new_lines[-1] if new_lines else ""
                    if not prev.lstrip().startswith("///"):
                        new_lines.append(f"\t/// Medida: {mname}")
                        self.fixes_applied.append(
                            f"[{tname}] Medida '{mname}': descripción agregada"
                        )
                new_lines.append(line)

            new_content = "\n".join(new_lines)
            if new_content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)


class FixMeasureFormatStrings(BaseFixer):
    """Add format strings to measures that likely need them."""

    fixer_id = "fix_measure_formats"
    name = "Agregar formato a medidas"
    description = (
        "Detecta medidas que probablemente necesitan formato (porcentajes, monedas, etc.) "
        "y sugiere/aplica el formato apropiado basado en el nombre y expresión."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    FORMAT_HINTS = {
        "pct": "#,0.0%",
        "percent": "#,0.0%",
        "porcentaje": "#,0.0%",
        "ratio": "#,0.00",
        "avg": "#,0.00",
        "promedio": "#,0.00",
        "count": "#,0",
        "cantidad": "#,0",
        "qty": "#,0",
    }

    def scan(self):
        for m in self.result.measures_detail:
            if m.format_string:
                continue
            suggested = self._suggest_format(m.name, m.expression)
            if suggested:
                self.issues.append(
                    f"[{m.table}] Medida '{m.name}': sin formato, sugerido: {suggested}"
                )

    def fix(self):
        # Only scan+report for format strings - applying wrong formats is risky
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")

    def _suggest_format(self, name: str, expression: str) -> str:
        name_lower = name.lower()
        for hint, fmt in self.FORMAT_HINTS.items():
            if hint in name_lower:
                return fmt
        return ""


class FixColumnNaming(BaseFixer):
    """Fix column and table naming - trim spaces, capitalize first letter."""

    fixer_id = "fix_column_naming"
    name = "Estandarizar nombres"
    description = (
        "Detecta nombres de tablas, columnas y medidas con espacios extra "
        "o sin capitalización correcta."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    def scan(self):
        # Check tables
        model_data = self.result._raw_model_data
        model = model_data.get("model", model_data)
        for table in model.get("tables", []):
            tname = table.get("name", "")
            if tname != tname.strip():
                self.issues.append(f"Tabla '{tname}': tiene espacios extra")
            for col in table.get("columns", []):
                cname = col.get("name", "")
                if cname != cname.strip():
                    self.issues.append(f"[{tname}] Columna '{cname}': tiene espacios extra")
            for m in table.get("measures", []):
                mname = m.get("name", "")
                if mname != mname.strip():
                    self.issues.append(f"[{tname}] Medida '{mname}': tiene espacios extra")

    def fix(self):
        # Naming fixes in BIM format
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
                trimmed = tname.strip()
                if tname != trimmed:
                    table["name"] = trimmed
                    changed = True
                    self.fixes_applied.append(f"Tabla '{tname}' -> '{trimmed}'")
                for col in table.get("columns", []):
                    cname = col.get("name", "")
                    trimmed = cname.strip()
                    if cname != trimmed:
                        col["name"] = trimmed
                        changed = True
                        self.fixes_applied.append(f"[{table.get('name', '')}] Columna '{cname}' -> '{trimmed}'")
                for m in table.get("measures", []):
                    mname = m.get("name", "")
                    trimmed = mname.strip()
                    if mname != trimmed:
                        m["name"] = trimmed
                        changed = True
                        self.fixes_applied.append(f"[{table.get('name', '')}] Medida '{mname}' -> '{trimmed}'")
            if changed:
                self._write_json_file(bim_path, data)


class FixHideForeignKeys(BaseFixer):
    """Hide foreign key columns that are used in relationships."""

    fixer_id = "fix_hide_foreign_keys"
    name = "Ocultar columnas de FK"
    description = (
        "Oculta las columnas de clave foránea (FK) usadas en relaciones. "
        "Los usuarios finales no necesitan ver estas columnas en los reportes."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    def scan(self):
        # Find all columns used as FK (fromColumn in relationships)
        fk_columns = set()
        for rel in self.result.relationships_detail:
            fk_columns.add((rel.from_table, rel.from_column))

        for col in self.result.columns_detail:
            if (col.table, col.name) in fk_columns and not col.is_hidden:
                self.issues.append(
                    f"[{col.table}] Columna FK '{col.name}' está visible"
                )

    def fix(self):
        fk_columns = set()
        for rel in self.result.relationships_detail:
            fk_columns.add((rel.from_table, rel.from_column))

        if not fk_columns:
            return

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
                for col in table.get("columns", []):
                    cname = col.get("name", "")
                    if (tname, cname) in fk_columns and not col.get("isHidden", False):
                        col["isHidden"] = True
                        changed = True
                        self.fixes_applied.append(
                            f"[{tname}] Columna FK '{cname}' ocultada"
                        )
            if changed:
                self._write_json_file(bim_path, data)
                return

        # TMDL format
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            for _, fk_col in [(t, c) for t, c in fk_columns if t == tname]:
                # Find the column block and add isHidden
                pattern = rf"(\tcolumn\s+'{re.escape(fk_col)}'.*?)(\n\t(?:column|measure|partition)\s|\Z)"
                match = re.search(pattern, content, re.DOTALL)
                if match and "isHidden" not in match.group(1):
                    block = match.group(1)
                    # Insert isHidden after the column declaration line
                    lines = block.split("\n")
                    new_lines = [lines[0], "\t\tisHidden"] + lines[1:]
                    content = content.replace(block, "\n".join(new_lines))
                    self.fixes_applied.append(f"[{tname}] Columna FK '{fk_col}' ocultada")

            if content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)


class FixSummarizeByNone(BaseFixer):
    """Set SummarizeBy to None for non-aggregatable columns."""

    fixer_id = "fix_summarize_by"
    name = "Corregir SummarizeBy"
    description = (
        "Establece SummarizeBy=None en columnas de texto, fecha y claves numéricas "
        "para prevenir agregaciones accidentales en los reportes."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    NON_AGGREGATE_TYPES = {"string", "datetime", "boolean"}  # lower-case for comparison

    def scan(self):
        for col in self.result.columns_detail:
            if col.data_type.lower() in self.NON_AGGREGATE_TYPES:
                if col.summarize_by and col.summarize_by.lower() not in ("none", ""):
                    self.issues.append(
                        f"[{col.table}] Columna '{col.name}' ({col.data_type}): "
                        f"SummarizeBy={col.summarize_by}, debería ser None"
                    )

    def fix(self):
        model_def = self._get_model_definition_path()

        # BIM format
        bim_fixed = False
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
                for col in table.get("columns", []):
                    dt = col.get("dataType", "").lower()
                    sb = col.get("summarizeBy", "").lower()
                    if dt in self.NON_AGGREGATE_TYPES and sb not in ("none", ""):
                        col["summarizeBy"] = "none"
                        changed = True
                        self.fixes_applied.append(
                            f"[{table.get('name', '')}] Columna '{col.get('name', '')}': SummarizeBy -> None"
                        )
            if changed:
                self._write_json_file(bim_path, data)
                bim_fixed = True

        if bim_fixed:
            return

        # TMDL format: walk each table file, parse columns, flip summarizeBy
        # when dataType is string/dateTime/boolean.
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            lines = content.split("\n")
            out = []
            # State: track current column block.
            in_column = False
            col_dtype = ""
            col_name = ""
            col_buffer_start = 0  # not used; we just rewrite line-by-line
            for line in lines:
                col_match = re.match(r"^\tcolumn\s+(?:'([^']+)'|([\w.]+))", line)
                if col_match:
                    in_column = True
                    col_name = col_match.group(1) or col_match.group(2) or ""
                    col_dtype = ""
                    out.append(line)
                    continue
                # End of column block: another top-level decl
                if in_column and re.match(r"^\t(column|measure|partition|annotation|hierarchy)\b", line):
                    in_column = False
                if in_column:
                    dt_match = re.match(r"^\t\tdataType:\s*(\w+)", line)
                    if dt_match:
                        col_dtype = dt_match.group(1).lower()
                    sb_match = re.match(r"^\t\tsummarizeBy:\s*(\w+)", line)
                    if sb_match and col_dtype in self.NON_AGGREGATE_TYPES:
                        sb_val = sb_match.group(1).lower()
                        if sb_val not in ("none", ""):
                            line = "\t\tsummarizeBy: none"
                            self.fixes_applied.append(
                                f"[{tname}] Columna '{col_name}': SummarizeBy -> none"
                            )
                out.append(line)
            new_content = "\n".join(out)
            if new_content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)


class FixFloatingPointTypes(BaseFixer):
    """Detect Double columns that should be Int64 or Decimal."""

    fixer_id = "fix_floating_point"
    name = "Corregir tipos de punto flotante"
    description = (
        "Detecta columnas de tipo Double que por su nombre podrían ser Int64 "
        "(IDs, counts, keys) o Decimal (montos, precios). Double puede causar "
        "errores de precisión en cálculos financieros."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    INT_HINTS = {"id", "key", "code", "count", "qty", "quantity", "num", "number", "year", "month", "day"}
    DECIMAL_HINTS = {"amount", "price", "cost", "total", "revenue", "monto", "precio", "costo", "importe"}

    def scan(self):
        for col in self.result.columns_detail:
            if col.data_type.lower() != "double":
                continue
            name_lower = col.name.lower().replace("_", " ").replace("-", " ")
            words = set(name_lower.split())

            if words & self.INT_HINTS:
                self.issues.append(
                    f"[{col.table}] Columna '{col.name}' (Double): "
                    f"por su nombre, podría ser Int64"
                )
            elif words & self.DECIMAL_HINTS:
                self.issues.append(
                    f"[{col.table}] Columna '{col.name}' (Double): "
                    f"por su nombre, podría ser Decimal para precisión financiera"
                )

    def fix(self):
        # This fixer only reports - changing data types can break queries
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")
