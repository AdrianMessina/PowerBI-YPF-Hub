"""
Data model for DAX measures
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class DAXComplexity(Enum):
    """DAX expression complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class DAXMeasure:
    """
    Represents a DAX measure in the model
    """
    name: str
    expression: str
    table: str
    description: Optional[str] = None
    display_folder: Optional[str] = None
    format_string: Optional[str] = None
    is_hidden: bool = False
    data_type: Optional[str] = None

    # Computed properties
    complexity: Optional[DAXComplexity] = field(default=None, init=False)
    expression_length: int = field(default=0, init=False)
    function_count: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Calculate derived properties"""
        self.expression_length = len(self.expression)
        self._calculate_complexity()
        self._analyze_functions()

    def _calculate_complexity(self):
        """Calculate complexity based on expression characteristics"""
        expr_upper = self.expression.upper()

        # Complex functions to look for
        complex_functions = [
            'CALCULATE', 'FILTER', 'SUMX', 'AVERAGEX', 'COUNTX',
            'MAXX', 'MINX', 'RANKX', 'TOPN', 'ADDCOLUMNS',
            'SUMMARIZE', 'CROSSFILTER', 'TREATAS', 'GENERATE'
        ]

        # Count occurrences
        complexity_score = sum(
            expr_upper.count(func) for func in complex_functions
        )

        # Count nested levels (rough estimate via parentheses depth)
        max_depth = self._calculate_nesting_depth(self.expression)

        # Determine complexity
        if complexity_score >= 5 or max_depth >= 5 or self.expression_length > 500:
            self.complexity = DAXComplexity.VERY_HIGH
        elif complexity_score >= 3 or max_depth >= 4 or self.expression_length > 300:
            self.complexity = DAXComplexity.HIGH
        elif complexity_score >= 1 or max_depth >= 3 or self.expression_length > 100:
            self.complexity = DAXComplexity.MEDIUM
        else:
            self.complexity = DAXComplexity.LOW

    def _calculate_nesting_depth(self, expr: str) -> int:
        """Calculate maximum nesting depth of parentheses"""
        max_depth = 0
        current_depth = 0

        for char in expr:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1

        return max_depth

    def _analyze_functions(self):
        """Analyze which DAX functions are used"""
        expr_upper = self.expression.upper()

        # Common DAX functions to track
        functions_to_track = [
            'CALCULATE', 'FILTER', 'ALL', 'ALLEXCEPT', 'SUMX', 'AVERAGEX',
            'COUNTX', 'MAXX', 'MINX', 'SUM', 'AVERAGE', 'COUNT', 'MAX', 'MIN',
            'IF', 'SWITCH', 'DIVIDE', 'RELATED', 'RELATEDTABLE', 'USERELATIONSHIP',
            'RANKX', 'TOPN', 'EARLIER', 'ADDCOLUMNS', 'SUMMARIZE', 'VALUES',
            'DISTINCT', 'CONCATENATEX', 'CROSSFILTER', 'TREATAS', 'GENERATE'
        ]

        self.function_count = {
            func: expr_upper.count(func)
            for func in functions_to_track
            if func in expr_upper
        }

    @property
    def has_time_intelligence(self) -> bool:
        """Check if measure uses time intelligence functions"""
        time_functions = [
            'DATESYTD', 'DATESBETWEEN', 'SAMEPERIODLASTYEAR', 'PARALLELPERIOD',
            'DATEADD', 'TOTALYTD', 'TOTALQTD', 'TOTALMTD', 'PREVIOUSMONTH',
            'PREVIOUSQUARTER', 'PREVIOUSYEAR', 'NEXTMONTH', 'NEXTQUARTER'
        ]
        expr_upper = self.expression.upper()
        return any(func in expr_upper for func in time_functions)

    @property
    def uses_context_transition(self) -> bool:
        """Check if measure uses context transition (CALCULATE/CALCULATETABLE)"""
        expr_upper = self.expression.upper()
        return 'CALCULATE' in expr_upper

    @property
    def uses_iterators(self) -> bool:
        """Check if measure uses iterator functions (X functions)"""
        iterator_functions = ['SUMX', 'AVERAGEX', 'COUNTX', 'MAXX', 'MINX', 'RANKX']
        expr_upper = self.expression.upper()
        return any(func in expr_upper for func in iterator_functions)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'table': self.table,
            'expression': self.expression,
            'description': self.description,
            'display_folder': self.display_folder,
            'format_string': self.format_string,
            'is_hidden': self.is_hidden,
            'data_type': self.data_type,
            'complexity': self.complexity.value if self.complexity else None,
            'expression_length': self.expression_length,
            'function_count': self.function_count,
            'has_time_intelligence': self.has_time_intelligence,
            'uses_context_transition': self.uses_context_transition,
            'uses_iterators': self.uses_iterators
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        complexity_str = self.complexity.value if self.complexity else "unknown"
        return f"{self.table}[{self.name}] ({complexity_str} complexity)"
