"""Power BI Performance Analyzer JSON parser.

Power BI Desktop exports a JSON con esta estructura (simplificada):

    {
      "version": "1.4.0",
      "events": [
        { "name": "Query", "id": "guid", "parent": "guid-visual",
          "start": "...", "end": "...", "duration": ms,
          "metrics": { "queryText": "...", ... } },
        { "name": "Visual display", "id": "guid", "parent": "guid-visual", ... },
        { "name": "Other", "id": "guid", "parent": "guid-visual", ... },
        { "name": "Visual container lifecycle", "id": "guid-visual",
          "metrics": { "visualName": "...", "visualType": "...",
                       "visualTitle": "..." } },
        ...
      ]
    }

Cada visual genera 3 sub-eventos (Query/Render/Other) que comparten un
mismo parent (el visual container). El total por visual es la suma.
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional


# Categorías de duración → colores y labels
SEV_GOOD = "good"      # < 500ms
SEV_WARN = "warning"   # 500-1000ms
SEV_BAD = "critical"   # > 1000ms


def classify(ms: float) -> str:
    if ms < 500:
        return SEV_GOOD
    if ms < 1000:
        return SEV_WARN
    return SEV_BAD


def parse(json_text: str) -> Dict[str, Any]:
    """Parsea un export de Performance Analyzer y devuelve estructura agregada.

    Returns:
        {
            'version': str,
            'visuals': [
                {
                    'id': str,
                    'name': str,
                    'type': str,
                    'page': str,
                    'total_ms': float,
                    'dax_ms': float,
                    'render_ms': float,
                    'other_ms': float,
                    'severity': 'good'|'warning'|'critical',
                    'queries': [str, ...]  # textos DAX detectados
                },
                ...
            ],
            'totals': {
                'n_visuals': int,
                'total_ms': float,
                'slow_count': int,   # >= 500ms
                'very_slow_count': int,  # >= 1000ms
                'top_offender': str | None,
            },
            'raw_event_count': int,
            'errors': [str, ...]
        }
    """
    errors: List[str] = []
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return {
            'version': '',
            'visuals': [],
            'totals': {'n_visuals': 0, 'total_ms': 0, 'slow_count': 0,
                       'very_slow_count': 0, 'top_offender': None},
            'raw_event_count': 0,
            'errors': [f'JSON inválido: {e}'],
        }

    events = data.get('events', []) or []
    version = data.get('version', '')

    # Mapas auxiliares
    visual_meta: Dict[str, Dict[str, str]] = {}  # parent_id -> meta dict
    durations: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {'dax': 0.0, 'render': 0.0, 'other': 0.0}
    )
    queries: Dict[str, List[str]] = defaultdict(list)
    page_by_visual: Dict[str, str] = {}

    for ev in events:
        if not isinstance(ev, dict):
            continue

        name = (ev.get('name') or '').lower()
        ev_id = ev.get('id', '')
        parent = ev.get('parent') or ev_id  # algunos eventos son el propio visual
        metrics = ev.get('metrics') or {}
        if not isinstance(metrics, dict):
            metrics = {}

        # ── Metadatos del visual (su evento "container" no tiene duration) ──
        # Suele tener visualName/visualType en metrics.
        if metrics.get('visualName') or metrics.get('visualType') or metrics.get('visualTitle'):
            meta = visual_meta.setdefault(parent if parent else ev_id, {})
            for k_src, k_dst in (
                ('visualName', 'name'),
                ('visualType', 'type'),
                ('visualTitle', 'title'),
                ('reportSection', 'page'),
                ('pageName', 'page'),
            ):
                v = metrics.get(k_src)
                if v and not meta.get(k_dst):
                    meta[k_dst] = str(v)

        # ── Duración del evento ──
        duration = _get_duration_ms(ev)
        if duration is None:
            continue

        # Clasificar contribución
        if 'query' in name or 'dax' in name:
            durations[parent]['dax'] += duration
        elif 'visual' in name and ('display' in name or 'render' in name):
            durations[parent]['render'] += duration
        elif 'other' in name:
            durations[parent]['other'] += duration
        else:
            # Eventos sin clasificar van a "other"
            durations[parent]['other'] += duration

        # Texto DAX si está
        qt = metrics.get('queryText') or metrics.get('query')
        if qt and isinstance(qt, str):
            queries[parent].append(qt.strip())

        # Página: a veces viene en el evento, no en el container
        page = metrics.get('reportSection') or metrics.get('pageName')
        if page and not page_by_visual.get(parent):
            page_by_visual[parent] = str(page)

    # ── Armar lista de visuales ──
    visuals: List[Dict[str, Any]] = []
    for vid, d in durations.items():
        meta = visual_meta.get(vid, {})
        total = d['dax'] + d['render'] + d['other']
        if total <= 0:
            continue
        visuals.append({
            'id': vid,
            'name': meta.get('title') or meta.get('name') or '(sin nombre)',
            'type': meta.get('type', '?'),
            'page': page_by_visual.get(vid) or meta.get('page', '?'),
            'total_ms': round(total, 1),
            'dax_ms': round(d['dax'], 1),
            'render_ms': round(d['render'], 1),
            'other_ms': round(d['other'], 1),
            'severity': classify(total),
            'queries': queries.get(vid, [])[:3],  # max 3 queries para no inflar
        })

    visuals.sort(key=lambda v: v['total_ms'], reverse=True)

    # ── Totales ──
    n_slow = sum(1 for v in visuals if v['total_ms'] >= 500)
    n_very_slow = sum(1 for v in visuals if v['total_ms'] >= 1000)
    total_ms = sum(v['total_ms'] for v in visuals)
    top = visuals[0]['name'] if visuals else None

    return {
        'version': version,
        'visuals': visuals,
        'totals': {
            'n_visuals': len(visuals),
            'total_ms': round(total_ms, 1),
            'slow_count': n_slow,
            'very_slow_count': n_very_slow,
            'top_offender': top,
        },
        'raw_event_count': len(events),
        'errors': errors,
    }


def _get_duration_ms(event: Dict[str, Any]) -> Optional[float]:
    """Extrae duración en ms del evento. Tolera varios shapes del JSON."""
    # Power BI usa varios campos según versión del export
    for key in ('duration', 'totalDuration', 'durationMs', 'elapsedMs'):
        v = event.get(key)
        if isinstance(v, (int, float)) and v >= 0:
            return float(v)

    # Caso fallback: start/end ISO
    start = event.get('start')
    end = event.get('end')
    if start and end:
        try:
            from datetime import datetime
            t0 = datetime.fromisoformat(start.replace('Z', '+00:00'))
            t1 = datetime.fromisoformat(end.replace('Z', '+00:00'))
            return max((t1 - t0).total_seconds() * 1000.0, 0.0)
        except (ValueError, AttributeError):
            return None

    return None
