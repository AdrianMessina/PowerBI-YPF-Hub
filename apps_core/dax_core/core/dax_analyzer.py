"""
Analizador de código DAX
Detecta problemas de performance y anti-patrones
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from .dax_parser import ParsedDaxExpression, calculate_complexity


@dataclass
class Issue:
    """Representa un problema detectado en el código DAX"""
    id: str
    severity: str  # 'critical', 'warning', 'info'
    category: str
    title: str
    description: str
    line: int = 0
    column: int = 0
    snippet: str = ""
    learn_more: str = ""


@dataclass
class PerformanceMetrics:
    """Métricas de performance del código DAX"""
    complexity: int  # 0-100
    nested_iterators: int
    context_transitions: int
    variables_used: int
    function_count: int
    estimated_impact: str  # 'high', 'medium', 'low'


def analyze_dax(parsed: ParsedDaxExpression) -> Tuple[List[Issue], PerformanceMetrics]:
    """
    Analiza código DAX parseado y detecta problemas

    Args:
        parsed: Expresión DAX parseada

    Returns:
        Tupla con (lista de issues, métricas de performance)
    """
    issues = []

    # Ejecutar todas las verificaciones de anti-patrones
    check_nested_iterators(parsed, issues)
    check_filter_without_keepfilters(parsed, issues)
    check_missing_variables(parsed, issues)
    check_calculate_nesting(parsed, issues)
    check_all_in_filter(parsed, issues)
    check_expensive_functions(parsed, issues)
    check_context_transitions(parsed, issues)
    check_calculated_columns_in_measures(parsed, issues)
    check_repeated_expressions(parsed, issues)

    # Calcular métricas
    metrics = calculate_metrics(parsed)

    return issues, metrics


def check_nested_iterators(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta iteradores anidados (muy costosos)"""
    iterators = ['SUMX', 'AVERAGEX', 'COUNTX', 'COUNTAX', 'MINX', 'MAXX', 'CONCATENATEX', 'RANKX']

    for outer_iterator in iterators:
        # Búsqueda simple de patrones anidados
        outer_pattern = re.compile(rf'\b{outer_iterator}\s*\(', re.IGNORECASE)
        outer_matches = list(outer_pattern.finditer(parsed.raw))

        if outer_matches:
            for inner_iterator in iterators:
                # Buscar patrón de anidamiento
                nested_pattern = re.compile(
                    rf'\b{outer_iterator}\s*\(.*?\b{inner_iterator}\s*\(',
                    re.IGNORECASE | re.DOTALL
                )

                # Limitar búsqueda a los primeros 1000 caracteres después del iterador externo
                # para evitar backtracking excesivo
                for outer_match in outer_matches:
                    search_text = parsed.raw[outer_match.start():outer_match.start() + 1000]
                    if re.search(rf'\b{inner_iterator}\s*\(', search_text, re.IGNORECASE):
                        issues.append(Issue(
                            id='nested-iterators',
                            severity='critical',
                            category='Performance',
                            title='Iteradores anidados detectados',
                            description=f'Se detectó {inner_iterator} dentro de {outer_iterator}. Esto causa que cada fila de la tabla externa evalúe todas las filas de la tabla interna, resultando en complejidad O(n²) o mayor.',
                            snippet=search_text[:100] + '...',
                            learn_more='https://www.sqlbi.com/articles/optimizing-nested-iterators-in-dax/'
                        ))
                        break  # Solo reportar una vez por iterador externo


def check_filter_without_keepfilters(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta FILTER en CALCULATE sin KEEPFILTERS"""
    calculate_with_filter = re.compile(r'CALCULATE\s*\([^)]*FILTER\s*\(', re.IGNORECASE)

    if calculate_with_filter.search(parsed.raw) and 'KEEPFILTERS' not in parsed.raw.upper():
        issues.append(Issue(
            id='filter-without-keepfilters',
            severity='warning',
            category='Filter Context',
            title='FILTER en CALCULATE sin KEEPFILTERS',
            description='Usar FILTER directamente en CALCULATE puede sobrescribir filtros existentes. Considera usar KEEPFILTERS(FILTER(...)) para mantener el contexto de filtro existente.',
            learn_more='https://www.sqlbi.com/articles/using-keepfilters-in-dax/'
        ))


def check_missing_variables(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta expresiones repetidas que deberían usar variables"""
    # Contar referencias a CALCULATE (sin intentar extraer todo el contenido)
    calculate_pattern = re.compile(r'\bCALCULATE\s*\(', re.IGNORECASE)
    calculate_count = len(calculate_pattern.findall(parsed.raw))

    if calculate_count > 2 and len(parsed.variables) == 0:
        issues.append(Issue(
            id='missing-variables',
            severity='warning',
            category='Code Quality',
            title='Múltiples CALCULATE sin variables',
            description='Se detectaron múltiples llamadas a CALCULATE. Usar VAR para almacenar cálculos intermedios mejora la performance y legibilidad.',
            snippet='',
            learn_more='https://www.sqlbi.com/articles/using-variables-in-dax/'
        ))

    # Verificar código complejo sin variables
    if len(parsed.functions) > 5 and len(parsed.variables) == 0:
        issues.append(Issue(
            id='no-variables-complex',
            severity='info',
            category='Code Quality',
            title='Código complejo sin variables',
            description='Tu código tiene múltiples funciones pero no usa variables. Considera usar VAR para mejorar legibilidad y potencialmente performance.',
            learn_more='https://www.sqlbi.com/articles/using-variables-in-dax/'
        ))


def check_calculate_nesting(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta CALCULATEs anidados innecesarios"""
    nested_calculate = re.compile(r'CALCULATE\s*\([^)]*CALCULATE\s*\(', re.IGNORECASE)

    if nested_calculate.search(parsed.raw):
        issues.append(Issue(
            id='nested-calculate',
            severity='warning',
            category='Context Transition',
            title='CALCULATE anidado detectado',
            description='CALCULATE anidado causa múltiples transiciones de contexto innecesarias. Considera combinar los filtros en un solo CALCULATE.',
            learn_more='https://www.sqlbi.com/articles/understanding-context-transition/'
        ))


def check_all_in_filter(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta ALL() usado directamente en FILTER (muy ineficiente)"""
    all_in_filter = re.compile(r'FILTER\s*\(\s*ALL\s*\(', re.IGNORECASE)

    if all_in_filter.search(parsed.raw):
        issues.append(Issue(
            id='all-in-filter',
            severity='critical',
            category='Performance',
            title='ALL() usado en FILTER sobre tabla completa',
            description='FILTER(ALL(Tabla), ...) itera sobre todas las filas sin aprovechar índices. Considera usar CALCULATE con filtros o FILTER solo sobre columnas específicas.',
            learn_more='https://www.sqlbi.com/articles/best-practices-using-filter-and-all/'
        ))


def check_expensive_functions(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta funciones conocidas por ser costosas"""
    expensive_functions = [
        {
            'name': 'CROSSJOIN',
            'reason': 'genera producto cartesiano de tablas'
        },
        {
            'name': 'GENERATE',
            'reason': 'itera y genera filas para cada fila de entrada'
        },
        {
            'name': 'SUMMARIZE',
            'reason': 'puede ser reemplazado por SUMMARIZECOLUMNS (más eficiente)'
        },
        {
            'name': 'LOOKUPVALUE',
            'reason': 'hace búsquedas lineales, considera usar RELATED si hay relación'
        }
    ]

    for func_info in expensive_functions:
        pattern = re.compile(rf'\b{func_info["name"]}\s*\(', re.IGNORECASE)
        if pattern.search(parsed.raw):
            issues.append(Issue(
                id=f'expensive-{func_info["name"].lower()}',
                severity='warning',
                category='Performance',
                title=f'Función costosa: {func_info["name"]}',
                description=f'{func_info["name"]} {func_info["reason"]}. Evalúa si hay una alternativa más eficiente.',
                learn_more='https://www.sqlbi.com/articles/optimizing-dax-expressions/'
            ))


def check_context_transitions(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta transiciones de contexto problemáticas"""
    # En columnas calculadas, usar medidas causa transición de contexto
    if parsed.object_type == 'calculated-column':
        if parsed.measures:
            issues.append(Issue(
                id='measure-in-calculated-column',
                severity='critical',
                category='Context Transition',
                title='Medida usada en columna calculada',
                description='Usar medidas en columnas calculadas causa transición de contexto en cada fila, lo cual es muy costoso. Considera reescribir la lógica usando funciones de columna calculada.',
                learn_more='https://www.sqlbi.com/articles/understanding-context-transition/'
            ))


def check_calculated_columns_in_measures(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta uso de lógica de columnas calculadas en medidas"""
    if parsed.object_type == 'measure':
        has_earlier = re.search(r'\bEARLIER\s*\(', parsed.raw, re.IGNORECASE)

        if has_earlier:
            issues.append(Issue(
                id='earlier-in-measure',
                severity='warning',
                category='Code Quality',
                title='EARLIER detectado en medida',
                description='EARLIER se usa típicamente en columnas calculadas. Si estás intentando usar lógica de columna calculada en una medida, considera crear la columna calculada por separado o usar variables.',
                learn_more='https://www.sqlbi.com/articles/row-context-and-filter-context-in-dax/'
            ))


def check_repeated_expressions(parsed: ParsedDaxExpression, issues: List[Issue]) -> None:
    """Detecta referencias a medidas repetidas que deberían estar en variables"""
    measure_counts = {}

    for measure in parsed.measures:
        # Escapar caracteres especiales de regex en el nombre de la medida
        escaped_measure = re.escape(measure)
        pattern = re.compile(rf'\[{escaped_measure}\]')
        matches = pattern.findall(parsed.raw)
        if len(matches) > 2:
            measure_counts[measure] = len(matches)

    if measure_counts and len(parsed.variables) == 0:
        most_repeated = max(measure_counts.items(), key=lambda x: x[1])

        issues.append(Issue(
            id='repeated-measure-reference',
            severity='info',
            category='Code Quality',
            title='Referencia a medida repetida',
            description=f'La medida [{most_repeated[0]}] se usa {most_repeated[1]} veces. Considera almacenarla en una variable para evaluar solo una vez.',
            learn_more='https://www.sqlbi.com/articles/using-variables-in-dax/'
        ))


def find_repeated_expressions(expressions: List[str]) -> List[str]:
    """Encuentra expresiones que se repiten en el código"""
    counts = {}

    for expr in expressions:
        normalized = ' '.join(expr.split()).strip()
        counts[normalized] = counts.get(normalized, 0) + 1

    return [expr for expr, count in counts.items() if count > 1]


def calculate_metrics(parsed: ParsedDaxExpression) -> PerformanceMetrics:
    """Calcula métricas de performance"""
    complexity = calculate_complexity(parsed)

    nested_iterators = sum(1 for f in parsed.functions if f.nested)

    context_transition_funcs = ['CALCULATE', 'CALCULATETABLE']
    context_transitions = sum(
        1 for f in parsed.functions
        if f.name in context_transition_funcs
    )

    # Estimar impacto
    if complexity > 60 or nested_iterators > 0:
        estimated_impact = 'high'
    elif complexity > 30 or context_transitions > 2:
        estimated_impact = 'medium'
    else:
        estimated_impact = 'low'

    return PerformanceMetrics(
        complexity=complexity,
        nested_iterators=nested_iterators,
        context_transitions=context_transitions,
        variables_used=len(parsed.variables),
        function_count=len(parsed.functions),
        estimated_impact=estimated_impact
    )
