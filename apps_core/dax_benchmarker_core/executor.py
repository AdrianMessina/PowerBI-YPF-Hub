"""DAX Query Executor — ejecuta queries DAX múltiples veces y mide tiempos.

Soporta dos modos:
  1. pbi-cli (si está conectado a un dataset via `pbi connect`)
  2. Simulación local (para testing sin conexión real)

El modo real requiere pbi-cli instalado y autenticado.
"""

import subprocess
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Resultado de una ejecución individual de query."""
    iteration: int
    duration_ms: float
    row_count: int
    error: Optional[str] = None


def execute_dax_query(query: str, iterations: int = 20, use_simulation: bool = False) -> List[BenchmarkResult]:
    """Ejecuta una query DAX N veces y retorna tiempos.

    Args:
        query: Query DAX a ejecutar
        iterations: Número de ejecuciones
        use_simulation: Si True, simula tiempos (para testing sin pbi-cli)

    Returns:
        Lista de BenchmarkResult con tiempos de cada ejecución
    """
    results: List[BenchmarkResult] = []

    for i in range(iterations):
        if use_simulation:
            result = _simulate_execution(i, query)
        else:
            result = _execute_via_pbi_cli(i, query)

        results.append(result)

        # Small delay between executions to avoid rate limits
        if not use_simulation and i < iterations - 1:
            time.sleep(0.1)

    return results


def _execute_via_pbi_cli(iteration: int, query: str) -> BenchmarkResult:
    """Ejecuta query via pbi-cli y mide tiempo."""
    try:
        start = time.perf_counter()

        # Execute via pbi-cli
        # pbi query eval --expression "QUERY" --format json
        result = subprocess.run(
            ['pbi', 'query', 'eval', '--expression', query, '--format', 'json'],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
        )

        end = time.perf_counter()
        duration_ms = (end - start) * 1000.0

        if result.returncode != 0:
            return BenchmarkResult(
                iteration=iteration,
                duration_ms=duration_ms,
                row_count=0,
                error=result.stderr.strip() or "Query failed",
            )

        # Parse JSON output to count rows
        try:
            data = json.loads(result.stdout)
            # pbi-cli returns array of rows
            row_count = len(data) if isinstance(data, list) else 0
        except (json.JSONDecodeError, TypeError):
            row_count = 0

        return BenchmarkResult(
            iteration=iteration,
            duration_ms=duration_ms,
            row_count=row_count,
            error=None,
        )

    except subprocess.TimeoutExpired:
        return BenchmarkResult(
            iteration=iteration,
            duration_ms=300000.0,  # 5 min
            row_count=0,
            error="Query timeout (>5min)",
        )
    except FileNotFoundError:
        return BenchmarkResult(
            iteration=iteration,
            duration_ms=0.0,
            row_count=0,
            error="pbi-cli not found — install with: pipx install pbi-cli-tool",
        )
    except Exception as e:
        return BenchmarkResult(
            iteration=iteration,
            duration_ms=0.0,
            row_count=0,
            error=str(e),
        )


def _simulate_execution(iteration: int, query: str) -> BenchmarkResult:
    """Simula ejecución para testing (sin pbi-cli real).

    Genera tiempos sintéticos basados en la complejidad de la query:
      - Queries simples (EVALUATE, sin CALCULATE): 50-200ms
      - Queries con CALCULATE: 200-800ms
      - Queries con múltiples CALCULATE o iteradores: 500-2000ms
      - Cold cache (primera ejecución): +50% tiempo

    Simula outliers ocasionales (+2x tiempo) para testing de detección.
    """
    import random

    # Base time según complejidad
    query_upper = query.upper()
    if 'CALCULATE' not in query_upper and 'FILTER' not in query_upper:
        base_ms = random.uniform(50, 200)
    elif query_upper.count('CALCULATE') == 1:
        base_ms = random.uniform(200, 800)
    else:
        base_ms = random.uniform(500, 2000)

    # Cold cache penalty (primera ejecución)
    if iteration == 0:
        base_ms *= 1.5

    # Outliers ocasionales (5% chance)
    if random.random() < 0.05:
        base_ms *= 2.0

    # Ruido normal (+/- 10%)
    duration_ms = base_ms * random.uniform(0.9, 1.1)

    # Row count simulado
    row_count = random.randint(100, 10000)

    time.sleep(duration_ms / 1000.0)  # Simular delay real

    return BenchmarkResult(
        iteration=iteration,
        duration_ms=duration_ms,
        row_count=row_count,
        error=None,
    )


def check_pbi_cli_available() -> Dict[str, Any]:
    """Verifica si pbi-cli está disponible y conectado.

    Returns:
        {
            'available': bool,
            'connected': bool,
            'error': Optional[str],
            'version': Optional[str],
        }
    """
    try:
        # Check if pbi command exists
        result = subprocess.run(
            ['pbi', '--version'],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return {
                'available': False,
                'connected': False,
                'error': 'pbi-cli not responding',
                'version': None,
            }

        version = result.stdout.strip()

        # Check if connected to a dataset
        conn_result = subprocess.run(
            ['pbi', 'connection', 'show'],
            capture_output=True,
            text=True,
            timeout=5,
        )

        connected = conn_result.returncode == 0

        return {
            'available': True,
            'connected': connected,
            'error': None if connected else 'No dataset connected — run: pbi connect',
            'version': version,
        }

    except FileNotFoundError:
        return {
            'available': False,
            'connected': False,
            'error': 'pbi-cli not installed',
            'version': None,
        }
    except subprocess.TimeoutExpired:
        return {
            'available': False,
            'connected': False,
            'error': 'pbi-cli timeout',
            'version': None,
        }
    except Exception as e:
        return {
            'available': False,
            'connected': False,
            'error': str(e),
            'version': None,
        }
