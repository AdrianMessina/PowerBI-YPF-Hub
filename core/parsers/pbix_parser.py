"""PBIX file parser - reads .pbix ZIP archives."""

import json
import os
import zipfile


class PBIXParser:
    """Parses .pbix files (ZIP archive format)."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.layout = None
        self.model = None
        self.custom_visuals = []
        self.embedded_images = []
        self.model_available = False
        self.model_note = ""

    def parse(self) -> dict:
        """Parse the PBIX file and return structured data."""
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"PBIX file not found: {self.file_path}")

        with zipfile.ZipFile(self.file_path, "r") as zf:
            self._parse_layout(zf)
            self._parse_model(zf)
            self._parse_custom_visuals(zf)
            self._parse_embedded_images(zf)

        return {
            "layout": self.layout,
            "model": self.model,
            "custom_visuals": self.custom_visuals,
            "embedded_images": self.embedded_images,
            "model_available": self.model_available,
            "model_note": self.model_note,
            "file_size_mb": os.path.getsize(self.file_path) / (1024 * 1024),
        }

    def _parse_layout(self, zf: zipfile.ZipFile):
        try:
            raw = zf.read("Report/Layout")
            text = raw.decode("utf-16-le")
            # Remove BOM if present
            if text.startswith("\ufeff"):
                text = text[1:]
            self.layout = json.loads(text)
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
            self.layout = {}

    def _parse_model(self, zf: zipfile.ZipFile):
        # Try DataModelSchema first (JSON format)
        for entry_name in ["DataModelSchema", "DataModel"]:
            if entry_name not in [zi.filename for zi in zf.infolist()]:
                continue
            try:
                raw = zf.read(entry_name)
                for encoding in ["utf-8", "utf-16-le", "utf-8-sig"]:
                    try:
                        text = raw.decode(encoding)
                        if text.startswith("\ufeff"):
                            text = text[1:]
                        self.model = json.loads(text)
                        self.model_available = True
                        return
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
            except KeyError:
                continue

        self.model_available = False
        self.model_note = (
            "El modelo de datos no pudo ser leído del archivo PBIX. "
            "Esto es normal en archivos comprimidos modernos. "
            "Para análisis completo del modelo, use formato PBIP."
        )

    def _parse_custom_visuals(self, zf: zipfile.ZipFile):
        prefix = "Report/CustomVisuals/"
        seen = set()
        for zi in zf.infolist():
            if zi.filename.startswith(prefix):
                parts = zi.filename[len(prefix):].split("/")
                if parts and parts[0] and parts[0] not in seen:
                    seen.add(parts[0])
                    self.custom_visuals.append(parts[0])

    def _parse_embedded_images(self, zf: zipfile.ZipFile):
        prefix = "Report/StaticResources/"
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"}
        for zi in zf.infolist():
            if zi.filename.startswith(prefix):
                ext = os.path.splitext(zi.filename)[1].lower()
                if ext in image_exts:
                    self.embedded_images.append({
                        "name": os.path.basename(zi.filename),
                        "size_kb": zi.file_size / 1024,
                        "path": zi.filename,
                    })

    def get_model_size_mb(self) -> float:
        """Get the size of the data model within the PBIX."""
        if not os.path.isfile(self.file_path):
            return 0
        total = 0
        with zipfile.ZipFile(self.file_path, "r") as zf:
            for entry in ["DataModel", "DataModelSchema"]:
                for zi in zf.infolist():
                    if zi.filename == entry:
                        total += zi.file_size
        return total / (1024 * 1024)
