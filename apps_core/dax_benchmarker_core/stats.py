"""Statistical analysis for DAX benchmark results.

Calcula percentiles, outliers, distribución, y genera recomendaciones
basadas en los tiempos medidos.
"""

import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .executor import BenchmarkResult


@dataclass
class BenchmarkStats:
    """Estadísticas agregadas de un benchmark."""
    total_executions: int
    successful_executions: int
    failed_executions: int

    # Tiempos (ms)
    mean: float
    median: float
    stddev: float
    min: float
    max: float

    # Percentiles
    p50: float
    p95: float
    p99: float

    # Outliers
    outlier_count: int
    outlier_threshold: float  # Valor sobre el cual se considera outlier

    # Row counts
    avg_row_count: int

    # Cold vs warm cache
    first_execution_ms: float  # Cold cache
    avg_warm_ms: float  # Promedio sin primera ejecución

    # Classification
    performance_class: str  # 'excellent', 'good', 'warning', 'critical'
    recommendation: str


def analyze_results(results: List[BenchmarkResult]) -> BenchmarkStats:
    """Analiza resultados de benchmark y genera estadísticas."""

    # Separar exitosos vs fallidos
    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    if not successful:
        # All failed
        return BenchmarkStats(
            total_executions=len(results),
            successful_executions=0,
            failed_executions=len(failed),
            mean=0.0,
            median=0.0,
            stddev=0.0,
            min=0.0,
            max=0.0,
            p50=0.0,
            p95=0.0,
            p99=0.0,
            outlier_count=0,
            outlier_threshold=0.0,
            avg_row_count=0,
            first_execution_ms=0.0,
            avg_warm_ms=0.0,
            performance_class='critical',
            recommendation='❌ Todas las ejecuciones fallaron. Verificar query DAX y conexión.',
        )

    # Extraer tiempos
    durations = [r.duration_ms for r in successful]
    row_counts = [r.row_count for r in successful]

    # Estadísticas básicas
    mean = statistics.mean(durations)
    median = statistics.median(durations)
    stddev = statistics.stdev(durations) if len(durations) > 1 else 0.0
    min_val = min(durations)
    max_val = max(durations)

    # Percentiles
    p50 = _percentile(durations, 50)
    p95 = _percentile(durations, 95)
    p99 = _percentile(durations, 99)

    # Outliers (IQR method)
    q1 = _percentile(durations, 25)
    q3 = _percentile(durations, 75)
    iqr = q3 - q1
    outlier_threshold = q3 + 1.5 * iqr
    outliers = [d for d in durations if d > outlier_threshold]

    # Row counts
    avg_rows = int(statistics.mean(row_counts)) if row_counts else 0

    # Cold vs warm
    first_exec_ms = durations[0]
    warm_durations = durations[1:] if len(durations) > 1 else durations
    avg_warm_ms = statistics.mean(warm_durations)

    # Clasificación de performance
    perf_class, recommendation = _classify_performance(p95, p99, len(outliers), len(durations))

    return BenchmarkStats(
        total_executions=len(results),
        successful_executions=len(successful),
        failed_executions=len(failed),
        mean=mean,
        median=median,
        stddev=stddev,
        min=min_val,
        max=max_val,
        p50=p50,
        p95=p95,
        p99=p99,
        outlier_count=len(outliers),
        outlier_threshold=outlier_threshold,
        avg_row_count=avg_rows,
        first_execution_ms=first_exec_ms,
        avg_warm_ms=avg_warm_ms,
        performance_class=perf_class,
        recommendation=recommendation,
    )


def _percentile(data: List[float], p: float) -> float:
    """Calcula percentil p de los datos (0-100)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    d0 = sorted_data[f]
    d1 = sorted_data[c]
    return d0 + (d1 - d0) * (k - f)


def _classify_performance(p95: float, p99: float, outlier_count: int, total_count: int) -> tuple[str, str]:
    """Clasifica performance y genera recomendación.

    Thresholds:
      - Excellent: p95 < 500ms
      - Good: p95 < 1000ms
      - Warning: p95 < 2000ms
      - Critical: p95 >= 2000ms

    También considera outliers: si >20% son outliers → degradar clase.
    """
    outlier_ratio = outlier_count / total_count if total_count > 0 else 0.0

    if p95 < 500:
        perf_class = 'excellent'
        rec = '✅ **Performance excelente** — query rápida y consistente (p95 < 500ms).'
    elif p95 < 1000:
        perf_class = 'good'
        rec = '🟢 **Performance buena** — query aceptable para uso interactivo (p95 < 1s).'
    elif p95 < 2000:
        perf_class = 'warning'
        rec = '🟡 **Performance aceptable** — considerar optimización si es query frecuente (p95 < 2s).'
    else:
        perf_class = 'critical'
        rec = '🔴 **Performance crítica** — query lenta, requiere optimización urgente (p95 >= 2s).'

    # Degradar clase si hay muchos outliers
    if outlier_ratio > 0.2:
        if perf_class == 'excellent':
            perf_class = 'good'
        elif perf_class == 'good':
            perf_class = 'warning'

        rec += f'\n\n⚠️ **Inconsistencia detectada**: {outlier_count} outliers ({outlier_ratio*100:.0f}%) — la query tiene tiempos muy variables.'

    # Agregar recomendación sobre cold cache si corresponde
    # (se agrega en el UI, acá solo clasificamos)

    return perf_class, rec


def format_duration(ms: float) -> str:
    """Formatea duración en ms a string legible."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}min"


def get_distribution_buckets(durations: List[float], num_buckets: int = 10) -> Dict[str, Any]:
    """Genera buckets para histograma de distribución.

    Returns:
        {
            'buckets': [{'range': '0-100ms', 'count': 5}, ...],
            'min': float,
            'max': float,
        }
    """
    if not durations:
        return {'buckets': [], 'min': 0.0, 'max': 0.0}

    min_val = min(durations)
    max_val = max(durations)

    if min_val == max_val:
        # All same value
        return {
            'buckets': [{'range': format_duration(min_val), 'count': len(durations)}],
            'min': min_val,
            'max': max_val,
        }

    bucket_size = (max_val - min_val) / num_buckets
    buckets = []

    for i in range(num_buckets):
        start = min_val + i * bucket_size
        end = start + bucket_size

        # Count values in this bucket
        count = sum(1 for d in durations if start <= d < end or (i == num_buckets - 1 and d == end))

        if count > 0:  # Solo incluir buckets con datos
            buckets.append({
                'range': f"{format_duration(start)}-{format_duration(end)}",
                'start': start,
                'end': end,
                'count': count,
            })

    return {
        'buckets': buckets,
        'min': min_val,
        'max': max_val,
    }
