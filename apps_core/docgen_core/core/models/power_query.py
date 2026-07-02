"""
Data model for Power Query (M) queries
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class DataSourceType(Enum):
    """Types of data sources"""
    SQL_SERVER = "sql_server"
    EXCEL = "excel"
    SHAREPOINT = "sharepoint"
    WEB = "web"
    ODATA = "odata"
    FOLDER = "folder"
    CSV = "csv"
    JSON = "json"
    API = "api"
    CALCULATED = "calculated"
    OTHER = "other"


@dataclass
class PowerQuery:
    """
    Represents a Power Query (M query) in the model
    """
    name: str
    expression: str
    table: Optional[str] = None
    source_type: DataSourceType = DataSourceType.OTHER
    description: Optional[str] = None

    # Computed properties
    expression_length: int = field(default=0, init=False)
    step_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.expression_length = len(self.expression)
        self._detect_source_type()
        self._count_steps()

    def _detect_source_type(self):
        """Auto-detect source type from M expression"""
        expr_lower = self.expression.lower()

        detection_map = {
            'sql.database': DataSourceType.SQL_SERVER,
            'excel.workbook': DataSourceType.EXCEL,
            'sharepoint': DataSourceType.SHAREPOINT,
            'web.contents': DataSourceType.WEB,
            'odata.feed': DataSourceType.ODATA,
            'folder.files': DataSourceType.FOLDER,
            'csv.document': DataSourceType.CSV,
            'json.document': DataSourceType.JSON,
            'web.page': DataSourceType.API
        }

        for pattern, source_type in detection_map.items():
            if pattern in expr_lower:
                self.source_type = source_type
                return

        # If expression starts with "let" and has no Source =, it's calculated
        if expr_lower.strip().startswith('let') and 'source =' not in expr_lower:
            self.source_type = DataSourceType.CALCULATED

    def _count_steps(self):
        """Count transformation steps in M query"""
        # Each line with "=" is typically a step
        lines = self.expression.split('\n')
        self.step_count = sum(1 for line in lines if '=' in line and not line.strip().startswith('//'))

    @property
    def has_error_handling(self) -> bool:
        """Check if query has error handling"""
        expr_lower = self.expression.lower()
        return 'try' in expr_lower or 'error' in expr_lower

    @property
    def uses_custom_functions(self) -> bool:
        """Check if query uses custom functions"""
        # Custom functions typically start with "fx"
        return '()' in self.expression and '=>' in self.expression

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'table': self.table,
            'expression': self.expression,
            'source_type': self.source_type.value,
            'description': self.description,
            'expression_length': self.expression_length,
            'step_count': self.step_count,
            'has_error_handling': self.has_error_handling,
            'uses_custom_functions': self.uses_custom_functions
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"{self.name} ({self.source_type.value}, {self.step_count} steps)"
