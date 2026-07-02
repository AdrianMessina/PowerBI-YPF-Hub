"""
DAX Optimizer Core Module
Análisis y optimización de código DAX
"""

from .dax_parser import parse_dax_code, ParsedDaxExpression
from .dax_analyzer import analyze_dax, Issue, PerformanceMetrics
from .dax_suggestions import generate_suggestions, calculate_score, Suggestion
from .pbip_extractor import (
    extract_measures_from_pbip,
    parse_model_bim,
    parse_tmdl_files,
    validate_pbip_file,
    get_pbip_info
)
from .measure_ranker import (
    rank_measures,
    calculate_impact_score,
    get_priority_label,
    get_priority_color,
    get_summary_stats,
    filter_measures_by_priority,
    get_top_issues,
    RankedMeasure
)

__all__ = [
    # Parser
    'parse_dax_code',
    'ParsedDaxExpression',
    # Analyzer
    'analyze_dax',
    'Issue',
    'PerformanceMetrics',
    # Suggestions
    'generate_suggestions',
    'calculate_score',
    'Suggestion',
    # PBIP Extractor
    'extract_measures_from_pbip',
    'parse_model_bim',
    'parse_tmdl_files',
    'validate_pbip_file',
    'get_pbip_info',
    # Measure Ranker
    'rank_measures',
    'calculate_impact_score',
    'get_priority_label',
    'get_priority_color',
    'get_summary_stats',
    'filter_measures_by_priority',
    'get_top_issues',
    'RankedMeasure'
]
