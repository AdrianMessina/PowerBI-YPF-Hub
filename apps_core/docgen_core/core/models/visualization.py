"""
Data models for Power BI visualizations (pages, visuals)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VisualType(Enum):
    """Types of Power BI visuals"""
    BAR_CHART = "barChart"
    COLUMN_CHART = "columnChart"
    LINE_CHART = "lineChart"
    PIE_CHART = "pieChart"
    DONUT_CHART = "donutChart"
    SCATTER_CHART = "scatterChart"
    MAP = "map"
    FILLED_MAP = "filledMap"
    TABLE = "table"
    MATRIX = "matrix"
    CARD = "card"
    MULTI_ROW_CARD = "multiRowCard"
    KPI = "kpi"
    SLICER = "slicer"
    GAUGE = "gauge"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"
    TREEMAP = "treemap"
    RIBBON = "ribbon"
    CUSTOM = "custom"
    OTHER = "other"

    @classmethod
    def from_string(cls, visual_type: str) -> 'VisualType':
        """Parse visual type from string"""
        visual_type_lower = visual_type.lower()
        for vtype in cls:
            if vtype.value.lower() in visual_type_lower:
                return vtype
        return cls.OTHER


@dataclass
class Visual:
    """
    Represents a single visual on a page
    """
    name: str
    visual_type: VisualType
    page: str
    title: Optional[str] = None
    position: Optional[Dict[str, float]] = None  # x, y, width, height
    filters: List[Any] = field(default_factory=list)  # List of Filter objects
    fields_used: List[str] = field(default_factory=list)
    is_hidden: bool = False
    is_slicer: bool = False
    slicer_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Normalize visual type"""
        if isinstance(self.visual_type, str):
            self.visual_type = VisualType.from_string(self.visual_type)

    @property
    def is_custom_visual(self) -> bool:
        """Check if this is a custom visual"""
        return self.visual_type == VisualType.CUSTOM

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'visual_type': self.visual_type.value,
            'page': self.page,
            'title': self.title,
            'position': self.position,
            'filter_count': len(self.filters),
            'field_count': len(self.fields_used),
            'is_hidden': self.is_hidden,
            'is_custom_visual': self.is_custom_visual
        }


@dataclass
class Bookmark:
    """
    Represents a bookmark in the report
    """
    name: str
    display_name: str
    page: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'page': self.page,
            'description': self.description
        }


@dataclass
class Page:
    """
    Represents a page in the Power BI report
    """
    name: str
    display_name: str
    visuals: List[Visual] = field(default_factory=list)
    filters: List[Any] = field(default_factory=list)  # List of Filter objects
    is_hidden: bool = False
    width: Optional[int] = None
    height: Optional[int] = None

    # Computed properties
    visual_count: int = field(default=0, init=False)
    visual_type_counts: Dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.visual_count = len(self.visuals)
        self._count_visual_types()

    def _count_visual_types(self):
        """Count visuals by type"""
        self.visual_type_counts = {}
        for visual in self.visuals:
            vtype = visual.visual_type.value
            self.visual_type_counts[vtype] = self.visual_type_counts.get(vtype, 0) + 1

    @property
    def has_custom_visuals(self) -> bool:
        """Check if page has custom visuals"""
        return any(v.is_custom_visual for v in self.visuals)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'visual_count': self.visual_count,
            'filter_count': len(self.filters),
            'is_hidden': self.is_hidden,
            'has_custom_visuals': self.has_custom_visuals,
            'visual_type_counts': self.visual_type_counts,
            'visuals': [v.to_dict() for v in self.visuals],
            'width': self.width,
            'height': self.height
        }


@dataclass
class ReportLayout:
    """
    Represents the complete report layout (pages, bookmarks, etc.)
    """
    pages: List[Page] = field(default_factory=list)
    bookmarks: List[Bookmark] = field(default_factory=list)
    report_filters: List[Any] = field(default_factory=list)  # List of Filter objects

    # Computed properties
    page_count: int = field(default=0, init=False)
    total_visual_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.page_count = len(self.pages)
        self.total_visual_count = sum(page.visual_count for page in self.pages)

    def get_page(self, page_name: str) -> Optional[Page]:
        """Get page by name"""
        for page in self.pages:
            if page.name == page_name or page.display_name == page_name:
                return page
        return None

    @property
    def pages_with_custom_visuals(self) -> List[Page]:
        """Get pages that have custom visuals"""
        return [page for page in self.pages if page.has_custom_visuals]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'page_count': self.page_count,
            'total_visual_count': self.total_visual_count,
            'bookmark_count': len(self.bookmarks),
            'pages': [page.to_dict() for page in self.pages],
            'bookmarks': [bm.to_dict() for bm in self.bookmarks],
            'pages_with_custom_visuals_count': len(self.pages_with_custom_visuals)
        }
