"""Data models for Power BI Analyzer 2.0."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FixMode(str, Enum):
    SCAN = "scan"
    FIX = "fix"
    SCAN_AND_FIX = "scan_and_fix"
    PREVIEW = "preview"


class FileType(str, Enum):
    PBIX = "pbix"
    PBIP = "pbip"


class ScoreCategory(str, Enum):
    EXCELLENT = "Excelente"
    GOOD = "Bueno"
    WARNING = "Atención"
    POOR = "Crítico"


@dataclass
class PageDetail:
    name: str
    visuals_count: int = 0
    filters_count: int = 0
    hidden: bool = False
    tooltip: bool = False
    width: int = 0
    height: int = 0
    visual_types: dict = field(default_factory=dict)


@dataclass
class MeasureDetail:
    name: str
    table: str
    expression: str = ""
    description: str = ""
    format_string: str = ""


@dataclass
class ColumnDetail:
    name: str
    table: str
    data_type: str = ""
    is_calculated: bool = False
    is_hidden: bool = False
    expression: str = ""
    summarize_by: str = ""


@dataclass
class RelationshipDetail:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_bidirectional: bool = False
    is_active: bool = True


@dataclass
class VisualDetail:
    visual_id: str
    visual_type: str
    page_name: str
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    title: str = ""
    fields: list = field(default_factory=list)
    filters: list = field(default_factory=list)


@dataclass
class MetricScore:
    value: Any
    status: str  # good, warning, critical
    score: float
    threshold_good: Any = None
    threshold_warning: Any = None
    threshold_critical: Any = None


@dataclass
class Recommendation:
    metric: str
    severity: Severity
    message: str
    current_value: Any = None
    target_value: Any = None
    fixable: bool = False
    fixer_id: str = ""


@dataclass
class FixResult:
    fixer_id: str
    fixer_name: str
    category: str
    issues_found: int = 0
    issues_fixed: int = 0
    details: list = field(default_factory=list)
    mode: FixMode = FixMode.SCAN
    success: bool = True
    error: str = ""
    # Trust & confidence fields
    confidence: str = "high"          # "high" | "medium" | "low"
    detection_method: str = ""        # "pattern_match" | "threshold" | "heuristic"
    affected_files: list = field(default_factory=list)
    before_preview: str = ""
    after_preview: str = ""
    is_manual: bool = False
    manual_steps: list = field(default_factory=list)
    validation_result: dict = field(default_factory=dict)
    severity: str = "warning"


@dataclass
class BackupInfo:
    backup_path: str
    created_at: str
    report_name: str
    file_count: int = 0
    size_mb: float = 0.0
    applied_fixers: list = field(default_factory=list)
    can_restore: bool = True


@dataclass
class AnalysisResult:
    report_name: str = ""
    report_path: str = ""
    file_type: FileType = FileType.PBIX
    model_analysis_available: bool = True
    model_analysis_note: str = ""

    # Counts
    total_pages: int = 0
    total_visuals: int = 0
    total_tables: int = 0
    total_measures: int = 0
    total_relationships: int = 0
    total_filters: int = 0
    total_columns: int = 0

    # Averages and maxes
    avg_visuals_per_page: float = 0
    max_visuals_per_page: int = 0
    max_visuals_page_name: str = ""
    avg_filters_per_page: float = 0
    max_filters_per_page: int = 0
    max_filters_page_name: str = ""

    # Model metrics
    complex_dax_measures: int = 0
    calculated_columns: int = 0
    calculated_tables: int = 0
    bidirectional_relationships: int = 0
    model_size_mb: float = 0
    model_size_source: str = ""  # 'pbix_zip', 'pbip_folder', 'unknown'
    auto_date_time_enabled: bool = False
    auto_date_time_tables_count: int = 0  # Cuántas LocalDateTable + Template hay

    # Desglose de tablas por tipo
    tables_by_type: dict = field(default_factory=dict)

    # ── Storage mode (Import / DirectQuery / Dual) ───────────────
    tables_by_mode: dict = field(default_factory=dict)          # {"import": 12, "directQuery": 3, "dual": 1}
    storage_mode_type: str = "import"                            # "import" | "directQuery" | "dual" | "composite"
    directquery_tables_detail: list = field(default_factory=list)   # [{"name","mode","source_snippet"}]
    directquery_issues: list = field(default_factory=list)      # [{"severity","table","issue","detail"}]
    query_folding_warnings: list = field(default_factory=list)  # [{"table","antipattern","snippet"}]

    # Design metrics
    slicers_count: int = 0
    buttons_count: int = 0
    shapes_count: int = 0
    textboxes_count: int = 0
    images_count: int = 0
    custom_visuals_count: int = 0
    embedded_images_count: int = 0
    embedded_images_mb: float = 0
    hidden_pages_count: int = 0
    tooltip_pages_count: int = 0
    bookmarks_count: int = 0
    has_custom_theme: bool = False
    theme_name: str = ""

    # Detail lists
    pages_detail: list = field(default_factory=list)
    measures_detail: list = field(default_factory=list)
    columns_detail: list = field(default_factory=list)
    calculated_columns_detail: list = field(default_factory=list)
    relationships_detail: list = field(default_factory=list)
    bidirectional_relationships_detail: list = field(default_factory=list)
    visuals_detail: list = field(default_factory=list)
    visual_types: dict = field(default_factory=dict)
    custom_visuals_list: list = field(default_factory=list)
    embedded_images_list: list = field(default_factory=list)
    measures_by_table: dict = field(default_factory=dict)
    columns_by_table: dict = field(default_factory=dict)
    bookmarks_detail: list = field(default_factory=list)

    # Scoring
    metric_scores: dict = field(default_factory=dict)
    overall_score: float = 0
    score_category: ScoreCategory = ScoreCategory.POOR

    # Recommendations
    recommendations: list = field(default_factory=list)

    # Fix results
    fix_results: list = field(default_factory=list)

    # Raw data for fixers
    _raw_report_data: dict = field(default_factory=dict, repr=False)
    _raw_model_data: dict = field(default_factory=dict, repr=False)
    _report_base_path: str = ""
    _model_base_path: str = ""
