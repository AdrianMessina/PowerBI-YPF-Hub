"""Aggregation Table Suggester — detecta medidas candidatas para tablas de agregación.

Analiza medidas DAX en busca de patrones que indican que podrían beneficiarse
de una tabla de agregación nativa de Power BI:

  - SUMMARIZECOLUMNS(...)
  - ADDCOLUMNS(VALUES(...), ...)
  - SUMMARIZE(...)
  - GROUPBY(...)

Estos patrones generan tablas en memoria en cada query, lo cual es costoso.
Una tabla de agregación pre-calculada mejora el performance dramáticamente.

Referencias:
  - https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced
  - https://www.sqlbi.com/articles/aggregations-in-power-bi/
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AggregationCandidate:
    """Representa una medida candidata para tabla de agregación."""
    measure_name: str
    table_name: str
    dax_expression: str
    pattern: str  # 'SUMMARIZECOLUMNS', 'ADDCOLUMNS+VALUES', 'SUMMARIZE', 'GROUPBY'
    confidence: str  # 'high', 'medium', 'low'
    reason: str
    match_snippet: str  # Fragmento DAX que matchea el patrón


# Patrones DAX a detectar (case-insensitive)
PATTERNS = {
    'SUMMARIZECOLUMNS': {
        'regex': r'\bSUMMARIZECOLUMNS\s*\(',
        'confidence': 'high',
        'reason': 'SUMMARIZECOLUMNS genera tabla en memoria — candidato ideal para agregación nativa',
    },
    'ADDCOLUMNS+VALUES': {
        'regex': r'\bADDCOLUMNS\s*\(\s*VALUES\s*\(',
        'confidence': 'high',
        'reason': 'ADDCOLUMNS(VALUES(...)) genera tabla en memoria — candidato ideal para agregación',
    },
    'SUMMARIZE': {
        'regex': r'\bSUMMARIZE\s*\(',
        'confidence': 'medium',
        'reason': 'SUMMARIZE puede beneficiarse de agregación si se usa en medidas pesadas',
    },
    'GROUPBY': {
        'regex': r'\bGROUPBY\s*\(',
        'confidence': 'medium',
        'reason': 'GROUPBY genera tabla en memoria — evaluar si se ejecuta frecuentemente',
    },
}


def scan_model(model_data: Dict[str, Any]) -> List[AggregationCandidate]:
    """Escanea modelo TMDL en busca de candidatos a agregación.

    Args:
        model_data: Diccionario con estructura del modelo (de tmdl_parser)

    Returns:
        Lista de AggregationCandidate ordenados por confidence (high > medium > low)
    """
    candidates: List[AggregationCandidate] = []

    # Modelo puede tener key "model" o directamente "tables"
    model_obj = model_data.get('model', model_data)
    tables = model_obj.get('tables', [])

    for table in tables:
        table_name = table.get('name', '')
        if not table_name:
            continue

        # Skip system tables
        if table_name.startswith('LocalDateTable_') or table_name.startswith('DateTableTemplate_'):
            continue

        measures = table.get('measures', [])
        for measure in measures:
            measure_name = measure.get('name', '')
            dax = measure.get('expression', '')

            if not measure_name or not dax:
                continue

            # Buscar patrones
            for pattern_name, pattern_def in PATTERNS.items():
                regex = pattern_def['regex']
                match = re.search(regex, dax, re.IGNORECASE)

                if match:
                    # Extraer snippet del match (50 chars antes y después)
                    start = max(0, match.start() - 50)
                    end = min(len(dax), match.end() + 50)
                    snippet = dax[start:end].strip()
                    if start > 0:
                        snippet = '...' + snippet
                    if end < len(dax):
                        snippet = snippet + '...'

                    candidates.append(AggregationCandidate(
                        measure_name=measure_name,
                        table_name=table_name,
                        dax_expression=dax,
                        pattern=pattern_name,
                        confidence=pattern_def['confidence'],
                        reason=pattern_def['reason'],
                        match_snippet=snippet,
                    ))

                    # Solo registrar el primer match por medida (evita duplicados)
                    break

    # Ordenar por confidence (high > medium > low)
    confidence_order = {'high': 0, 'medium': 1, 'low': 2}
    candidates.sort(key=lambda c: (confidence_order[c.confidence], c.table_name, c.measure_name))

    return candidates


def generate_recommendation(candidate: AggregationCandidate) -> str:
    """Genera recomendación de implementación para un candidato."""

    base = (
        f"**Convertir medida `{candidate.measure_name}` en tabla de agregación**\n\n"
        f"La medida usa `{candidate.pattern}` que genera una tabla en memoria en cada query. "
        f"Crear una tabla de agregación pre-calculada mejorará el performance.\n\n"
    )

    steps = (
        "**Pasos:**\n"
        "1. En Power BI Desktop, crear una **nueva tabla calculada** con el contenido "
        "de la expresión DAX de la medida (sin la función agregadora final)\n"
        "2. Configurar la tabla como **tabla de agregación**:\n"
        "   - Click derecho en la tabla → *Manage aggregations*\n"
        "   - Mapear columnas a la tabla de detalle correspondiente\n"
        "   - Definir funciones de agregación (SUM, COUNT, etc.)\n"
        "3. **Eliminar o reemplazar** la medida original — Power BI usará la agregación automáticamente\n"
        "4. Validar con **Performance Analyzer** que las queries usan la tabla de agregación\n\n"
    )

    docs = (
        "**Documentación:**\n"
        "- [Aggregations in Power BI](https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced)\n"
        "- [SQLBI: Aggregations patterns](https://www.sqlbi.com/articles/aggregations-in-power-bi/)\n"
    )

    return base + steps + docs


def get_summary_stats(candidates: List[AggregationCandidate]) -> Dict[str, Any]:
    """Genera estadísticas resumen de los candidatos."""

    total = len(candidates)
    by_confidence = {
        'high': sum(1 for c in candidates if c.confidence == 'high'),
        'medium': sum(1 for c in candidates if c.confidence == 'medium'),
        'low': sum(1 for c in candidates if c.confidence == 'low'),
    }
    by_pattern = {}
    for c in candidates:
        by_pattern[c.pattern] = by_pattern.get(c.pattern, 0) + 1

    affected_tables = len(set(c.table_name for c in candidates))

    return {
        'total': total,
        'by_confidence': by_confidence,
        'by_pattern': by_pattern,
        'affected_tables': affected_tables,
    }
