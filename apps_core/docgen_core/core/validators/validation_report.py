"""
Validation report data structures
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    details: str = ""
    affected_objects: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'details': self.details,
            'affected_objects': self.affected_objects,
            'recommendation': self.recommendation
        }


@dataclass
class ValidationReport:
    """Complete validation report"""
    issues: List[ValidationIssue] = field(default_factory=list)
    quality_score: float = 100.0

    # Issue counts by severity
    critical_count: int = field(default=0, init=False)
    error_count: int = field(default=0, init=False)
    warning_count: int = field(default=0, init=False)
    info_count: int = field(default=0, init=False)

    def __post_init__(self):
        """Calculate issue counts"""
        self.critical_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL)
        self.error_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        self.warning_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        self.info_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

    def add_issue(self, issue: ValidationIssue):
        """Add an issue to the report"""
        self.issues.append(issue)
        self.__post_init__()  # Recalculate counts

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return self.critical_count > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return self.error_count > 0

    @property
    def total_issues(self) -> int:
        """Total number of issues"""
        return len(self.issues)

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level"""
        return [issue for issue in self.issues if issue.severity == severity]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'quality_score': self.quality_score,
            'total_issues': self.total_issues,
            'critical_count': self.critical_count,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'has_critical_issues': self.has_critical_issues,
            'has_errors': self.has_errors,
            'issues': [issue.to_dict() for issue in self.issues]
        }
