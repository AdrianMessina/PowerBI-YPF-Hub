"""
Generador de sugerencias de optimización para código DAX
"""

import re
from typing import List
from dataclasses import dataclass
from .dax_parser import ParsedDaxExpression
from .dax_analyzer import Issue


@dataclass
class Suggestion:
    """Sugerencia de optimización para código DAX"""
    id: str
    title: str
    description: str
    original_code: str
    suggested_code: str
    impact: str  # 'high', 'medium', 'low'
    reason: str


def generate_suggestions(parsed: ParsedDaxExpression, issues: List[Issue]) -> List[Suggestion]:
    """
    Genera sugerencias de optimización basadas en los problemas detectados

    Args:
        parsed: Expresión DAX parseada
        issues: Lista de problemas detectados

    Returns:
        Lista de sugerencias de optimización
    """
    suggestions = []

    # Generar sugerencias basadas en los issues
    for issue in issues:
        if issue.id == 'nested-iterators':
            suggestions.append(generate_nested_iterator_suggestion(parsed))
        elif issue.id == 'filter-without-keepfilters':
            suggestions.append(generate_keepfilters_suggestion(parsed))
        elif issue.id in ['missing-variables', 'no-variables-complex']:
            suggestions.append(generate_variable_suggestion(parsed))
        elif issue.id == 'nested-calculate':
            suggestions.append(generate_flatten_calculate_suggestion(parsed))
        elif issue.id == 'all-in-filter':
            suggestions.append(generate_all_in_filter_suggestion(parsed))

    # Sugerencia genérica de variables si hay expresiones repetidas
    if len(parsed.variables) == 0 and len(parsed.functions) > 3:
        var_suggestion = generate_generic_variable_suggestion(parsed)
        if var_suggestion and not any(s.id == 'add-variables' for s in suggestions):
            suggestions.append(var_suggestion)

    return suggestions


def generate_nested_iterator_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia para eliminar iteradores anidados"""
    example = """-- ❌ Original (nested iterators):
SUMX(
    Tabla1,
    SUMX(
        FILTER(Tabla2, Tabla2[ID] = Tabla1[ID]),
        Tabla2[Valor]
    )
)

-- ✅ Optimizado (usando variables y relaciones):
SUMX(
    Tabla1,
    VAR TablaFiltrada =
        FILTER(Tabla2, Tabla2[ID] = Tabla1[ID])
    RETURN
        CALCULATE(SUM(Tabla2[Valor]), TablaFiltrada)
)

-- ✅ Mejor aún (si existe relación):
SUMX(
    Tabla1,
    CALCULATE(SUM(Tabla2[Valor]))
)"""

    return Suggestion(
        id='optimize-nested-iterators',
        title='Eliminar iteradores anidados',
        description='Refactoriza para evitar iterar múltiples veces',
        original_code='Patrón detectado: SUMX(..., SUMX(...))',
        suggested_code=example,
        impact='high',
        reason='Reduce complejidad de O(n²) a O(n), mejorando drásticamente la performance en tablas grandes.'
    )


def generate_keepfilters_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia para usar KEEPFILTERS"""
    return Suggestion(
        id='add-keepfilters',
        title='Usar KEEPFILTERS para mantener contexto',
        description='Envuelve FILTER con KEEPFILTERS',
        original_code='CALCULATE([Medida], FILTER(...))',
        suggested_code='CALCULATE([Medida], KEEPFILTERS(FILTER(...)))',
        impact='medium',
        reason='KEEPFILTERS respeta los filtros existentes en lugar de sobrescribirlos, evitando resultados inesperados.'
    )


def generate_variable_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia para usar variables"""
    # Ejemplo genérico de uso de variables
    example = """-- ✅ Patrón recomendado:
VAR Ventas = SUM(Tabla[Ventas])
VAR Costos = SUM(Tabla[Costos])
VAR Margen = Ventas - Costos
RETURN
    DIVIDE(Margen, Ventas)

-- O para cálculos complejos:
VAR MiCalculo = CALCULATE(...)
RETURN
    IF(MiCalculo > 0, MiCalculo, BLANK())"""

    return Suggestion(
        id='add-variables',
        title='Introducir variables (VAR)',
        description='Almacena cálculos intermedios en variables',
        original_code='Expresiones repetidas o código sin variables',
        suggested_code=example,
        impact='medium',
        reason='Las variables se evalúan una sola vez y se reutilizan, mejorando performance y legibilidad.'
    )


def generate_flatten_calculate_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia para aplanar CALCULATEs anidados"""
    return Suggestion(
        id='flatten-calculate',
        title='Aplanar CALCULATEs anidados',
        description='Combina múltiples CALCULATE en uno solo',
        original_code="""CALCULATE(
    CALCULATE([Medida], Filtro1),
    Filtro2
)""",
        suggested_code="""CALCULATE(
    [Medida],
    Filtro1,
    Filtro2
)""",
        impact='medium',
        reason='Elimina transiciones de contexto innecesarias, reduciendo overhead de evaluación.'
    )


def generate_all_in_filter_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia para optimizar ALL en FILTER"""
    return Suggestion(
        id='optimize-all-filter',
        title='Optimizar uso de ALL en FILTER',
        description='Usa CALCULATE en lugar de FILTER(ALL(...))',
        original_code="""FILTER(
    ALL(Tabla),
    Tabla[Columna] = Valor
)""",
        suggested_code="""CALCULATE(
    VALUES(Tabla),
    Tabla[Columna] = Valor,
    REMOVEFILTERS(Tabla)
)

-- O mejor, si solo filtras una columna:
CALCULATETABLE(
    VALUES(Tabla),
    Tabla[Columna] = Valor,
    REMOVEFILTERS(Tabla)
)""",
        impact='high',
        reason='CALCULATE puede aprovechar índices y optimizaciones del motor, mientras que FILTER(ALL(...)) itera todas las filas.'
    )


def generate_generic_variable_suggestion(parsed: ParsedDaxExpression) -> Suggestion:
    """Sugerencia genérica de uso de variables"""
    # Solo sugerir si hay medidas usadas múltiples veces
    if not parsed.measures:
        return None

    return Suggestion(
        id='add-variables',
        title='Considerar uso de variables',
        description='Tu código tiene múltiples funciones. Variables pueden mejorar la legibilidad y potencialmente la performance.',
        original_code='Código actual sin variables',
        suggested_code="""-- Patrón recomendado:
VAR Paso1 = CALCULATE(...)
VAR Paso2 = FILTER(...)
VAR Resultado = SUMX(Paso2, ...)
RETURN
    Resultado""",
        impact='low',
        reason='Variables hacen el código más mantenible y pueden prevenir recálculos innecesarios.'
    )


def calculate_score(parsed: ParsedDaxExpression, issues: List[Issue]) -> int:
    """
    Calcula un score de calidad del código (0-100)

    Args:
        parsed: Expresión DAX parseada
        issues: Lista de problemas detectados

    Returns:
        Score entre 0 y 100
    """
    score = 100

    # Restar puntos por problemas
    for issue in issues:
        if issue.severity == 'critical':
            score -= 25
        elif issue.severity == 'warning':
            score -= 10
        elif issue.severity == 'info':
            score -= 5

    # Bonus por buenas prácticas
    if parsed.variables:
        score += 5

    # Penalizar alta complejidad
    if len(parsed.functions) > 10:
        score -= 10

    return max(0, min(100, score))
