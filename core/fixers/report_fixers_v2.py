"""Report-layer fixers v2 - additional report quality checks."""

import json
import os
from collections import defaultdict
from core.fixers.base import BaseFixer


class FixDuplicateVisuals(BaseFixer):
    """Detect visuals with identical position and type (likely duplicates)."""

    fixer_id = "fix_duplicate_visuals"
    name = "Detectar visuals duplicados"
    description = (
        "Detecta visuals que tienen el mismo tipo y posición exacta en una página, "
        "lo cual indica un visual duplicado accidentalmente."
    )
    category = "report"
    severity = "warning"
    requires_pbip = True
    is_manual = True
    detection_method = "pattern_match"

    def scan(self):
        report = self.result._raw_report_data
        for section in report.get("sections", []):
            page_name = section.get("displayName", section.get("name", ""))
            seen = {}
            for container in section.get("visualContainers", []):
                vid = container.get("_visual_id", "")
                vdir = container.get("_visual_dir", "")
                if vdir:
                    vpath = os.path.join(vdir, "visual.json")
                    if os.path.exists(vpath):
                        data = self._read_json_file(vpath)
                        if not data:
                            continue
                        pos = data.get("position", {})
                        vtype = data.get("visual", {}).get("visualType", "")
                        key = (vtype, pos.get("x"), pos.get("y"),
                               pos.get("width"), pos.get("height"))
                        if key in seen and vtype:
                            self.issues.append(
                                f"[{page_name}] Visual '{vid}' es duplicado de "
                                f"'{seen[key]}' (tipo: {vtype})"
                            )
                        elif vtype:
                            seen[key] = vid

    def fix(self):
        # Only reports - deleting visuals is destructive
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixOverlappingVisuals(BaseFixer):
    """Detect visuals that significantly overlap each other."""

    fixer_id = "fix_overlapping_visuals"
    name = "Detectar visuals superpuestos"
    description = (
        "Detecta visuals que se superponen más de un 50% en una misma página. "
        "La superposición excesiva puede indicar errores de diseño."
    )
    category = "report"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    OVERLAP_THRESHOLD = 0.5  # 50% overlap

    def scan(self):
        report = self.result._raw_report_data
        for section in report.get("sections", []):
            page_name = section.get("displayName", section.get("name", ""))
            visuals = []
            for container in section.get("visualContainers", []):
                vid = container.get("_visual_id", "")
                vdir = container.get("_visual_dir", "")
                if vdir:
                    vpath = os.path.join(vdir, "visual.json")
                    if os.path.exists(vpath):
                        data = self._read_json_file(vpath)
                        if not data:
                            continue
                        pos = data.get("position", {})
                        vtype = data.get("visual", {}).get("visualType", "")
                        if pos and vtype not in ("shape", "textbox", "image"):
                            visuals.append({
                                "id": vid, "type": vtype,
                                "x": pos.get("x", 0), "y": pos.get("y", 0),
                                "w": pos.get("width", 0), "h": pos.get("height", 0),
                            })

            # Check pairwise overlaps
            for i, a in enumerate(visuals):
                for b in visuals[i + 1:]:
                    overlap = self._overlap_ratio(a, b)
                    if overlap > self.OVERLAP_THRESHOLD:
                        self.issues.append(
                            f"[{page_name}] '{a['id']}' ({a['type']}) y "
                            f"'{b['id']}' ({b['type']}) se superponen {overlap:.0%}"
                        )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")

    def _overlap_ratio(self, a: dict, b: dict) -> float:
        x1 = max(a["x"], b["x"])
        y1 = max(a["y"], b["y"])
        x2 = min(a["x"] + a["w"], b["x"] + b["w"])
        y2 = min(a["y"] + a["h"], b["y"] + b["h"])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        overlap_area = (x2 - x1) * (y2 - y1)
        area_a = a["w"] * a["h"]
        area_b = b["w"] * b["h"]
        min_area = min(area_a, area_b)
        return overlap_area / min_area if min_area > 0 else 0.0


class FixEmptyPages(BaseFixer):
    """Detect pages with no visuals or only background shapes."""

    fixer_id = "fix_empty_pages"
    name = "Detectar páginas vacías"
    description = (
        "Detecta páginas sin visuals de datos (solo shapes/textboxes/images). "
        "Las páginas vacías agregan peso y confunden a los usuarios."
    )
    category = "report"
    severity = "warning"
    requires_pbip = True
    is_manual = True
    detection_method = "pattern_match"

    DECORATIVE_TYPES = {"shape", "textbox", "image"}

    def scan(self):
        for page in self.result.pages_detail:
            if page.hidden or page.tooltip:
                continue
            # Check if page has only decorative visuals
            data_visuals = 0
            for vtype, count in page.visual_types.items():
                if vtype.lower() not in self.DECORATIVE_TYPES:
                    data_visuals += count
            if data_visuals == 0 and page.visuals_count > 0:
                self.issues.append(
                    f"[{page.name}] Solo tiene visuals decorativos "
                    f"({page.visuals_count} shapes/textboxes/images)"
                )
            elif page.visuals_count == 0:
                self.issues.append(f"[{page.name}] Página completamente vacía")

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixVisualTabOrder(BaseFixer):
    """Check and fix visual tab order for accessibility."""

    fixer_id = "fix_visual_tab_order"
    name = "Corregir orden de tabulación"
    description = (
        "Verifica que el orden de tabulación de los visuals siga un patrón "
        "lógico (izquierda-derecha, arriba-abajo) para accesibilidad."
    )
    category = "report"
    severity = "info"
    requires_pbip = True

    def scan(self):
        for page_path, data, page_name in self._iter_page_files():
            page_dir = os.path.dirname(page_path)
            visuals_dir = os.path.join(page_dir, "visuals")
            if not os.path.isdir(visuals_dir):
                continue

            visuals_positions = []
            for vid in os.listdir(visuals_dir):
                vpath = os.path.join(visuals_dir, vid, "visual.json")
                if not os.path.exists(vpath):
                    continue
                vdata = self._read_json_file(vpath)
                if not vdata:
                    continue
                pos = vdata.get("position", {}) or {}
                # tabOrder lives under position in PBIR schema 2.6.0+.
                # Also accept root-level (legacy / broken files) for detection.
                tab = pos.get("tabOrder", vdata.get("tabOrder", -1))
                root_tab_invalid = "tabOrder" in vdata  # root-level is invalid
                visuals_positions.append({
                    "id": vid,
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                    "tab": tab,
                    "root_invalid": root_tab_invalid,
                })

            if not visuals_positions:
                continue

            # ALWAYS report when any file has invalid root-level tabOrder so the
            # fix() pass can clean them up — regardless of spatial-order analysis.
            invalid_root = [v for v in visuals_positions if v["root_invalid"]]
            if invalid_root:
                self.issues.append(
                    f"[{page_name}] {len(invalid_root)} visual(es) con tabOrder en root "
                    f"(invalid en schema 2.6.0+; debe ir bajo position)"
                )

            if len(visuals_positions) < 2:
                continue

            # Check if tabOrder follows spatial order (top-left to bottom-right)
            spatial = sorted(visuals_positions, key=lambda v: (v["y"] // 100, v["x"]))
            tab_ordered = sorted(visuals_positions, key=lambda v: v["tab"])

            mismatches = 0
            for s, t in zip(spatial, tab_ordered):
                if s["id"] != t["id"]:
                    mismatches += 1

            if mismatches > len(visuals_positions) * 0.5:
                self.issues.append(
                    f"[{page_name}] Orden de tabulación no sigue patrón espacial "
                    f"({mismatches}/{len(visuals_positions)} visuals desordenados)"
                )

    def fix(self):
        for page_path, data, page_name in self._iter_page_files():
            page_dir = os.path.dirname(page_path)
            visuals_dir = os.path.join(page_dir, "visuals")
            if not os.path.isdir(visuals_dir):
                continue

            visuals = []
            for vid in os.listdir(visuals_dir):
                vpath = os.path.join(visuals_dir, vid, "visual.json")
                if not os.path.exists(vpath):
                    continue
                vdata = self._read_json_file(vpath)
                if not vdata:
                    continue
                pos = vdata.get("position", {}) or {}
                visuals.append({
                    "path": vpath,
                    "data": vdata,
                    "id": vid,
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                })

            if not visuals:
                continue

            # PASS 1 — strip any invalid root-level tabOrder. PBIR schema 2.6.0+
            # only allows tabOrder under `position`, never at the root. Files
            # written by older versions of this fixer have it at the root and
            # Power BI Desktop rejects them with "schema does not allow
            # additional properties".
            cleaned_root = 0
            for v in visuals:
                if "tabOrder" in v["data"]:
                    # If position has no tabOrder yet, migrate the value down.
                    pos = v["data"].setdefault("position", {})
                    if "tabOrder" not in pos:
                        pos["tabOrder"] = v["data"]["tabOrder"]
                    del v["data"]["tabOrder"]
                    self._write_json_file(v["path"], v["data"])
                    cleaned_root += 1

            if cleaned_root:
                self.fixes_applied.append(
                    f"[{page_name}] tabOrder en root removido de {cleaned_root} visual(es)"
                )

            if len(visuals) < 2:
                continue

            # PASS 2 — reassign tab order so it follows spatial reading order
            # (top-left to bottom-right). Write to position.tabOrder.
            sorted_visuals = sorted(visuals, key=lambda v: (v["y"] // 100, v["x"]))
            reordered = 0
            for idx, v in enumerate(sorted_visuals):
                new_tab = (idx + 1) * 1000
                pos = v["data"].setdefault("position", {})
                if pos.get("tabOrder") != new_tab:
                    pos["tabOrder"] = new_tab
                    self._write_json_file(v["path"], v["data"])
                    reordered += 1

            if reordered:
                self.fixes_applied.append(
                    f"[{page_name}] position.tabOrder actualizado en {reordered} visual(es)"
                )


class FixLargeCardCount(BaseFixer):
    """Detect pages with too many card visuals (performance issue)."""

    fixer_id = "fix_large_card_count"
    name = "Detectar exceso de cards"
    description = (
        "Detecta páginas con más de 10 visuals tipo card. "
        "Cada card genera una query DAX individual, impactando el rendimiento."
    )
    category = "report"
    severity = "warning"
    requires_pbip = False
    is_manual = True
    detection_method = "threshold"

    CARD_TYPES = {"card", "cardVisual", "multiRowCard", "kpi"}
    MAX_CARDS = 10

    def scan(self):
        for page in self.result.pages_detail:
            card_count = sum(
                page.visual_types.get(ct, 0) for ct in self.CARD_TYPES
            )
            if card_count > self.MAX_CARDS:
                self.issues.append(
                    f"[{page.name}] {card_count} cards detectados "
                    f"(máximo recomendado: {self.MAX_CARDS}). "
                    f"Cada card genera una query DAX individual."
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixSlicerSync(BaseFixer):
    """Detect inconsistent slicer usage across pages."""

    fixer_id = "fix_slicer_sync"
    name = "Detectar slicers inconsistentes"
    description = (
        "Detecta páginas con cantidad de slicers muy diferente al promedio, "
        "lo cual puede indicar slicers faltantes o redundantes."
    )
    category = "report"
    severity = "info"
    requires_pbip = False
    is_manual = True
    detection_method = "heuristic"

    def scan(self):
        pages_with_slicers = []
        for page in self.result.pages_detail:
            if page.hidden or page.tooltip:
                continue
            slicer_count = page.visual_types.get("slicer", 0)
            pages_with_slicers.append((page.name, slicer_count))

        if len(pages_with_slicers) < 2:
            return

        counts = [c for _, c in pages_with_slicers]
        avg = sum(counts) / len(counts)
        if avg == 0:
            return

        for name, count in pages_with_slicers:
            if count == 0 and avg >= 2:
                self.issues.append(
                    f"[{name}] No tiene slicers (promedio del reporte: {avg:.1f})"
                )
            elif count > avg * 2 and count > 5:
                self.issues.append(
                    f"[{name}] {count} slicers (promedio: {avg:.1f}). "
                    f"Considere consolidar con sync slicers."
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")
