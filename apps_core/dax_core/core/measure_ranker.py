"""
Sistema de ranking y priorización de medidas DAX
Calcula scores de impacto y prioriza medidas problemáticas
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class RankedMeasure:
    """Medida con información de ranking"""
    name: str
    table: str
    expression: str
    impact_score: int  # 0-100
    priority_label: str  # "Crítico", "Alto", "Medio", "Bajo"
    critical_issues: int
    warnings: int
    infos: int
    complexity: int
    issues: List
    metrics: any
    suggestions: List


def calculate_impact_score(issues: List, metrics: any, base_score: int) -> int:
    """
    Calcula el score de riesgo de una medida (0-100)
    MAYOR score = MAYOR riesgo de performance

    0-25: Bajo riesgo (código optimizado)
    26-50: Riesgo medio (algunas mejoras posibles)
    51-75: Alto riesgo (problemas de performance)
    76-100: Riesgo crítico (impacto severo en performance)

    Args:
        issues: Lista de problemas detectados
        metrics: Métricas de performance (puede ser None si el análisis falló)
        base_score: Score base calculado por dax_suggestions (0-100, menor=peor)

    Returns:
        Score de riesgo entre 0 y 100 (mayor=peor)
    """
    # Invertir el base_score: era 0-100 (menor=peor), ahora será 0-100 (mayor=peor)
    risk_score = 100 - base_score

    # Contar issues por severidad
    critical_count = sum(1 for i in issues if i.severity == 'critical')
    warning_count = sum(1 for i in issues if i.severity == 'warning')

    # Penalizaciones adicionales por patrones específicos
    for issue in issues:
        # Problemas críticos de performance
        if issue.id == 'nested-iterators':
            risk_score += 20  # Penalización extra por iteradores anidados
        elif issue.id == 'all-in-filter':
            risk_score += 15  # ALL en FILTER es muy costoso
        elif issue.id == 'measure-in-calculated-column':
            risk_score += 20  # Transición de contexto en cada fila

    # Solo aplicar penalizaciones basadas en metrics si está disponible
    if metrics is not None:
        # Penalizar por alta complejidad
        if metrics.complexity > 70:
            risk_score += 15
        elif metrics.complexity > 50:
            risk_score += 10

        # Penalizar por múltiples iteradores anidados
        if metrics.nested_iterators > 1:
            risk_score += 15
        elif metrics.nested_iterators == 1:
            risk_score += 10

        # Penalizar por muchas transiciones de contexto
        if metrics.context_transitions > 5:
            risk_score += 10

        # Reducir riesgo por uso de variables (buena práctica)
        if metrics.variables_used > 0:
            risk_score -= 5

    # Asegurar que esté en rango 0-100
    return max(0, min(100, risk_score))


def get_priority_label(impact_score: int) -> str:
    """
    Determina la etiqueta de prioridad basada en el score de riesgo

    Args:
        impact_score: Score de riesgo (0-100, mayor=peor)

    Returns:
        Etiqueta de prioridad
    """
    if impact_score >= 76:
        return "Crítico"
    elif impact_score >= 51:
        return "Alto"
    elif impact_score >= 26:
        return "Medio"
    else:
        return "Bajo"


def get_priority_color(impact_score: int) -> str:
    """
    Retorna el color para el badge de prioridad

    Args:
        impact_score: Score de riesgo (0-100, mayor=peor)

    Returns:
        Color en formato hexadecimal
    """
    if impact_score >= 76:
        return "#ff4757"  # Rojo
    elif impact_score >= 51:
        return "#ffa502"  # Naranja
    elif impact_score >= 26:
        return "#ffd32a"  # Amarillo
    else:
        return "#2ed573"  # Verde


def rank_measures(analyzed_measures: List[Dict]) -> List[RankedMeasure]:
    """
    Rankea medidas por impacto en performance

    Args:
        analyzed_measures: Lista de medidas analizadas con formato:
        {
            'name': str,
            'table': str,
            'expression': str,
            'issues': List[Issue],
            'metrics': PerformanceMetrics,
            'suggestions': List[Suggestion],
            'base_score': int
        }

    Returns:
        Lista de RankedMeasure ordenadas por impacto (peores primero)
    """
    ranked = []

    for measure_data in analyzed_measures:
        # Calcular score de impacto
        impact_score = calculate_impact_score(
            measure_data['issues'],
            measure_data['metrics'],
            measure_data['base_score']
        )

        # Contar issues por tipo
        critical_issues = sum(1 for i in measure_data['issues'] if i.severity == 'critical')
        warnings = sum(1 for i in measure_data['issues'] if i.severity == 'warning')
        infos = sum(1 for i in measure_data['issues'] if i.severity == 'info')

        # Obtener complejidad (0 si no hay metrics)
        complexity = measure_data['metrics'].complexity if measure_data['metrics'] is not None else 0

        # Crear objeto rankeado
        ranked_measure = RankedMeasure(
            name=measure_data['name'],
            table=measure_data['table'],
            expression=measure_data['expression'],
            impact_score=impact_score,
            priority_label=get_priority_label(impact_score),
            critical_issues=critical_issues,
            warnings=warnings,
            infos=infos,
            complexity=complexity,
            issues=measure_data['issues'],
            metrics=measure_data['metrics'],
            suggestions=measure_data['suggestions']
        )

        ranked.append(ranked_measure)

    # Ordenar por score de riesgo (mayor score primero = mayor riesgo)
    ranked.sort(key=lambda m: (-m.impact_score, -m.complexity))

    return ranked


def get_summary_stats(ranked_measures: List[RankedMeasure]) -> Dict:
    """
    Calcula estadísticas de resumen del análisis

    Args:
        ranked_measures: Lista de medidas rankeadas

    Returns:
        Diccionario con estadísticas
    """
    if not ranked_measures:
        return {
            'total_measures': 0,
            'critical_measures': 0,
            'high_priority': 0,
            'medium_priority': 0,
            'low_priority': 0,
            'avg_score': 0,
            'total_critical_issues': 0,
            'total_warnings': 0,
            'avg_complexity': 0
        }

    total = len(ranked_measures)
    critical = sum(1 for m in ranked_measures if m.impact_score >= 76)
    high = sum(1 for m in ranked_measures if 51 <= m.impact_score < 76)
    medium = sum(1 for m in ranked_measures if 26 <= m.impact_score < 51)
    low = sum(1 for m in ranked_measures if m.impact_score < 26)

    avg_score = sum(m.impact_score for m in ranked_measures) / total
    total_critical_issues = sum(m.critical_issues for m in ranked_measures)
    total_warnings = sum(m.warnings for m in ranked_measures)
    avg_complexity = sum(m.complexity for m in ranked_measures) / total

    return {
        'total_measures': total,
        'critical_measures': critical,
        'high_priority': high,
        'medium_priority': medium,
        'low_priority': low,
        'avg_score': round(avg_score, 1),
        'total_critical_issues': total_critical_issues,
        'total_warnings': total_warnings,
        'avg_complexity': round(avg_complexity, 1)
    }


def filter_measures_by_priority(ranked_measures: List[RankedMeasure], priority: str) -> List[RankedMeasure]:
    """
    Filtra medidas por nivel de prioridad

    Args:
        ranked_measures: Lista de medidas rankeadas
        priority: "Crítico", "Alto", "Medio", "Bajo", o "Todas"

    Returns:
        Lista filtrada de medidas
    """
    if priority == "Todas":
        return ranked_measures

    return [m for m in ranked_measures if m.priority_label == priority]


def get_top_issues(ranked_measures: List[RankedMeasure], top_n: int = 5) -> List[Dict]:
    """
    Obtiene los issues más comunes en el conjunto de medidas

    Args:
        ranked_measures: Lista de medidas rankeadas
        top_n: Número de issues top a retornar

    Returns:
        Lista de issues con conteos
    """
    issue_counts = {}

    for measure in ranked_measures:
        for issue in measure.issues:
            key = f"{issue.id}:{issue.title}"
            if key not in issue_counts:
                issue_counts[key] = {
                    'id': issue.id,
                    'title': issue.title,
                    'severity': issue.severity,
                    'count': 0,
                    'measures': []
                }
            issue_counts[key]['count'] += 1
            issue_counts[key]['measures'].append(measure.name)

    # Ordenar por frecuencia
    sorted_issues = sorted(issue_counts.values(), key=lambda x: x['count'], reverse=True)

    return sorted_issues[:top_n]
