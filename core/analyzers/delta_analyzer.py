"""Delta Analyzer — compare analysis snapshots over time.

Saves JSON snapshots of each analysis and compares them to show
what changed between versions (new tables, removed measures,
score improvements, etc.)
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field

from core.models import AnalysisResult


SNAPSHOTS_DIR = ".pbi_fixer_snapshots"


@dataclass
class DeltaChange:
    category: str       # "table", "measure", "relationship", "visual", "score", "page"
    change_type: str    # "added", "removed", "modified"
    name: str
    detail: str = ""


@dataclass
class DeltaResult:
    snapshot_a: str     # timestamp A
    snapshot_b: str     # timestamp B
    report_name: str = ""
    score_before: float = 0
    score_after: float = 0
    changes: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def get_snapshots_dir(report_path: str) -> str:
    """Get or create the snapshots directory for a report."""
    base = report_path
    if os.path.isfile(base):
        base = os.path.dirname(base)
    snap_dir = os.path.join(base, SNAPSHOTS_DIR)
    os.makedirs(snap_dir, exist_ok=True)
    return snap_dir


def save_snapshot(result: AnalysisResult) -> str:
    """Save current analysis as a JSON snapshot. Returns snapshot path."""
    snap_dir = get_snapshots_dir(result.report_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{timestamp}.json"
    path = os.path.join(snap_dir, filename)

    data = {
        "timestamp": datetime.now().isoformat(),
        "report_name": result.report_name,
        "score": result.overall_score,
        "score_category": result.score_category.value,
        "total_pages": result.total_pages,
        "total_visuals": result.total_visuals,
        "total_tables": result.total_tables,
        "total_measures": result.total_measures,
        "total_relationships": result.total_relationships,
        "total_filters": result.total_filters,
        "total_columns": result.total_columns,
        "calculated_columns": result.calculated_columns,
        "bidirectional_relationships": result.bidirectional_relationships,
        "slicers_count": result.slicers_count,
        "custom_visuals_count": result.custom_visuals_count,
        "embedded_images_mb": round(result.embedded_images_mb, 2),
        "visual_types": result.visual_types,
        "tables": [t.name for t in _get_tables(result)],
        "measures": [
            {"name": m.name, "table": m.table}
            for m in result.measures_detail
        ],
        "relationships": [
            {"from": f"{r.from_table}.{r.from_column}",
             "to": f"{r.to_table}.{r.to_column}",
             "bidi": r.is_bidirectional}
            for r in result.relationships_detail
        ],
        "pages": [
            {"name": p.name, "visuals": p.visuals_count, "filters": p.filters_count}
            for p in result.pages_detail
        ],
        "recommendations_count": len(result.recommendations),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return path


def list_snapshots(report_path: str) -> list[dict]:
    """List available snapshots for a report, newest first."""
    snap_dir = get_snapshots_dir(report_path)
    snapshots = []
    for fname in os.listdir(snap_dir):
        if not fname.startswith("snapshot_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(snap_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            snapshots.append({
                "path": fpath,
                "filename": fname,
                "timestamp": data.get("timestamp", ""),
                "score": data.get("score", 0),
                "pages": data.get("total_pages", 0),
                "visuals": data.get("total_visuals", 0),
                "tables": data.get("total_tables", 0),
                "measures": data.get("total_measures", 0),
            })
        except Exception:
            continue

    return sorted(snapshots, key=lambda s: s["timestamp"], reverse=True)


def compare_snapshots(path_a: str, path_b: str) -> DeltaResult:
    """Compare two snapshots and return changes."""
    with open(path_a, "r", encoding="utf-8") as f:
        a = json.load(f)
    with open(path_b, "r", encoding="utf-8") as f:
        b = json.load(f)

    delta = DeltaResult(
        snapshot_a=a.get("timestamp", ""),
        snapshot_b=b.get("timestamp", ""),
        report_name=b.get("report_name", ""),
        score_before=a.get("score", 0),
        score_after=b.get("score", 0),
    )

    changes = []

    # Score change
    if a.get("score", 0) != b.get("score", 0):
        diff = b["score"] - a["score"]
        direction = "mejoro" if diff > 0 else "empeoro"
        changes.append(DeltaChange(
            "score", "modified", "Score",
            f"{a['score']:.1f} -> {b['score']:.1f} ({direction} {abs(diff):.1f} puntos)",
        ))

    # Numeric metrics
    metrics = [
        ("total_pages", "page", "Paginas"),
        ("total_visuals", "visual", "Visuals"),
        ("total_tables", "table", "Tablas"),
        ("total_measures", "measure", "Medidas"),
        ("total_relationships", "relationship", "Relaciones"),
        ("total_filters", "filter", "Filtros"),
        ("calculated_columns", "column", "Col. Calculadas"),
        ("bidirectional_relationships", "relationship", "Rel. Bidireccionales"),
        ("slicers_count", "visual", "Slicers"),
        ("custom_visuals_count", "visual", "Custom Visuals"),
        ("recommendations_count", "score", "Recomendaciones"),
    ]
    for key, cat, label in metrics:
        va = a.get(key, 0)
        vb = b.get(key, 0)
        if va != vb:
            diff = vb - va
            sign = "+" if diff > 0 else ""
            changes.append(DeltaChange(
                cat, "modified", label, f"{va} -> {vb} ({sign}{diff})"
            ))

    # Tables added/removed
    tables_a = set(a.get("tables", []))
    tables_b = set(b.get("tables", []))
    for t in tables_b - tables_a:
        changes.append(DeltaChange("table", "added", t, "Tabla nueva"))
    for t in tables_a - tables_b:
        changes.append(DeltaChange("table", "removed", t, "Tabla eliminada"))

    # Measures added/removed
    measures_a = {f"{m['table']}.{m['name']}" for m in a.get("measures", [])}
    measures_b = {f"{m['table']}.{m['name']}" for m in b.get("measures", [])}
    for m in measures_b - measures_a:
        changes.append(DeltaChange("measure", "added", m, "Medida nueva"))
    for m in measures_a - measures_b:
        changes.append(DeltaChange("measure", "removed", m, "Medida eliminada"))

    # Pages added/removed
    pages_a = {p["name"] for p in a.get("pages", [])}
    pages_b = {p["name"] for p in b.get("pages", [])}
    for p in pages_b - pages_a:
        changes.append(DeltaChange("page", "added", p, "Pagina nueva"))
    for p in pages_a - pages_b:
        changes.append(DeltaChange("page", "removed", p, "Pagina eliminada"))

    # Visual type distribution changes
    vt_a = a.get("visual_types", {})
    vt_b = b.get("visual_types", {})
    all_types = set(list(vt_a.keys()) + list(vt_b.keys()))
    for vt in all_types:
        ca = vt_a.get(vt, 0)
        cb = vt_b.get(vt, 0)
        if ca != cb:
            if ca == 0:
                changes.append(DeltaChange("visual", "added", vt, f"Nuevo tipo: {cb} visuals"))
            elif cb == 0:
                changes.append(DeltaChange("visual", "removed", vt, f"Tipo eliminado (tenia {ca})"))
            else:
                diff = cb - ca
                sign = "+" if diff > 0 else ""
                changes.append(DeltaChange("visual", "modified", vt, f"{ca} -> {cb} ({sign}{diff})"))

    delta.changes = changes

    # Summary counts
    delta.summary = {
        "added": sum(1 for c in changes if c.change_type == "added"),
        "removed": sum(1 for c in changes if c.change_type == "removed"),
        "modified": sum(1 for c in changes if c.change_type == "modified"),
        "total": len(changes),
    }

    return delta


def _get_tables(result: AnalysisResult) -> list:
    """Extract table names from raw model data.

    Excluye tablas automáticas de Power BI (LocalDateTable_*, DateTableTemplate_*)
    para que los snapshots y comparaciones reflejen solo el modelo del usuario.
    """
    model = result._raw_model_data
    model_data = model.get("model", model)
    tables = model_data.get("tables", [])

    class T:
        def __init__(self, name):
            self.name = name

    def _is_system(t: dict) -> bool:
        if t.get("isSystemTable", False):
            return True
        if t.get("tableType", "") in ("auto_datetime_local", "auto_datetime_template", "system_hidden"):
            return True
        tname = t.get("name", "")
        return tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_")

    return [
        T(t.get("name", ""))
        for t in tables
        if t.get("name", "") and not _is_system(t)
    ]
