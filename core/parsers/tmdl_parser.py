"""TMDL file parser - converts TMDL to BIM-compatible dict."""

import os
import re


class TMDLParser:
    """Parses TMDL (Tabular Model Definition Language) files."""

    def __init__(self, definition_path: str):
        self.definition_path = definition_path
        self.model = {"tables": [], "relationships": []}

    def parse(self) -> dict:
        """Parse all TMDL files and return BIM-compatible model dict."""
        self._parse_tables()
        self._parse_relationships()
        return {"model": self.model}

    def _parse_tables(self):
        tables_dir = os.path.join(self.definition_path, "tables")
        if not os.path.isdir(tables_dir):
            return

        for fname in os.listdir(tables_dir):
            if not fname.endswith(".tmdl"):
                continue
            fpath = os.path.join(tables_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                table = self._parse_table_file(content)
                if table:
                    self.model["tables"].append(table)
            except Exception:
                continue

    def _parse_table_file(self, content: str) -> dict | None:
        lines = content.split("\n")
        if not lines:
            return None

        # Extract table name
        table_name = None
        for line in lines:
            m = re.match(r"^table\s+'([^']+)'", line.strip())
            if not m:
                m = re.match(r'^table\s+"([^"]+)"', line.strip())
            if not m:
                m = re.match(r"^table\s+(\S+)", line.strip())
            if m:
                table_name = m.group(1)
                break

        if not table_name:
            return None

        table = {
            "name": table_name,
            "columns": [],
            "measures": [],
            "partitions": [],
            "isCalculatedTable": False,
            "isHidden": False,
            "isPrivate": False,
            "tableType": "user",
            "isSystemTable": False,
        }

        # Check if hidden
        if re.search(r"^\s+isHidden\s*$", content, re.MULTILINE):
            table["isHidden"] = True

        # Check if private (sistema)
        if re.search(r"^\s+isPrivate\s*$", content, re.MULTILINE):
            table["isPrivate"] = True

        # Marker temporal - el tableType definitivo se asigna al final
        # (después de detectar isCalculatedTable en las partitions)
        is_template = "__PBI_TemplateDateTable" in content
        _temp_is_auto_datetime = (
            is_template
            or table_name.startswith("LocalDateTable_")
            or table_name.startswith("DateTableTemplate_")
        )

        # Extract columns
        col_pattern = re.compile(
            r"^\tcolumn\s+'([^']+)'(?:\s*$|\s)", re.MULTILINE
        )
        col_blocks = re.split(r"(?=^\tcolumn\s+')", content, flags=re.MULTILINE)
        for block in col_blocks:
            cm = re.match(r"^\tcolumn\s+'([^']+)'", block)
            if not cm:
                continue
            col = {
                "name": cm.group(1),
                "dataType": "",  # empty = unknown; only filled when declared
                "isHidden": False,
                "type": "data",
                "summarizeBy": "none",
            }
            # Data type
            dt = re.search(r"dataType:\s*(\w+)", block)
            if dt:
                col["dataType"] = dt.group(1)
            else:
                # Infer from formatString when possible: numeric formats imply
                # numeric type. Avoids treating Field Parameter '*Orden' columns
                # (which omit dataType) as strings.
                fs_match = re.search(r"formatString:\s*(.+)", block)
                if fs_match:
                    fs = fs_match.group(1).strip().lower()
                    if any(c.isdigit() or c in "#0.," for c in fs):
                        col["dataType"] = "int64"
            # Hidden
            if re.search(r"^\s+isHidden\s*$", block, re.MULTILINE):
                col["isHidden"] = True
            # Calculated column (has expression with =)
            expr = re.search(r"expression\s*(?:=|:)\s*(.+?)(?:\n\t\w|\Z)", block, re.DOTALL)
            if expr:
                col["type"] = "calculated"
                col["expression"] = expr.group(1).strip()
            # SummarizeBy
            sb = re.search(r"summarizeBy:\s*(\w+)", block)
            if sb:
                col["summarizeBy"] = sb.group(1)
            # Format
            fs = re.search(r"formatString:\s*(.+)", block)
            if fs:
                col["formatString"] = fs.group(1).strip()

            table["columns"].append(col)

        # Pre-pass: map measure name -> /// description that precedes it.
        # In TMDL, descriptions are triple-slash comments above the object,
        # NOT a `description:` property.
        triple_slash_desc = {}
        pending_comments = []
        for ln in content.split("\n"):
            stripped = ln.lstrip()
            if stripped.startswith("///"):
                pending_comments.append(stripped[3:].strip())
                continue
            mm_pre = re.match(r"^\tmeasure\s+'([^']+)'", ln)
            if mm_pre and pending_comments:
                triple_slash_desc[mm_pre.group(1)] = " ".join(pending_comments).strip()
            pending_comments = []

        # Extract measures
        measure_blocks = re.split(r"(?=^\tmeasure\s+')", content, flags=re.MULTILINE)
        for block in measure_blocks:
            mm = re.match(r"^\tmeasure\s+'([^']+)'\s*=\s*(.*?)(?=\n\tmeasure\s+'|\n\tcolumn\s+'|\n\tpartition\s+'|\n\tannotation\s|\Z)", block, re.DOTALL)
            if not mm:
                mm = re.match(r"^\tmeasure\s+'([^']+)'\s*=\s*(.*)", block, re.DOTALL)
            if not mm:
                continue
            measure = {
                "name": mm.group(1),
                "expression": mm.group(2).strip(),
                "description": triple_slash_desc.get(mm.group(1), ""),
                "formatString": "",
                "displayFolder": "",
            }
            # Legacy: also pick up `description:` property if present (invalid TMDL
            # but historical files may still have it).
            if not measure["description"]:
                desc = re.search(r"description:\s*(.+)", block)
                if desc:
                    measure["description"] = desc.group(1).strip()
            fs = re.search(r"formatString:\s*(.+)", block)
            if fs:
                measure["formatString"] = fs.group(1).strip()
            df = re.search(r"displayFolder:\s*(.+)", block)
            if df:
                measure["displayFolder"] = df.group(1).strip()
            table["measures"].append(measure)

        # ── Parse partitions con detalle (mode + source + kind) ──────────
        # Sintaxis TMDL:
        #   partition <name> = <kind>
        #       mode: <mode>
        #       source = <expr>
        # kind ∈ {calculated, m, entityRef}
        # mode ∈ {import, directQuery, dual}   (default = import si no aparece)
        partition_blocks = re.split(
            r"(?=^\tpartition\s+)", content, flags=re.MULTILINE
        )
        for pblock in partition_blocks:
            pm = re.match(
                r"^\tpartition\s+(?:'([^']+)'|\"([^\"]+)\"|(\S+))\s*=\s*(\w+)",
                pblock,
            )
            if not pm:
                continue
            pname = pm.group(1) or pm.group(2) or pm.group(3) or ""
            pkind = pm.group(4).strip().lower()

            # mode
            mm_mode = re.search(r"^\s+mode:\s*(\w+)", pblock, re.MULTILINE)
            pmode = mm_mode.group(1).strip().lower() if mm_mode else "import"

            # source = ...  (capturar hasta próximo bloque hermano o EOF)
            src_match = re.search(
                r"^\s+source\s*=\s*(.*?)(?=^\t\w|^\tannotation\s|\Z)",
                pblock,
                re.MULTILINE | re.DOTALL,
            )
            psource = src_match.group(1).strip() if src_match else ""

            table["partitions"].append({
                "name": pname,
                "kind": pkind,          # calculated | m | entityRef
                "mode": pmode,          # import | directQuery | dual
                "source": psource,
            })

        # Check for calculated table (mantener compatibilidad con lógica previa)
        if any(p["kind"] == "calculated" for p in table["partitions"]):
            table["isCalculatedTable"] = True

        # ── Storage mode a nivel tabla ────────────────────────────────
        # Si hay múltiples partitions con distintos modes, tabla es "dual/mixed"
        # Si no hay partitions (raro), default a "import"
        if table["partitions"]:
            modes = {p["mode"] for p in table["partitions"]}
            if len(modes) == 1:
                table["mode"] = modes.pop()
            else:
                table["mode"] = "dual"
        else:
            table["mode"] = "import"

        # ── Asignación FINAL del tableType (después de detectar calculated) ──
        # Prioridad: Auto Date/Time > system_hidden > calculated > user
        if is_template or table_name.startswith("DateTableTemplate_"):
            table["tableType"] = "auto_datetime_template"
            table["isSystemTable"] = True
        elif table_name.startswith("LocalDateTable_") and table["isHidden"]:
            table["tableType"] = "auto_datetime_local"
            table["isSystemTable"] = True
        elif table["isHidden"] and table["isPrivate"]:
            table["tableType"] = "system_hidden"
            table["isSystemTable"] = True
        elif table["isCalculatedTable"]:
            table["tableType"] = "calculated"
            table["isSystemTable"] = False
        else:
            table["tableType"] = "user"
            table["isSystemTable"] = False

        return table

    def _parse_relationships(self):
        rel_file = os.path.join(self.definition_path, "relationships.tmdl")
        if not os.path.isfile(rel_file):
            return

        try:
            with open(rel_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        blocks = content.split("\nrelationship")
        for block in blocks:
            from_match = re.search(r"fromColumn:\s*'?([^'\n]+)'?\.([^'\n]+)'?\s*$", block, re.MULTILINE)
            to_match = re.search(r"toColumn:\s*'?([^'\n]+)'?\.([^'\n]+)'?\s*$", block, re.MULTILINE)

            if not from_match or not to_match:
                from_col = re.search(r"fromColumn:\s*(.+)", block)
                to_col = re.search(r"toColumn:\s*(.+)", block)
                if not from_col or not to_col:
                    continue
                # Try table.column format
                fp = from_col.group(1).strip().replace("'", "")
                tp = to_col.group(1).strip().replace("'", "")
                if "." in fp and "." in tp:
                    from_parts = fp.rsplit(".", 1)
                    to_parts = tp.rsplit(".", 1)
                else:
                    continue
            else:
                from_parts = [from_match.group(1).strip("' "), from_match.group(2).strip("' ")]
                to_parts = [to_match.group(1).strip("' "), to_match.group(2).strip("' ")]

            is_bidi = "bothDirections" in block or "crossFilteringBehavior: bothDirections" in block
            is_active = "isActive: false" not in block.lower()

            self.model["relationships"].append({
                "fromTable": from_parts[0],
                "fromColumn": from_parts[1],
                "toTable": to_parts[0],
                "toColumn": to_parts[1],
                "crossFilteringBehavior": "bothDirections" if is_bidi else "oneDirection",
                "isActive": is_active,
            })
