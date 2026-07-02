"""Model Manager — Perspectives, Translations, and model metadata.

Reads and writes perspectives and translations from TMDL/BIM model files.
"""

import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class Perspective:
    name: str
    tables: list = field(default_factory=list)   # [{"table": str, "columns": [str], "measures": [str]}]


@dataclass
class Translation:
    culture: str            # e.g. "es-AR", "en-US", "pt-BR"
    has_linguistic: bool = False
    table_translations: dict = field(default_factory=dict)   # {table_name: translated_name}
    column_translations: dict = field(default_factory=dict)  # {"table.column": translated_name}
    measure_translations: dict = field(default_factory=dict) # {"table.measure": translated_name}


class ModelManager:
    """Read and manage perspectives and translations from TMDL/BIM."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.definition_path = os.path.join(model_path, "definition")
        if not os.path.isdir(self.definition_path):
            self.definition_path = model_path

    # ═══════════════════════════════════════════════════════════
    #  PERSPECTIVES
    # ═══════════════════════════════════════════════════════════

    def list_perspectives(self) -> list[Perspective]:
        """Read perspectives from TMDL or BIM."""
        # Try TMDL perspectives folder
        persp_dir = os.path.join(self.definition_path, "perspectives")
        if os.path.isdir(persp_dir):
            return self._read_tmdl_perspectives(persp_dir)

        # Try BIM
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(self.definition_path, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.model_path, bim_name)
            if os.path.exists(bim_path):
                return self._read_bim_perspectives(bim_path)

        return []

    def create_perspective(self, name: str, tables: list[str]) -> bool:
        """Create a new perspective including all columns/measures of given tables."""
        persp_dir = os.path.join(self.definition_path, "perspectives")
        os.makedirs(persp_dir, exist_ok=True)

        safe_name = re.sub(r'[^\w\s-]', '', name).strip()
        path = os.path.join(persp_dir, f"{safe_name}.tmdl")

        lines = [f"perspective '{name}'"]
        lines.append("")

        # Add tables with their columns and measures
        tables_dir = os.path.join(self.definition_path, "tables")
        for tname in tables:
            lines.append(f"\tperspectiveTable '{tname}'")
            lines.append("")

            # Read table file to get columns and measures
            if os.path.isdir(tables_dir):
                tfile = os.path.join(tables_dir, f"{tname}.tmdl")
                if not os.path.exists(tfile):
                    tfile = os.path.join(tables_dir, f"'{tname}'.tmdl")
                if os.path.exists(tfile):
                    with open(tfile, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Extract columns
                    for m in re.finditer(r"^\tcolumn\s+'([^']+)'", content, re.MULTILINE):
                        lines.append(f"\t\tperspectiveColumn '{m.group(1)}'")
                    # Extract measures
                    for m in re.finditer(r"^\tmeasure\s+'([^']+)'", content, re.MULTILINE):
                        lines.append(f"\t\tperspectiveMeasure '{m.group(1)}'")
                    lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    def _read_tmdl_perspectives(self, persp_dir: str) -> list[Perspective]:
        perspectives = []
        for fname in os.listdir(persp_dir):
            if not fname.endswith(".tmdl"):
                continue
            fpath = os.path.join(persp_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            m = re.match(r"^perspective\s+'([^']+)'", content)
            name = m.group(1) if m else fname.replace(".tmdl", "")

            tables = []
            current_table = None
            for line in content.split("\n"):
                tm = re.match(r"^\tperspectiveTable\s+'([^']+)'", line)
                if tm:
                    current_table = {"table": tm.group(1), "columns": [], "measures": []}
                    tables.append(current_table)
                elif current_table:
                    cm = re.match(r"^\t\tperspectiveColumn\s+'([^']+)'", line)
                    if cm:
                        current_table["columns"].append(cm.group(1))
                    mm = re.match(r"^\t\tperspectiveMeasure\s+'([^']+)'", line)
                    if mm:
                        current_table["measures"].append(mm.group(1))

            perspectives.append(Perspective(name=name, tables=tables))
        return perspectives

    def _read_bim_perspectives(self, bim_path: str) -> list[Perspective]:
        try:
            with open(bim_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        model = data.get("model", data)
        perspectives = []
        for p in model.get("perspectives", []):
            tables = []
            for pt in p.get("tables", []):
                tables.append({
                    "table": pt.get("name", ""),
                    "columns": [c.get("name", "") for c in pt.get("columns", [])],
                    "measures": [m.get("name", "") for m in pt.get("measures", [])],
                })
            perspectives.append(Perspective(name=p.get("name", ""), tables=tables))
        return perspectives

    # ═══════════════════════════════════════════════════════════
    #  TRANSLATIONS
    # ═══════════════════════════════════════════════════════════

    def list_translations(self) -> list[Translation]:
        """Read translations/cultures from TMDL or BIM."""
        cultures_dir = os.path.join(self.definition_path, "cultures")
        if os.path.isdir(cultures_dir):
            return self._read_tmdl_translations(cultures_dir)

        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(self.definition_path, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.model_path, bim_name)
            if os.path.exists(bim_path):
                return self._read_bim_translations(bim_path)

        return []

    def create_translation(self, culture: str, translations: dict) -> bool:
        """Create a new translation file.

        translations = {
            "tables": {"OldName": "NewName", ...},
            "columns": {"Table.Column": "Translated", ...},
            "measures": {"Table.Measure": "Translated", ...},
        }
        """
        cultures_dir = os.path.join(self.definition_path, "cultures")
        os.makedirs(cultures_dir, exist_ok=True)

        path = os.path.join(cultures_dir, f"{culture}.tmdl")

        lines = [f"cultureInfo {culture}"]
        lines.append("")

        # Group by table
        table_items = {}
        for key, translated in translations.get("tables", {}).items():
            table_items.setdefault(key, {"caption": translated, "columns": {}, "measures": {}})

        for key, translated in translations.get("columns", {}).items():
            parts = key.split(".", 1)
            if len(parts) == 2:
                table_items.setdefault(parts[0], {"caption": "", "columns": {}, "measures": {}})
                table_items[parts[0]]["columns"][parts[1]] = translated

        for key, translated in translations.get("measures", {}).items():
            parts = key.split(".", 1)
            if len(parts) == 2:
                table_items.setdefault(parts[0], {"caption": "", "columns": {}, "measures": {}})
                table_items[parts[0]]["measures"][parts[1]] = translated

        for tname, items in table_items.items():
            lines.append(f"\ttranslation '{tname}'")
            if items["caption"]:
                lines.append(f"\t\tcaption: {items['caption']}")
            for cname, ctrans in items["columns"].items():
                lines.append(f"\t\ttranslation '{cname}'")
                lines.append(f"\t\t\tcaption: {ctrans}")
            for mname, mtrans in items["measures"].items():
                lines.append(f"\t\ttranslation '{mname}'")
                lines.append(f"\t\t\tcaption: {mtrans}")
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    def _read_tmdl_translations(self, cultures_dir: str) -> list[Translation]:
        translations = []
        for fname in os.listdir(cultures_dir):
            if not fname.endswith(".tmdl"):
                continue
            culture = fname.replace(".tmdl", "")
            fpath = os.path.join(cultures_dir, fname)

            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            has_linguistic = "linguisticMetadata" in content

            t = Translation(culture=culture, has_linguistic=has_linguistic)

            # Parse translations (simplified — captures table/column captions)
            current_table = None
            for line in content.split("\n"):
                tm = re.match(r"^\ttranslation\s+'([^']+)'", line)
                if tm:
                    current_table = tm.group(1)
                cm = re.match(r"^\t\tcaption:\s+(.+)", line)
                if cm and current_table:
                    t.table_translations[current_table] = cm.group(1).strip()

            translations.append(t)
        return translations

    def _read_bim_translations(self, bim_path: str) -> list[Translation]:
        try:
            with open(bim_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        model = data.get("model", data)
        translations = []
        for c in model.get("cultures", []):
            culture = c.get("name", "")
            t = Translation(culture=culture, has_linguistic=bool(c.get("linguisticMetadata")))

            for obj in c.get("translations", {}).get("model", {}).get("tables", []):
                tname = obj.get("name", "")
                if obj.get("translatedCaption"):
                    t.table_translations[tname] = obj["translatedCaption"]
                for col in obj.get("columns", []):
                    if col.get("translatedCaption"):
                        t.column_translations[f"{tname}.{col['name']}"] = col["translatedCaption"]
                for m in obj.get("measures", []):
                    if m.get("translatedCaption"):
                        t.measure_translations[f"{tname}.{m['name']}"] = m["translatedCaption"]

            translations.append(t)
        return translations
