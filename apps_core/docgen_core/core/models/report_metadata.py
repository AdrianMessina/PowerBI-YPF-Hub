"""
Top-level report metadata model
Aggregates all components: data model, layout, security, queries
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

from .data_model import DataModel
from .visualization import ReportLayout
from .security import SecurityConfiguration
from .power_query import PowerQuery


@dataclass
class ReportMetadata:
    """
    Complete metadata for a Power BI report
    This is the main container returned by parsers
    """
    # Basic info
    report_name: str
    report_path: str
    report_type: str  # 'pbix' or 'pbip'

    # Main components
    data_model: DataModel = field(default_factory=DataModel)
    layout: ReportLayout = field(default_factory=ReportLayout)
    security: SecurityConfiguration = field(default_factory=SecurityConfiguration)
    queries: list = field(default_factory=list)  # List[PowerQuery]

    # Metadata
    extraction_date: Optional[datetime] = None
    report_id: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None

    # Additional properties
    custom_visuals: list = field(default_factory=list)  # Custom visual info
    parameters: Dict[str, Any] = field(default_factory=dict)  # Report parameters
    bookmarks: list = field(default_factory=list)

    def __post_init__(self):
        """Set extraction date if not provided"""
        if self.extraction_date is None:
            self.extraction_date = datetime.now()

    @property
    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            'report_name': self.report_name,
            'report_type': self.report_type,
            'table_count': self.data_model.table_count,
            'relationship_count': self.data_model.relationship_count,
            'measure_count': self.data_model.measure_count,
            'page_count': self.layout.page_count,
            'visual_count': self.layout.total_visual_count,
            'query_count': len(self.queries),
            'has_rls': self.security.has_rls,
            'has_ols': self.security.has_ols,
            'custom_visual_count': len(self.custom_visuals),
            'extraction_date': self.extraction_date.isoformat() if self.extraction_date else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete metadata to dictionary"""
        return {
            'metadata': {
                'report_name': self.report_name,
                'report_path': self.report_path,
                'report_type': self.report_type,
                'report_id': self.report_id,
                'display_name': self.display_name,
                'description': self.description,
                'author': self.author,
                'created_date': self.created_date.isoformat() if self.created_date else None,
                'modified_date': self.modified_date.isoformat() if self.modified_date else None,
                'extraction_date': self.extraction_date.isoformat() if self.extraction_date else None
            },
            'summary': self.summary_stats,
            'data_model': self.data_model.to_dict(),
            'layout': self.layout.to_dict(),
            'security': self.security.to_dict(),
            'queries': [q.to_dict() for q in self.queries],
            'custom_visuals': self.custom_visuals,
            'parameters': self.parameters
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        return (
            f"Power BI Report: {self.report_name}\n"
            f"Type: {self.report_type}\n"
            f"Tables: {self.data_model.table_count}, "
            f"Relationships: {self.data_model.relationship_count}, "
            f"Measures: {self.data_model.measure_count}\n"
            f"Pages: {self.layout.page_count}, "
            f"Visuals: {self.layout.total_visual_count}\n"
            f"RLS: {'Yes' if self.security.has_rls else 'No'}"
        )
