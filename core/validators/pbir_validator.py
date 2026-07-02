"""Post-fix validator for PBIR/TMDL schema rules.

Catches the rules Power BI Desktop enforces but doesn't document together.
Each rule is added here as soon as we discover one in the wild, so the next
deploy can never reintroduce it. Run this BEFORE handing the user a fixed
ZIP — if any BLOCKING issue is reported, do not let them download.

To add a rule: append to `RULES` and implement a `_check_*` method that
returns a list of `ValidationIssue`.
"""

import glob
import json
import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationIssue:
    rule: str                 # rule id (e.g. "tabOrder_root")
    severity: str             # "blocking" | "soft"
    file: str                 # path relative to project root
    message: str              # human-readable
    line: int = 0             # 0 = whole file
    hint: str = ""            # suggested fix


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def blocking(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def soft(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "soft"]

    @property
    def is_clean(self) -> bool:
        return not self.issues

    @property
    def can_open(self) -> bool:
        return not self.blocking


class PBIRValidator:
    """Validates a PBIP project (.Report + .SemanticModel) against known
    rules that Power BI Desktop enforces at open time."""

    def __init__(self, report_base: str | None, model_base: str | None):
        self.report_base = report_base
        self.model_base = model_base

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        if self.model_base and os.path.isdir(self.model_base):
            result.issues.extend(self._check_tmdl_measures())
            result.issues.extend(self._check_tmdl_calc_items())
            result.issues.extend(self._check_relationships())
            result.issues.extend(self._check_sortby_self_reference())
            result.issues.extend(self._check_discourage_implicit_measures())
        if self.report_base and os.path.isdir(self.report_base):
            result.issues.extend(self._check_visual_json())
        return result

    # ── helpers ─────────────────────────────────────────────────────

    def _tmdl_table_files(self):
        if not self.model_base:
            return
        tables_dir = os.path.join(self.model_base, "definition", "tables")
        if not os.path.isdir(tables_dir):
            return
        for fname in os.listdir(tables_dir):
            if fname.endswith(".tmdl"):
                yield os.path.join(tables_dir, fname)

    def _rel_path(self, path: str) -> str:
        base = self.model_base or self.report_base or ""
        try:
            parent = os.path.dirname(base)
            return os.path.relpath(path, parent)
        except Exception:
            return path

    # ── rule 1: description: as TMDL measure property (must be ///) ─

    def _check_tmdl_measures(self) -> List[ValidationIssue]:
        issues = []
        for fpath in self._tmdl_table_files():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue
            in_measure = False
            measure_name = ""
            for idx, ln in enumerate(lines, start=1):
                stripped = ln.strip()
                if re.match(r"^\tmeasure\s+", ln):
                    in_measure = True
                    m = re.match(r"^\tmeasure\s+'?([^'=\s]+)", ln)
                    measure_name = m.group(1) if m else ""
                    continue
                if in_measure and re.match(r"^\t(column|measure|partition|annotation)\b", ln):
                    in_measure = False
                if in_measure and re.match(r"^\t\tdescription:", ln):
                    issues.append(ValidationIssue(
                        rule="tmdl_measure_description_property",
                        severity="blocking",
                        file=self._rel_path(fpath),
                        line=idx,
                        message=(
                            f"Measure '{measure_name}' has `description:` as property. "
                            f"In TMDL descriptions must be `/// text` before the object."
                        ),
                        hint="Replace `description: X` with `/// X` on the line before `measure`.",
                    ))
        return issues

    # ── rule 2: lineageTag inside calculationItem (invalid) ─────────

    def _check_tmdl_calc_items(self) -> List[ValidationIssue]:
        issues = []
        for fpath in self._tmdl_table_files():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue
            in_item = False
            for idx, ln in enumerate(lines, start=1):
                if re.match(r"^\t\tcalculationItem\b", ln):
                    in_item = True
                    continue
                if in_item and re.match(r"^\t\t(calculationItem|calculationGroup|column|table|partition)\b", ln):
                    in_item = False
                if in_item and re.match(r"^\t\t\tlineageTag:", ln):
                    issues.append(ValidationIssue(
                        rule="tmdl_calcitem_lineagetag",
                        severity="blocking",
                        file=self._rel_path(fpath),
                        line=idx,
                        message="lineageTag is not allowed inside calculationItem.",
                        hint="Remove the lineageTag line.",
                    ))
        return issues

    # ── rule 3: tabOrder at root of visual.json (must be under position) ─
    # ── rule 4: visualType at root of visual.json (must be under visual) ─

    def _check_visual_json(self) -> List[ValidationIssue]:
        issues = []
        if not self.report_base:
            return issues
        pattern = os.path.join(self.report_base, "definition", "pages", "*", "visuals", "*", "visual.json")
        for fpath in glob.glob(pattern):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if "tabOrder" in data:
                issues.append(ValidationIssue(
                    rule="pbir_visual_taborder_root",
                    severity="blocking",
                    file=self._rel_path(fpath),
                    message="tabOrder must be under position, not at the root of visual.json.",
                    hint="Move tabOrder into position.{tabOrder}.",
                ))
            if "visualType" in data:
                issues.append(ValidationIssue(
                    rule="pbir_visual_visualtype_root",
                    severity="blocking",
                    file=self._rel_path(fpath),
                    message="visualType must be under visual, not at the root of visual.json.",
                    hint="Move visualType into visual.{visualType}.",
                ))
        return issues

    # ── rule 5: 1:1 relationship with oneDirection ──────────────────

    def _check_relationships(self) -> List[ValidationIssue]:
        issues = []
        if not self.model_base:
            return issues
        rel_file = os.path.join(self.model_base, "definition", "relationships.tmdl")
        if not os.path.exists(rel_file):
            return issues
        try:
            with open(rel_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return issues
        blocks = re.split(r"(?=^relationship\s)", content, flags=re.MULTILINE)
        # Track line offsets for reporting
        line_start = 1
        for block in blocks:
            block_lines = block.count("\n")
            if block.startswith("relationship"):
                has_from_one = bool(re.search(r"^\s*fromCardinality:\s*one\b", block, re.MULTILINE))
                has_to_many = bool(re.search(r"^\s*toCardinality:\s*many\b", block, re.MULTILINE))
                is_one_one = has_from_one and not has_to_many
                has_one_dir = bool(re.search(r"crossFilteringBehavior:\s*oneDirection", block))
                if is_one_one and has_one_dir:
                    m = re.search(r"relationship\s+(\S+)", block)
                    rid = m.group(1) if m else "?"
                    issues.append(ValidationIssue(
                        rule="tmdl_one_to_one_unidirectional",
                        severity="blocking",
                        file=self._rel_path(rel_file),
                        line=line_start,
                        message=(
                            f"Relationship {rid} is 1:1 but crossFilteringBehavior is oneDirection. "
                            f"Power BI requires bothDirections for 1:1 relationships."
                        ),
                        hint="Change crossFilteringBehavior to bothDirections.",
                    ))
            line_start += block_lines
        return issues

    # ── rule 6: sortByColumn self-reference ─────────────────────────

    def _check_sortby_self_reference(self) -> List[ValidationIssue]:
        issues = []
        for fpath in self._tmdl_table_files():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            for match in re.finditer(r"^\tcolumn\s+'?([^'\s]+)'?\s*\n((?:\t\t[^\n]+\n)+)", content, re.MULTILINE):
                col_name = match.group(1)
                body = match.group(2)
                sbc = re.search(r"sortByColumn:\s*'?([^'\n]+?)'?\s*$", body, re.MULTILINE)
                if sbc and sbc.group(1).strip() == col_name:
                    issues.append(ValidationIssue(
                        rule="tmdl_sortby_self_reference",
                        severity="blocking",
                        file=self._rel_path(fpath),
                        message=f"Column '{col_name}' has sortByColumn pointing to itself.",
                        hint=f"Remove the sortByColumn line on column '{col_name}'.",
                    ))
        return issues

    # ── rule 7: calc group requires discourageImplicitMeasures: true ─

    def _check_discourage_implicit_measures(self) -> List[ValidationIssue]:
        issues = []
        if not self.model_base:
            return issues
        # Does the model have any calc group?
        has_calc_group = False
        for fpath in self._tmdl_table_files():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    if re.search(r"^\tcalculationGroup\b", f.read(), re.MULTILINE):
                        has_calc_group = True
                        break
            except Exception:
                continue
        if not has_calc_group:
            return issues
        # Then model.tmdl must declare discourageImplicitMeasures: true
        model_tmdl = os.path.join(self.model_base, "definition", "model.tmdl")
        if not os.path.exists(model_tmdl):
            return issues
        try:
            with open(model_tmdl, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return issues
        if not re.search(r"^\s*discourageImplicitMeasures:\s*true\b", content, re.MULTILINE):
            issues.append(ValidationIssue(
                rule="tmdl_calcgroup_requires_discourage_implicit",
                severity="blocking",
                file=self._rel_path(model_tmdl),
                message=(
                    "Model has calculation groups but discourageImplicitMeasures is not "
                    "set to true. Power BI rejects this."
                ),
                hint="Add `discourageImplicitMeasures: true` as a property of the `model` block.",
            ))
        return issues


# Registry of rules (for documentation/UI surfacing)
RULES = [
    ("tmdl_measure_description_property",
     "TMDL `description:` as measure property → use `/// text`"),
    ("tmdl_calcitem_lineagetag",
     "lineageTag inside calculationItem is not allowed"),
    ("pbir_visual_taborder_root",
     "tabOrder at root of visual.json → must be under position"),
    ("pbir_visual_visualtype_root",
     "visualType at root of visual.json → must be under visual"),
    ("tmdl_one_to_one_unidirectional",
     "1:1 relationship with oneDirection → must be bothDirections"),
    ("tmdl_sortby_self_reference",
     "Column sortByColumn pointing to itself"),
    ("tmdl_calcgroup_requires_discourage_implicit",
     "Model with calc groups needs discourageImplicitMeasures: true"),
]
