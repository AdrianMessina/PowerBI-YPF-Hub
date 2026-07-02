"""Semantic model fixers - modify TMDL/BIM files."""

import os
import re
from core.fixers.base import BaseFixer


class FixBidirectionalRelationships(BaseFixer):
    """Convert bidirectional relationships to one-direction.

    Caveat: One-to-one relationships REQUIRE crossFilteringBehavior:
    bothDirections (Power BI rejects the model otherwise). Only N:1
    (many-to-one) and M:N relationships are flipped to oneDirection.
    """

    fixer_id = "fix_bidirectional"
    name = "Corregir relaciones bidireccionales"
    description = (
        "Convierte relaciones bidireccionales N:1/M:N a unidireccionales. "
        "Las relaciones 1:1 se preservan como bothDirections (requerido por Power BI)."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True

    def scan(self):
        """Reads relationships.tmdl directly because cardinality information
        is not in the cached `result.relationships_detail`. Reports two kinds
        of issues:
        - Non-1:1 with bothDirections (BPA anti-pattern, will be flipped)
        - 1:1 with oneDirection (broken state from older buggy runs of this
          fixer; Power BI rejects 1:1 unless crossFilteringBehavior=bothDirections)
        """
        model_def = self._get_model_definition_path()
        rel_file = os.path.join(model_def, "relationships.tmdl")

        if os.path.exists(rel_file):
            try:
                with open(rel_file, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                content = ""
            blocks = re.split(r"(?=^relationship\s)", content, flags=re.MULTILINE)
            for block in blocks:
                if not block.startswith("relationship"):
                    continue
                from_col = re.search(r"fromColumn:\s*(\S+)", block)
                to_col = re.search(r"toColumn:\s*(\S+)", block)
                label = (
                    f"{from_col.group(1) if from_col else '?'} <-> "
                    f"{to_col.group(1) if to_col else '?'}"
                )
                is_one_one = self._is_one_to_one(block)
                has_both = bool(re.search(r"crossFilteringBehavior:\s*bothDirections", block))
                has_one = bool(re.search(r"crossFilteringBehavior:\s*oneDirection", block))

                if is_one_one and has_one:
                    self.issues.append(
                        f"{label} (1:1): crossFilteringBehavior=oneDirection invalido "
                        f"— Power BI requiere bothDirections para 1:1"
                    )
                elif not is_one_one and has_both:
                    self.issues.append(
                        f"{label}: bidireccional (debe ser oneDirection)"
                    )
            return

        # BIM fallback (cardinality available in dict)
        for rel in self.result.relationships_detail:
            if rel.is_bidirectional:
                self.issues.append(
                    f"{rel.from_table}.{rel.from_column} <-> {rel.to_table}.{rel.to_column}: bidireccional"
                )

    def fix(self):
        if not self.issues:
            return

        model_def = self._get_model_definition_path()

        # Try TMDL format
        rel_file = os.path.join(model_def, "relationships.tmdl")
        if os.path.exists(rel_file):
            self._fix_tmdl_relationships(rel_file)
            return

        # Try BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if os.path.exists(bim_path):
                self._fix_bim_relationships(bim_path)
                return

    @staticmethod
    def _is_one_to_one(block: str) -> bool:
        """A relationship is 1:1 when fromCardinality is 'one' AND
        toCardinality is NOT explicitly 'many'.

        TMDL defaults: fromCardinality=many, toCardinality=one. So an explicit
        `fromCardinality: one` with no `toCardinality: many` is 1:1.
        """
        has_from_one = bool(re.search(r"^\s*fromCardinality:\s*one\b", block, re.MULTILINE))
        has_to_many = bool(re.search(r"^\s*toCardinality:\s*many\b", block, re.MULTILINE))
        return has_from_one and not has_to_many

    def _fix_tmdl_relationships(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into per-relationship blocks. Each block starts with a line
        # `relationship <id>` and runs until the next such line.
        blocks = re.split(r"(?=^relationship\s)", content, flags=re.MULTILINE)
        flipped = 0
        restored = 0  # 1:1 relationships incorrectly set to oneDirection by older runs
        new_blocks = []
        for block in blocks:
            if not block.startswith("relationship"):
                new_blocks.append(block)
                continue

            is_one_one = self._is_one_to_one(block)

            if is_one_one:
                # 1:1 must be bothDirections. If a past run forced it to
                # oneDirection, restore it here.
                if re.search(r"crossFilteringBehavior:\s*oneDirection", block):
                    block = re.sub(
                        r"crossFilteringBehavior:\s*oneDirection",
                        "crossFilteringBehavior: bothDirections",
                        block,
                    )
                    restored += 1
            else:
                # Many-to-one / many-to-many: bothDirections is the BPA
                # anti-pattern. Flip to oneDirection.
                if re.search(r"crossFilteringBehavior:\s*bothDirections", block):
                    block = re.sub(
                        r"crossFilteringBehavior:\s*bothDirections",
                        "crossFilteringBehavior: oneDirection",
                        block,
                    )
                    flipped += 1

            new_blocks.append(block)

        new_content = "".join(new_blocks)
        if new_content == content:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        if flipped:
            self.fixes_applied.append(
                f"{flipped} relacion(es) N:1/M:N: bothDirections -> oneDirection"
            )
        if restored:
            self.fixes_applied.append(
                f"{restored} relacion(es) 1:1: oneDirection -> bothDirections "
                f"(requerido por Power BI)"
            )

    def _fix_bim_relationships(self, path: str):
        data = self._read_json_file(path)
        if not data:
            return

        model = data.get("model", data)
        flipped = 0
        restored = 0
        for rel in model.get("relationships", []):
            from_card = rel.get("fromCardinality", "many").lower()
            to_card = rel.get("toCardinality", "one").lower()
            is_one_one = (from_card == "one" and to_card == "one")
            cfb = rel.get("crossFilteringBehavior", "").lower()

            if is_one_one and cfb == "onedirection":
                rel["crossFilteringBehavior"] = "bothDirections"
                restored += 1
            elif not is_one_one and cfb == "bothdirections":
                rel["crossFilteringBehavior"] = "oneDirection"
                flipped += 1

        if flipped or restored:
            self._write_json_file(path, data)
        if flipped:
            self.fixes_applied.append(
                f"{flipped} relacion(es) N:1/M:N: bothDirections -> oneDirection"
            )
        if restored:
            self.fixes_applied.append(
                f"{restored} relacion(es) 1:1: oneDirection -> bothDirections "
                f"(requerido por Power BI)"
            )


class FixCalculatedColumnsToMeasures(BaseFixer):
    """Detect calculated columns that could be measures instead."""

    fixer_id = "fix_calculated_columns"
    name = "Detectar columnas calculadas convertibles a medidas"
    description = (
        "Detecta columnas calculadas que podrían ser medidas DAX. "
        "Las medidas se calculan en tiempo de consulta y no ocupan espacio en el modelo. "
        "NOTA: Este fix solo reporta, no convierte automáticamente (requiere revisión manual)."
    )
    category = "model"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    # Patterns that suggest the column could be a measure
    MEASURE_PATTERNS = [
        r"CALCULATE\s*\(", r"SUMX\s*\(", r"AVERAGEX\s*\(",
        r"COUNTROWS\s*\(", r"SUM\s*\(", r"AVERAGE\s*\(",
        r"COUNT\s*\(", r"MIN\s*\(", r"MAX\s*\(",
    ]

    def scan(self):
        for col in self.result.columns_detail:
            if not col.is_calculated:
                continue
            if not col.expression:
                continue
            # Check if expression looks like an aggregation (measure candidate)
            expr_upper = col.expression.upper()
            for pattern in self.MEASURE_PATTERNS:
                if re.search(pattern, expr_upper):
                    self.issues.append(
                        f"[{col.table}] Columna calculada '{col.name}' usa {pattern.split('(')[0].strip(chr(92))}"
                        f" y podría ser una medida"
                    )
                    break

    def fix(self):
        # This fixer only reports, doesn't auto-convert
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")
