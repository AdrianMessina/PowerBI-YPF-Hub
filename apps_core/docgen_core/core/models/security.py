"""
Data models for Power BI security (RLS, OLS)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class TablePermission:
    """
    Represents a table-level permission filter (RLS)
    """
    table: str
    filter_expression: str
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'table': self.table,
            'filter_expression': self.filter_expression,
            'description': self.description
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"{self.table}: {self.filter_expression[:50]}..."


@dataclass
class RLSRole:
    """
    Represents a Row Level Security (RLS) role
    """
    name: str
    description: Optional[str] = None
    table_permissions: List[TablePermission] = field(default_factory=list)
    members: List[str] = field(default_factory=list)  # User/group names

    @property
    def table_count(self) -> int:
        """Number of tables with filters"""
        return len(self.table_permissions)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'table_count': self.table_count,
            'table_permissions': [perm.to_dict() for perm in self.table_permissions],
            'members': self.members
        }

    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"Role: {self.name} ({self.table_count} table filters)"


@dataclass
class ObjectLevelSecurity:
    """
    Represents Object Level Security (OLS) - column/table visibility
    """
    object_type: str  # 'table' or 'column'
    object_name: str
    table: Optional[str] = None  # For columns
    roles_with_access: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'object_type': self.object_type,
            'object_name': self.object_name,
            'table': self.table,
            'roles_with_access': self.roles_with_access
        }


@dataclass
class SecurityConfiguration:
    """
    Complete security configuration for the model
    """
    rls_roles: List[RLSRole] = field(default_factory=list)
    ols_rules: List[ObjectLevelSecurity] = field(default_factory=list)

    @property
    def has_rls(self) -> bool:
        """Check if RLS is configured"""
        return len(self.rls_roles) > 0

    @property
    def has_ols(self) -> bool:
        """Check if OLS is configured"""
        return len(self.ols_rules) > 0

    @property
    def total_table_filters(self) -> int:
        """Total number of table filters across all roles"""
        return sum(role.table_count for role in self.rls_roles)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'has_rls': self.has_rls,
            'has_ols': self.has_ols,
            'rls_role_count': len(self.rls_roles),
            'ols_rule_count': len(self.ols_rules),
            'total_table_filters': self.total_table_filters,
            'rls_roles': [role.to_dict() for role in self.rls_roles],
            'ols_rules': [rule.to_dict() for rule in self.ols_rules]
        }
