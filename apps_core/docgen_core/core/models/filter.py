"""
Data models for Power BI filters (report, page, and visual-level filters)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class FilterType(Enum):
    """Types of Power BI filters"""
    CATEGORICAL = "Categorical"
    ADVANCED = "Advanced"
    TOPN = "TopN"
    BASIC = "Basic"
    RELATIVE_DATE = "RelativeDate"
    RELATIVE_TIME = "RelativeTime"
    INCLUDE_EXCLUDE = "IncludeExclude"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, filter_type: str) -> 'FilterType':
        """Parse filter type from string"""
        if not filter_type:
            return cls.UNKNOWN

        filter_type_upper = filter_type.upper()
        for ftype in cls:
            if ftype.value.upper() == filter_type_upper:
                return ftype
        return cls.UNKNOWN


@dataclass
class FilterField:
    """Represents a field being filtered"""
    table: str
    column: str
    aggregation: Optional[str] = None  # e.g., "Sum", "Average", etc.

    def __str__(self) -> str:
        """Get user-friendly string representation"""
        if self.aggregation:
            return f"{self.aggregation}({self.table}.{self.column})"
        return f"{self.table}.{self.column}"


@dataclass
class FilterExpression:
    """Represents filter logic/conditions"""
    filter_type: FilterType
    values: List[Any] = field(default_factory=list)  # Selected values
    conditions: List[Dict[str, Any]] = field(default_factory=list)  # Advanced conditions
    is_inverted: bool = False  # True = Exclude, False = Include
    raw_data: Optional[Dict[str, Any]] = None  # Store raw JSON for complex filters

    def to_readable_text(self) -> str:
        """Convert filter expression to human-readable text"""
        if self.filter_type == FilterType.CATEGORICAL:
            if self.values:
                value_count = len(self.values)
                if value_count <= 5:
                    value_list = ', '.join([str(v) for v in self.values])
                    action = "excluye" if self.is_inverted else "incluye"
                    return f"{action}: {value_list}"
                else:
                    action = "excluye" if self.is_inverted else "incluye"
                    return f"{action} {value_count} valores"
            return "Filtro categórico aplicado"

        elif self.filter_type == FilterType.ADVANCED:
            if self.conditions:
                # Try to parse advanced conditions
                cond_texts = []
                for cond in self.conditions[:3]:  # Show max 3 conditions
                    operator = cond.get('operator', '?')
                    value = cond.get('value', '?')
                    cond_texts.append(f"{operator} {value}")
                return f"Condiciones: {'; '.join(cond_texts)}"
            return "Filtro avanzado aplicado"

        elif self.filter_type == FilterType.TOPN:
            n = self.raw_data.get('itemCount', 'N') if self.raw_data else 'N'
            return f"Top {n} elementos"

        elif self.filter_type == FilterType.RELATIVE_DATE:
            return "Filtro de fecha relativa"

        elif self.filter_type == FilterType.BASIC:
            if self.values:
                return f"Valores: {', '.join([str(v) for v in self.values[:5]])}"
            return "Filtro básico"

        return "Filtro aplicado"


@dataclass
class Filter:
    """
    Represents a Power BI filter (report, page, or visual level)
    """
    name: str
    field: FilterField
    expression: FilterExpression
    scope: str  # "Report", "Page", or "Visual"
    how_created: str = "User"  # "User" or "System"
    is_locked: bool = False
    is_hidden: bool = False

    @property
    def expression_text(self) -> str:
        """Get human-readable expression text"""
        return self.expression.to_readable_text()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'field': str(self.field),
            'field_table': self.field.table,
            'field_column': self.field.column,
            'scope': self.scope,
            'filter_type': self.expression.filter_type.value,
            'expression': self.expression_text,
            'how_created': self.how_created,
            'is_locked': self.is_locked,
            'is_hidden': self.is_hidden
        }


@dataclass
class SlicerConfig:
    """Configuration for a slicer visual"""
    field: FilterField
    mode: str = "Basic"  # "Basic", "Dropdown", "List", "Between", "Before", "After"
    orientation: str = "Vertical"  # "Vertical" or "Horizontal"
    is_synced: bool = False
    sync_group: Optional[str] = None
    search_enabled: bool = False
    select_all_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'field': str(self.field),
            'mode': self.mode,
            'orientation': self.orientation,
            'is_synced': self.is_synced,
            'sync_group': self.sync_group,
            'search_enabled': self.search_enabled,
            'select_all_enabled': self.select_all_enabled
        }
