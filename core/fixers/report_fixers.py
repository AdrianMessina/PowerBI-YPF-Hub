"""Report-layer fixers for PBIR visual/page files."""

import json
import math
from core.fixers.base import BaseFixer


class FixPieCharts(BaseFixer):
    """Replace pie/donut charts with bar charts."""

    fixer_id = "fix_pie_charts"
    name = "Reemplazar gráficos de torta"
    description = (
        "Reemplaza gráficos de torta (pie) y dona (donut) por gráficos de barras, "
        "que son más efectivos para comparar valores según las mejores prácticas de visualización."
    )
    category = "report"
    severity = "warning"
    requires_pbip = True

    PIE_TYPES = {"pieChart", "donutChart"}
    REPLACEMENT_TYPE = "barChart"

    def scan(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            vtype = self._get_visual_type(data)
            if vtype in self.PIE_TYPES:
                self.issues.append(
                    f"[{page_name}] Visual '{vid}': {vtype} -> debería ser barChart"
                )

    def fix(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            vtype = self._get_visual_type(data)
            if vtype not in self.PIE_TYPES:
                continue

            # Write to whichever structure the file actually uses. PBIR 2.6+
            # nests visualType under `visual`; older PBIP nests under
            # `config.singleVisual`. Root-level visualType is invalid per the
            # 2.6 schema but we tolerate it if the file already has it.
            if isinstance(data.get("visual"), dict) and "visualType" in data["visual"]:
                data["visual"]["visualType"] = self.REPLACEMENT_TYPE
            elif "singleVisual" in data.get("config", data):
                target = data.get("config", data)
                if isinstance(target, str):
                    target = json.loads(target)
                target["singleVisual"]["visualType"] = self.REPLACEMENT_TYPE
                if isinstance(data.get("config"), str):
                    data["config"] = json.dumps(target)
            elif "visualType" in data:
                data["visualType"] = self.REPLACEMENT_TYPE

            self._write_json_file(visual_path, data)
            self.fixes_applied.append(
                f"[{page_name}] Visual '{vid}': {vtype} -> {self.REPLACEMENT_TYPE}"
            )

    def _get_visual_type(self, data: dict) -> str:
        # PBIR 2.6+: visualType under `visual`.
        v = data.get("visual")
        if isinstance(v, dict) and v.get("visualType"):
            return v["visualType"]
        # Legacy formats
        config = data.get("config", data)
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                return ""
        sv = config.get("singleVisual", {})
        if sv:
            return sv.get("visualType", "")
        return data.get("visualType", "")


class FixPageSize(BaseFixer):
    """Upgrade page sizes to Full HD (1920x1080)."""

    fixer_id = "fix_page_size"
    name = "Actualizar páginas a Full HD"
    description = (
        "Actualiza las dimensiones de las páginas a resolución Full HD (1920x1080) "
        "para mejor aprovechamiento del espacio en pantallas modernas."
    )
    category = "report"
    severity = "info"
    requires_pbip = True

    TARGET_WIDTH = 1920
    TARGET_HEIGHT = 1080

    def scan(self):
        for page_path, data, page_name in self._iter_page_files():
            w = data.get("width", 1280)
            h = data.get("height", 720)
            # Skip tooltip pages
            if str(data.get("config", {}).get("type", "")).lower() == "tooltip":
                continue
            if data.get("visibility", 0) == 1:
                continue
            if w != self.TARGET_WIDTH or h != self.TARGET_HEIGHT:
                self.issues.append(
                    f"[{page_name}] Tamaño actual: {w}x{h} -> debería ser {self.TARGET_WIDTH}x{self.TARGET_HEIGHT}"
                )

    def fix(self):
        for page_path, data, page_name in self._iter_page_files():
            w = data.get("width", 1280)
            h = data.get("height", 720)
            if str(data.get("config", {}).get("type", "")).lower() == "tooltip":
                continue
            if data.get("visibility", 0) == 1:
                continue
            if w == self.TARGET_WIDTH and h == self.TARGET_HEIGHT:
                continue

            old_w, old_h = w, h
            scale_x = self.TARGET_WIDTH / old_w if old_w else 1
            scale_y = self.TARGET_HEIGHT / old_h if old_h else 1

            data["width"] = self.TARGET_WIDTH
            data["height"] = self.TARGET_HEIGHT

            self._write_json_file(page_path, data)

            # Scale visual positions proportionally
            page_dir = page_path.replace("page.json", "").rstrip("/\\")
            self._scale_visuals_in_page(page_dir, scale_x, scale_y)

            self.fixes_applied.append(
                f"[{page_name}] {old_w}x{old_h} -> {self.TARGET_WIDTH}x{self.TARGET_HEIGHT}"
            )

    def _scale_visuals_in_page(self, page_dir: str, scale_x: float, scale_y: float):
        import os
        visuals_dir = os.path.join(page_dir, "visuals")
        if not os.path.isdir(visuals_dir):
            return
        for vid in os.listdir(visuals_dir):
            vpath = os.path.join(visuals_dir, vid, "visual.json")
            if not os.path.exists(vpath):
                continue
            data = self._read_json_file(vpath)
            if not data:
                continue
            pos = data.get("position", {})
            if pos:
                pos["x"] = round(pos.get("x", 0) * scale_x)
                pos["y"] = round(pos.get("y", 0) * scale_y)
                pos["width"] = round(pos.get("width", 0) * scale_x)
                pos["height"] = round(pos.get("height", 0) * scale_y)
                data["position"] = pos
                self._write_json_file(vpath, data)


class FixVisualAlignment(BaseFixer):
    """Snap visuals to an 8px grid for consistent alignment."""

    fixer_id = "fix_visual_alignment"
    name = "Alinear visuals a grilla"
    description = (
        "Alinea las posiciones y tamaños de los visuals a una grilla de 8px "
        "para lograr un diseño más limpio y profesional."
    )
    category = "report"
    severity = "info"
    requires_pbip = True

    GRID_SIZE = 8

    def scan(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            pos = data.get("position", {})
            if not pos:
                continue
            for key in ("x", "y", "width", "height"):
                val = pos.get(key, 0)
                if val % self.GRID_SIZE != 0:
                    self.issues.append(
                        f"[{page_name}] Visual '{vid}': {key}={val} no alineado a grilla de {self.GRID_SIZE}px"
                    )
                    break  # One issue per visual is enough

    def fix(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            pos = data.get("position", {})
            if not pos:
                continue
            changed = False
            for key in ("x", "y", "width", "height"):
                val = pos.get(key, 0)
                snapped = self._snap_to_grid(val)
                if snapped != val:
                    pos[key] = snapped
                    changed = True
            if changed:
                data["position"] = pos
                self._write_json_file(visual_path, data)
                self.fixes_applied.append(
                    f"[{page_name}] Visual '{vid}' alineado a grilla de {self.GRID_SIZE}px"
                )

    def _snap_to_grid(self, value) -> int:
        return round(value / self.GRID_SIZE) * self.GRID_SIZE


class FixRemoveUnusedCustomVisuals(BaseFixer):
    """Detect custom visuals declared but not used in any page."""

    fixer_id = "fix_unused_custom_visuals"
    name = "Eliminar custom visuals sin uso"
    description = (
        "Detecta custom visuals registrados en el reporte pero que no se usan "
        "en ninguna página. Estos agregan peso innecesario al archivo."
    )
    category = "report"
    severity = "info"
    requires_pbip = True

    def scan(self):
        registered = set(self.result.custom_visuals_list)
        used = set()
        for _, data, _, _ in self._iter_visual_files():
            vtype = data.get("visualType", "")
            config = data.get("config", {})
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except json.JSONDecodeError:
                    config = {}
            sv = config.get("singleVisual", {})
            if sv:
                vtype = sv.get("visualType", vtype)
            if vtype:
                used.add(vtype)

        unused = registered - used
        for cv in unused:
            self.issues.append(f"Custom visual '{cv}' registrado pero no usado en ninguna página")

    def fix(self):
        # For PBIR, custom visuals are in definition/customVisuals/ folder
        import os
        report_def = self._get_report_definition_path()
        cv_dir = os.path.join(report_def, "customVisuals")
        if not os.path.isdir(cv_dir):
            self.scan()  # Re-scan to populate issues (scan-only in this case)
            return

        registered = set(os.listdir(cv_dir))
        used = set()
        for _, data, _, _ in self._iter_visual_files():
            config = data.get("config", data)
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except json.JSONDecodeError:
                    continue
            sv = config.get("singleVisual", {})
            vtype = sv.get("visualType", data.get("visualType", ""))
            if vtype:
                used.add(vtype)

        for cv_name in registered:
            cv_path = os.path.join(cv_dir, cv_name)
            if not os.path.isdir(cv_path):
                continue
            if cv_name not in used:
                import shutil
                shutil.rmtree(cv_path)
                self.fixes_applied.append(f"Custom visual '{cv_name}' eliminado")


class FixHideVisualFilters(BaseFixer):
    """Remove ShowItemsWithNoData from visuals to improve performance."""

    fixer_id = "fix_hide_visual_filters"
    name = "Deshabilitar ShowItemsWithNoData"
    description = (
        "Deshabilita la opción 'Mostrar elementos sin datos' en los visuals, "
        "que puede degradar el rendimiento de las consultas."
    )
    category = "report"
    severity = "warning"
    requires_pbip = True

    def scan(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            if self._has_show_items_no_data(data):
                self.issues.append(
                    f"[{page_name}] Visual '{vid}': ShowItemsWithNoData habilitado"
                )

    def fix(self):
        for visual_path, data, page_name, vid in self._iter_visual_files():
            if not self._has_show_items_no_data(data):
                continue
            self._remove_show_items_no_data(data)
            self._write_json_file(visual_path, data)
            self.fixes_applied.append(
                f"[{page_name}] Visual '{vid}': ShowItemsWithNoData deshabilitado"
            )

    def _has_show_items_no_data(self, data: dict) -> bool:
        text = json.dumps(data)
        return "showItemsWithNoData" in text.lower() or "ShowItemsNoData" in text

    def _remove_show_items_no_data(self, data: dict):
        """Recursively remove showItemsWithNoData settings."""
        if isinstance(data, dict):
            keys_to_remove = []
            for key, val in data.items():
                if key.lower() in ("showitemswithnodata", "showitemsnodata"):
                    keys_to_remove.append(key)
                elif isinstance(val, (dict, list)):
                    self._remove_show_items_no_data(val)
            for key in keys_to_remove:
                del data[key]
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._remove_show_items_no_data(item)
