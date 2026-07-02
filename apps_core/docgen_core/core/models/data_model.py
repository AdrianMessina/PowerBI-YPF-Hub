"""
Data models for Power BI tables, columns, and the overall data model
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ColumnDataType(Enum):
    """Column data types in Power BI"""
    STRING = "string"
    INT64 = "int64"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DECIMAL = "decimal"
    UNKNOWN = "unknown"


class TableType(Enum):
    """Types of tables in Power BI"""
    REGULAR = "regular"          # Regular imported table
    CALCULATED = "calculated"    # Calculated table (DAX)
    CALENDAR = "calendar"        # Date/Calendar table
    MEASURE_ONLY = "measure_only"  # Table with only measures


@dataclass
class Column:
    """
    Represents a column in a Power BI table
    """
    name: str
    table: str
    data_type: ColumnDataType = ColumnDataType.UNKNOWN
    is_hidden: bool = False
    is_key: bool = False
    is_calculated: bool = False
    expression: Optional[str] = None
    description: Optional[str] = None
    display_folder: Optional[str] = None
    format_string: Optional[str] = None
    source_column: Optional[str] = None

    def __post_init__(self):
        """Normalize data type"""
        if isinstance(self.data_type, str):
            try:
                self.data_type = ColumnDataType[self.data_type.upper()]
            except KeyError:
                self.data_type = ColumnDataType.UNKNOWN

    @property
    def full_name(self) -> str:
        """Get fully qualified column name"""
        return f"{self.table}[{self.name}]"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'table': self.table,
            'data_type': self.data_type.value,
            'is_hidden': self.is_hidden,
            'is_key': self.is_key,
            'is_calculated': self.is_calculated,
            'expression': self.expression,
            'description': self.description,
            'display_folder': self.display_folder,
            'format_string': self.format_string,
            'source_column': self.source_column,
            'full_name': self.full_name
        }


@dataclass
class Hierarchy:
    """
    Represents a hierarchy in a table
    """
    name: str
    table: str
    levels: List[str] = field(default_factory=list)
    is_hidden: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'table': self.table,
            'levels': self.levels,
            'is_hidden': self.is_hidden
        }


@dataclass
class Table:
    """
    Represents a table in the Power BI data model
    """
    name: str
    columns: List[Column] = field(default_factory=list)
    table_type: TableType = TableType.REGULAR
    is_hidden: bool = False
    description: Optional[str] = None
    source_expression: Optional[str] = None  # M query or DAX for calculated tables
    hierarchies: List[Hierarchy] = field(default_factory=list)

    # Computed properties
    column_count: int = field(default=0, init=False)
    calculated_column_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.column_count = len(self.columns)
        self.calculated_column_count = sum(
            1 for col in self.columns if col.is_calculated
        )

    @property
    def is_fact_table(self) -> bool:
        """
        Heuristic to determine if this is a fact table
        (has many numeric columns, typically larger)
        """
        if self.table_type == TableType.CALCULATED:
            return False

        numeric_types = {ColumnDataType.INT64, ColumnDataType.DOUBLE, ColumnDataType.DECIMAL}
        numeric_count = sum(
            1 for col in self.columns
            if col.data_type in numeric_types
        )

        # If more than 50% columns are numeric, likely a fact table
        return numeric_count > len(self.columns) * 0.5 if self.columns else False

    @property
    def is_dimension_table(self) -> bool:
        """
        Heuristic to determine if this is a dimension table
        """
        return not self.is_fact_table and self.table_type == TableType.REGULAR

    def get_column(self, column_name: str) -> Optional[Column]:
        """Get column by name"""
        for col in self.columns:
            if col.name == column_name:
                return col
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'table_type': self.table_type.value,
            'is_hidden': self.is_hidden,
            'description': self.description,
            'column_count': self.column_count,
            'calculated_column_count': self.calculated_column_count,
            'columns': [col.to_dict() for col in self.columns],
            'hierarchies': [h.to_dict() for h in self.hierarchies],
            'is_fact_table': self.is_fact_table,
            'is_dimension_table': self.is_dimension_table,
            'source_expression': self.source_expression[:200] if self.source_expression else None
        }


@dataclass
class DataModel:
    """
    Represents the complete Power BI data model
    """
    tables: List[Table] = field(default_factory=list)
    relationships: List[Any] = field(default_factory=list)  # List[Relationship] - avoid circular import
    measures: List[Any] = field(default_factory=list)  # List[DAXMeasure]

    # Computed properties
    table_count: int = field(default=0, init=False)
    relationship_count: int = field(default=0, init=False)
    measure_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.table_count = len(self.tables)
        self.relationship_count = len(self.relationships)
        self.measure_count = len(self.measures)

    def get_table(self, table_name: str) -> Optional[Table]:
        """Get table by name"""
        for table in self.tables:
            if table.name == table_name:
                return table
        return None

    def get_table_relationships(self, table_name: str) -> List[Any]:
        """Get all relationships involving a table"""
        return [
            rel for rel in self.relationships
            if rel.from_table == table_name or rel.to_table == table_name
        ]

    def get_bidirectional_relationships(self) -> List[Any]:
        """Get all bidirectional relationships"""
        return [rel for rel in self.relationships if rel.is_bidirectional]

    def get_many_to_many_relationships(self) -> List[Any]:
        """Get all many-to-many relationships"""
        return [rel for rel in self.relationships if rel.is_many_to_many]

    def get_fact_tables(self) -> List[Table]:
        """Get all fact tables"""
        return [table for table in self.tables if table.is_fact_table]

    def get_dimension_tables(self) -> List[Table]:
        """Get all dimension tables"""
        return [table for table in self.tables if table.is_dimension_table]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'table_count': self.table_count,
            'relationship_count': self.relationship_count,
            'measure_count': self.measure_count,
            'tables': [table.to_dict() for table in self.tables],
            'relationships': [rel.to_dict() for rel in self.relationships],
            'measures': [measure.to_dict() for measure in self.measures],
            'fact_table_count': len(self.get_fact_tables()),
            'dimension_table_count': len(self.get_dimension_tables()),
            'bidirectional_relationship_count': len(self.get_bidirectional_relationships()),
            'many_to_many_relationship_count': len(self.get_many_to_many_relationships())
        }
