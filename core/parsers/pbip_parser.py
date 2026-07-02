"""PBIP/PBIR file parser - reads Power BI project folders."""

import json
import os
from core.parsers.tmdl_parser import TMDLParser


class PBIPParser:
    """Parses PBIP (Power BI Project) folder structures.

    Supports both:
    - Old format: report.json with sections[]
    - New PBIR format: pages/pages.json with individual page/visual files
    - TMDL and BIM model formats
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.report_path = ""
        self.model_path = ""
        self.report_data = {}
        self.model_data = {}
        self.is_pbir = False
        self._resolve_paths()

    def _resolve_paths(self):
        """Auto-detect report and model folder locations.

        Handles all input forms:
        - Parent folder containing .Report + .SemanticModel
        - .pbip file (uses parent dir)
        - .Report folder directly (looks for sibling .SemanticModel)
        - .SemanticModel folder directly
        """
        base = self.project_path

        # If given a .pbip file, use its directory
        if os.path.isfile(base) and base.endswith(".pbip"):
            base = os.path.dirname(base)

        # If given a .Report folder directly, also check parent for sibling .SemanticModel
        is_report_folder = (
            os.path.isdir(base) and
            (base.endswith(".Report") or base.endswith(".Report/") or base.endswith(".Report\\"))
        )

        # Determine search directory for siblings
        search_dir = os.path.dirname(base) if is_report_folder else base

        # Look for .Report and .SemanticModel folders in search_dir
        if os.path.isdir(search_dir):
            for item in os.listdir(search_dir):
                full = os.path.join(search_dir, item)
                if not os.path.isdir(full):
                    continue
                if item.endswith(".Report") or item == "Report":
                    if not self.report_path:
                        self.report_path = full
                elif item.endswith(".SemanticModel") or item == "SemanticModel":
                    self.model_path = full
                elif item == "definition" and not self.model_path and search_dir == base:
                    self.model_path = base

        # If we were given the .Report folder directly, use it
        if is_report_folder and not self.report_path:
            self.report_path = base

        # Fallback: if path itself is a report/model folder
        if not self.report_path:
            if os.path.exists(os.path.join(base, "report.json")) or \
               os.path.exists(os.path.join(base, "definition.pbir")):
                self.report_path = base
        if not self.model_path:
            if os.path.exists(os.path.join(base, "definition", "model.tmdl")) or \
               os.path.exists(os.path.join(base, "model.bim")):
                self.model_path = base

    def parse(self) -> dict:
        """Parse the PBIP project and return structured data."""
        report = self._parse_report() if self.report_path else {}
        model = self._parse_model() if self.model_path else {}

        return {
            "layout": report,
            "model": model,
            "custom_visuals": self._find_custom_visuals(),
            "embedded_images": self._find_embedded_images(),
            "model_available": bool(model),
            "model_note": "" if model else "No se encontró modelo semántico.",
            "file_size_mb": self._calculate_folder_size(),
            "is_pbir": self.is_pbir,
            "report_base_path": self.report_path,
            "model_base_path": self.model_path,
        }

    def _parse_report(self) -> dict:
        """Parse report data (old format or PBIR)."""
        # Check for PBIR format first
        pbir_marker = os.path.join(self.report_path, "definition.pbir")
        pages_json = os.path.join(self.report_path, "definition", "pages", "pages.json")
        old_report = os.path.join(self.report_path, "definition", "report.json")
        legacy_report = os.path.join(self.report_path, "report.json")

        if os.path.exists(pages_json):
            self.is_pbir = True
            return self._parse_pbir_report()
        elif os.path.exists(old_report):
            return self._parse_json_file(old_report)
        elif os.path.exists(legacy_report):
            return self._parse_json_file(legacy_report)
        elif os.path.exists(pbir_marker):
            self.is_pbir = True
            return self._parse_pbir_report()

        return {}

    def _parse_pbir_report(self) -> dict:
        """Parse PBIR format report with individual page/visual files."""
        definition_dir = os.path.join(self.report_path, "definition")
        pages_dir = os.path.join(definition_dir, "pages")
        pages_json = os.path.join(pages_dir, "pages.json")

        result = {
            "sections": [],
            "config": "{}",
            "filters": "[]",
            "bookmarks": [],
            "_is_pbir": True,
            "_pages_dir": pages_dir,
        }

        # Load report config if available
        report_json = os.path.join(definition_dir, "report.json")
        if os.path.exists(report_json):
            rdata = self._parse_json_file(report_json)
            if rdata:
                result["config"] = json.dumps(rdata.get("config", {}))
                # PBIR: filters live under filterConfig.filters
                fc = rdata.get("filterConfig", {})
                result["filters"] = json.dumps(fc.get("filters", rdata.get("filters", [])))
                result["bookmarks"] = rdata.get("bookmarks", [])

        # Load pages order
        if not os.path.exists(pages_json):
            return result

        pages_data = self._parse_json_file(pages_json)
        if not pages_data:
            return result

        page_order = pages_data.get("pageOrder", [])

        for page_id in page_order:
            page_dir = os.path.join(pages_dir, page_id)
            page_json = os.path.join(page_dir, "page.json")

            if not os.path.exists(page_json):
                continue

            page_data = self._parse_json_file(page_json)
            if not page_data:
                continue

            section = {
                "name": page_id,
                "displayName": page_data.get("displayName", page_id),
                "width": page_data.get("width", 1280),
                "height": page_data.get("height", 720),
                "displayOption": page_data.get("displayOption", 0),
                "visibility": page_data.get("visibility", 0),
                "config": json.dumps(page_data.get("config", {})),
                "filters": json.dumps(
                    page_data.get("filterConfig", {}).get("filters",
                    page_data.get("filters", []))
                ),
                "visualContainers": [],
                "_page_dir": page_dir,
                "_page_id": page_id,
            }

            # Load visuals for this page
            visuals_dir = os.path.join(page_dir, "visuals")
            if os.path.isdir(visuals_dir):
                for visual_id in os.listdir(visuals_dir):
                    visual_dir = os.path.join(visuals_dir, visual_id)
                    visual_json = os.path.join(visual_dir, "visual.json")

                    if not os.path.exists(visual_json):
                        continue

                    visual_data = self._parse_json_file(visual_json)
                    if not visual_data:
                        continue

                    # Convert PBIR visual to legacy container format
                    # PBIR stores visual type in visual.visualType (not config.singleVisual)
                    pbir_visual = visual_data.get("visual", {})
                    visual_type = pbir_visual.get("visualType", "")
                    legacy_config = {
                        "singleVisual": {
                            "visualType": visual_type,
                            "objects": pbir_visual.get("objects", {}),
                        }
                    }

                    pos = visual_data.get("position", {})
                    container = {
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "width": pos.get("width", 0),
                        "height": pos.get("height", 0),
                        "config": json.dumps(legacy_config),
                        "filters": json.dumps(
                            visual_data.get("filterConfig", {}).get("filters",
                            visual_data.get("filters", []))
                        ),
                        "query": json.dumps(pbir_visual.get("query", {})),
                        "dataTransforms": json.dumps(pbir_visual.get("dataTransforms", {})),
                        "_visual_id": visual_id,
                        "_visual_dir": visual_dir,
                        "_visual_data": visual_data,
                    }
                    section["visualContainers"].append(container)

            result["sections"].append(section)

        return result

    def _parse_model(self) -> dict:
        """Parse semantic model (TMDL or BIM format)."""
        # Try TMDL first
        tmdl_dir = os.path.join(self.model_path, "definition")
        if os.path.exists(os.path.join(tmdl_dir, "model.tmdl")):
            parser = TMDLParser(tmdl_dir)
            return parser.parse()

        # Try BIM
        for bim_name in ["model.bim", "dataset.bim"]:
            bim_path = os.path.join(self.model_path, bim_name)
            if os.path.exists(bim_path):
                data = self._parse_json_file(bim_path)
                if data:
                    return data
            # Also check under definition/
            bim_path2 = os.path.join(self.model_path, "definition", bim_name)
            if os.path.exists(bim_path2):
                data = self._parse_json_file(bim_path2)
                if data:
                    return data

        return {}

    def _find_custom_visuals(self) -> list:
        """Find custom visuals in the report folder."""
        cv_dir = os.path.join(self.report_path, "definition", "customVisuals")
        if not os.path.isdir(cv_dir):
            cv_dir = os.path.join(self.report_path, "CustomVisuals")
        if not os.path.isdir(cv_dir):
            return []
        return [d for d in os.listdir(cv_dir) if os.path.isdir(os.path.join(cv_dir, d))]

    def _find_embedded_images(self) -> list:
        """Find embedded images in the report folder."""
        images = []
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}
        static_dir = os.path.join(self.report_path, "StaticResources")
        if not os.path.isdir(static_dir):
            static_dir = os.path.join(self.report_path, "definition", "staticResources")
        if not os.path.isdir(static_dir):
            return images

        for root, _, files in os.walk(static_dir):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in image_exts:
                    fpath = os.path.join(root, fname)
                    images.append({
                        "name": fname,
                        "size_kb": os.path.getsize(fpath) / 1024,
                        "path": fpath,
                    })
        return images

    def _calculate_folder_size(self) -> float:
        """Calculate total folder size in MB."""
        total = 0
        base = self.project_path
        if os.path.isfile(base):
            base = os.path.dirname(base)
        for root, _, files in os.walk(base):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total / (1024 * 1024)

    @staticmethod
    def _parse_json_file(path: str) -> dict | None:
        """Read and parse a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except Exception:
                return None
        except Exception:
            return None
