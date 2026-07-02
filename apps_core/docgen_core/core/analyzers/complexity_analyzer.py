"""
DAX complexity analyzer - Analyzes DAX measure complexity and patterns
"""

import re
import logging
from typing import List, Dict, Set
from ..models.dax_measure import DAXMeasure, DAXComplexity
from ..validators.validation_report import ValidationReport, ValidationIssue, ValidationSeverity


logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """Analyzes DAX measure complexity"""

    # DAX patterns for detection
    TIME_INTELLIGENCE_FUNCTIONS = {
        'TOTALYTD', 'TOTALQTD', 'TOTALMTD',
        'DATESYTD', 'DATESQTD', 'DATESMTD',
        'DATEADD', 'DATESBETWEEN', 'DATESINPERIOD',
        'SAMEPERIODLASTYEAR', 'PARALLELPERIOD',
        'PREVIOUSMONTH', 'PREVIOUSQUARTER', 'PREVIOUSYEAR',
        'NEXTMONTH', 'NEXTQUARTER', 'NEXTYEAR',
        'STARTOFMONTH', 'STARTOFQUARTER', 'STARTOFYEAR',
        'ENDOFMONTH', 'ENDOFQUARTER', 'ENDOFYEAR'
    }

    ITERATOR_FUNCTIONS = {
        'SUMX', 'AVERAGEX', 'MINX', 'MAXX', 'COUNTX',
        'FILTER', 'ADDCOLUMNS', 'SELECTCOLUMNS',
        'GROUPBY', 'SUMMARIZE', 'SUMMARIZECOLUMNS',
        'GENERATEALL', 'GENERATE', 'CROSSJOIN'
    }

    FILTER_FUNCTIONS = {
        'CALCULATE', 'CALCULATETABLE', 'FILTER',
        'ALL', 'ALLEXCEPT', 'ALLSELECTED', 'ALLNOBLANKROW',
        'REMOVEFILTERS', 'KEEPFILTERS', 'USERELATIONSHIP'
    }

    COMPLEX_PATTERNS = {
        'nested_calculate': r'CALCULATE\s*\([^)]*CALCULATE',
        'nested_filter': r'FILTER\s*\([^)]*FILTER',
        'nested_iterator': r'(SUMX|AVERAGEX|COUNTX)\s*\([^)]*X\s*\(',
        'var_usage': r'\bVAR\b',
        'return_usage': r'\bRETURN\b'
    }

    def __init__(self, measures: List[DAXMeasure]):
        """
        Initialize analyzer

        Args:
            measures: List of DAXMeasure objects to analyze
        """
        self.measures = measures
        self.report = ValidationReport()

    def analyze_all(self) -> ValidationReport:
        """
        Analyze all measures

        Returns:
            ValidationReport with complexity findings
        """
        logger.info(f"Analyzing {len(self.measures)} DAX measures...")

        for measure in self.measures:
            self._analyze_measure(measure)

        logger.info(f"DAX analysis complete. Found {self.report.total_issues} complexity issues")

        return self.report

    def _analyze_measure(self, measure: DAXMeasure):
        """Analyze a single measure"""
        expression = measure.expression.upper() if measure.expression else ""

        # Check for very high complexity
        if measure.complexity == DAXComplexity.VERY_HIGH:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="High Complexity",
                message=f"Very complex measure: '{measure.name}'",
                details=f"This measure has very high complexity. Expression length: {measure.expression_length} characters.",
                affected_objects=[f"{measure.table}.{measure.name}"],
                recommendation="Consider breaking this into multiple simpler measures or using variables to improve readability."
            ))

        # Check for nested CALCULATE
        if re.search(self.COMPLEX_PATTERNS['nested_calculate'], expression, re.IGNORECASE):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="Complex Patterns",
                message=f"Nested CALCULATE detected: '{measure.name}'",
                details="This measure contains nested CALCULATE functions.",
                affected_objects=[f"{measure.table}.{measure.name}"],
                recommendation="Nested CALCULATE can be difficult to understand. Consider refactoring using variables."
            ))

        # Check for nested iterators
        if re.search(self.COMPLEX_PATTERNS['nested_iterator'], expression, re.IGNORECASE):
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="Performance",
                message=f"Nested iterator functions: '{measure.name}'",
                details="This measure contains nested iterator functions (e.g., SUMX within SUMX).",
                affected_objects=[f"{measure.table}.{measure.name}"],
                recommendation="Nested iterators can cause performance issues. Consider materializing intermediate results or restructuring the logic."
            ))

        # Check for very long expressions without VAR
        has_var = bool(re.search(self.COMPLEX_PATTERNS['var_usage'], expression, re.IGNORECASE))
        if measure.expression_length > 500 and not has_var:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="Code Quality",
                message=f"Long expression without variables: '{measure.name}'",
                details=f"This measure is {measure.expression_length} characters long but doesn't use VAR/RETURN pattern.",
                affected_objects=[f"{measure.table}.{measure.name}"],
                recommendation="Use VAR to break down complex expressions and improve readability."
            ))

        # Check for measures with many iterator functions
        iterator_count = sum(1 for func in self.ITERATOR_FUNCTIONS if func in expression)
        if iterator_count >= 3:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="Performance",
                message=f"Multiple iterator functions: '{measure.name}' ({iterator_count} iterators)",
                details=f"This measure uses {iterator_count} different iterator functions.",
                affected_objects=[f"{measure.table}.{measure.name}"],
                recommendation="Multiple iterators can impact performance. Verify query performance and consider optimization."
            ))

    def get_complexity_summary(self) -> Dict[str, int]:
        """
        Get summary of measure complexity distribution

        Returns:
            Dictionary with counts per complexity level
        """
        summary = {
            'low': 0,
            'medium': 0,
            'high': 0,
            'very_high': 0
        }

        for measure in self.measures:
            if measure.complexity == DAXComplexity.LOW:
                summary['low'] += 1
            elif measure.complexity == DAXComplexity.MEDIUM:
                summary['medium'] += 1
            elif measure.complexity == DAXComplexity.HIGH:
                summary['high'] += 1
            elif measure.complexity == DAXComplexity.VERY_HIGH:
                summary['very_high'] += 1

        return summary

    def get_time_intelligence_measures(self) -> List[DAXMeasure]:
        """Get all measures using time intelligence"""
        return [m for m in self.measures if m.has_time_intelligence]

    def get_iterator_measures(self) -> List[DAXMeasure]:
        """Get all measures using iterator functions"""
        return [m for m in self.measures if m.uses_iterators]

    def get_most_complex_measures(self, top_n: int = 10) -> List[DAXMeasure]:
        """
        Get the most complex measures

        Args:
            top_n: Number of top complex measures to return

        Returns:
            List of most complex measures
        """
        sorted_measures = sorted(
            self.measures,
            key=lambda m: (
                m.complexity == DAXComplexity.VERY_HIGH,
                m.complexity == DAXComplexity.HIGH,
                m.expression_length
            ),
            reverse=True
        )

        return sorted_measures[:top_n]
