"""
Relationship validator - Validates relationship configuration and detects issues
"""

import logging
from typing import List, Set, Dict, Tuple
from collections import defaultdict
from ..models.data_model import DataModel
from ..models.relationship import Relationship, Cardinality, CrossFilterDirection
from .validation_report import ValidationReport, ValidationIssue, ValidationSeverity


logger = logging.getLogger(__name__)


class RelationshipValidator:
    """Validates Power BI relationships for common issues"""

    def __init__(self, data_model: DataModel):
        """
        Initialize validator

        Args:
            data_model: DataModel to validate
        """
        self.data_model = data_model
        self.report = ValidationReport()

    def validate_all(self) -> ValidationReport:
        """
        Run all relationship validation checks

        Returns:
            ValidationReport with all findings
        """
        logger.info("Starting relationship validation...")

        # Run all checks
        self._check_circular_dependencies()
        self._check_bidirectional_chains()
        self._check_many_to_many_relationships()
        self._check_inactive_relationships()
        self._check_duplicate_relationships()
        self._check_ambiguous_paths()

        # Calculate quality score
        self.report.quality_score = self._calculate_quality_score()

        logger.info(f"Relationship validation complete. Quality score: {self.report.quality_score:.1f}")

        return self.report

    def _check_circular_dependencies(self):
        """Detect circular relationship chains"""
        # Build adjacency list
        graph = defaultdict(list)
        for rel in self.data_model.relationships:
            if rel.is_active:
                graph[rel.from_table].append(rel.to_table)

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: List[str]) -> bool:
            """DFS to detect cycle"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle_path = path[cycle_start:] + [neighbor]
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="Circular Dependencies",
                        message=f"Circular relationship chain detected",
                        details=f"Cycle: {' → '.join(cycle_path)}",
                        affected_objects=cycle_path,
                        recommendation="Break the cycle by deactivating one relationship or restructuring the model."
                    ))
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        # Check all nodes
        for table in self.data_model.tables:
            if table.name not in visited:
                has_cycle(table.name, [])

    def _check_bidirectional_chains(self):
        """Check for chains of bidirectional relationships (performance issue)"""
        # Build bidirectional graph
        bi_graph = defaultdict(list)
        for rel in self.data_model.relationships:
            if rel.is_bidirectional and rel.is_active:
                bi_graph[rel.from_table].append(rel.to_table)
                bi_graph[rel.to_table].append(rel.from_table)  # Bidirectional

        # Find connected components with more than 2 tables
        visited = set()

        def dfs_component(node: str, component: Set[str]):
            """DFS to find connected component"""
            visited.add(node)
            component.add(node)
            for neighbor in bi_graph[node]:
                if neighbor not in visited:
                    dfs_component(neighbor, component)

        components = []
        for table in bi_graph.keys():
            if table not in visited:
                component = set()
                dfs_component(table, component)
                if len(component) > 2:
                    components.append(component)

        # Report chains
        for component in components:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="Bidirectional Chains",
                message=f"Chain of bidirectional relationships detected ({len(component)} tables)",
                details=f"Tables: {', '.join(sorted(component))}",
                affected_objects=list(component),
                recommendation="Bidirectional chains can cause performance issues and ambiguous filter context. Consider using single-direction relationships where possible."
            ))

    def _check_many_to_many_relationships(self):
        """Check for many-to-many relationships"""
        for rel in self.data_model.relationships:
            if rel.is_many_to_many:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="Many-to-Many Relationships",
                    message=f"Many-to-many relationship: {rel.from_table} ↔ {rel.to_table}",
                    details=f"Relationship between '{rel.from_table}.{rel.from_column}' and '{rel.to_table}.{rel.to_column}'",
                    affected_objects=[rel.from_table, rel.to_table],
                    recommendation="Many-to-many relationships can impact performance. Consider using a bridge table for better control and performance."
                ))

    def _check_inactive_relationships(self):
        """Check for inactive relationships"""
        inactive = [rel for rel in self.data_model.relationships if not rel.is_active]

        if inactive:
            for rel in inactive:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="Inactive Relationships",
                    message=f"Inactive relationship: {rel.from_table} → {rel.to_table}",
                    details=f"Relationship between '{rel.from_table}.{rel.from_column}' and '{rel.to_table}.{rel.to_column}' is inactive",
                    affected_objects=[rel.from_table, rel.to_table],
                    recommendation="Inactive relationships must be activated using USERELATIONSHIP in DAX. Verify this is intentional."
                ))

    def _check_duplicate_relationships(self):
        """Check for duplicate relationships between same tables"""
        # Group relationships by table pair
        table_pairs = defaultdict(list)
        for rel in self.data_model.relationships:
            # Sort to treat (A,B) same as (B,A)
            pair = tuple(sorted([rel.from_table, rel.to_table]))
            table_pairs[pair].append(rel)

        # Check for multiple relationships between same tables
        for (table1, table2), rels in table_pairs.items():
            if len(rels) > 1:
                active_count = sum(1 for rel in rels if rel.is_active)

                if active_count > 1:
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="Duplicate Relationships",
                        message=f"Multiple active relationships between {table1} and {table2}",
                        details=f"Found {active_count} active relationships out of {len(rels)} total",
                        affected_objects=[table1, table2],
                        recommendation="Multiple active relationships between tables can cause ambiguous paths. Deactivate unnecessary relationships."
                    ))
                else:
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="Duplicate Relationships",
                        message=f"Multiple relationships between {table1} and {table2}",
                        details=f"Found {len(rels)} relationships (only {active_count} active)",
                        affected_objects=[table1, table2],
                        recommendation="This is common for role-playing dimensions. Use USERELATIONSHIP to activate as needed."
                    ))

    def _check_ambiguous_paths(self):
        """Check for ambiguous relationship paths (multiple paths between tables)"""
        # Build graph of active relationships
        graph = defaultdict(list)
        for rel in self.data_model.relationships:
            if rel.is_active:
                graph[rel.from_table].append((rel.to_table, rel))
                if rel.is_bidirectional:
                    graph[rel.to_table].append((rel.from_table, rel))

        # Find all table pairs with multiple paths
        checked_pairs = set()

        # Convert to list to avoid "dictionary changed size during iteration" error
        for start_table in list(graph.keys()):
            # BFS to find all reachable tables and count paths
            from collections import deque
            queue = deque([(start_table, [])])  # (node, path)
            paths_to_target = defaultdict(list)

            while queue:
                current, path = queue.popleft()

                for neighbor, rel in graph[current]:
                    new_path = path + [rel]

                    # Record path to neighbor
                    pair = tuple(sorted([start_table, neighbor]))
                    if pair not in checked_pairs:
                        paths_to_target[neighbor].append(new_path)

                    # Continue BFS (limit depth to avoid infinite loops)
                    if len(new_path) < 4:
                        queue.append((neighbor, new_path))

            # Check for multiple paths
            for target, paths in paths_to_target.items():
                if len(paths) > 1:
                    pair = tuple(sorted([start_table, target]))
                    if pair not in checked_pairs:
                        checked_pairs.add(pair)

                        path_descriptions = []
                        for p in paths[:3]:  # Show max 3 paths
                            path_str = start_table
                            for r in p:
                                arrow = "⟷" if r.is_bidirectional else "→"
                                path_str += f" {arrow} {r.to_table if r.from_table in path_str else r.from_table}"
                            path_descriptions.append(path_str)

                        self.report.add_issue(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="Ambiguous Paths",
                            message=f"Multiple paths between {start_table} and {target}",
                            details=f"Found {len(paths)} different paths. Examples:\n" + "\n".join(path_descriptions),
                            affected_objects=[start_table, target],
                            recommendation="Ambiguous paths can cause unexpected filter behavior. Consider deactivating some relationships or using USERELATIONSHIP explicitly."
                        ))

    def _calculate_quality_score(self) -> float:
        """Calculate relationship quality score"""
        score = 100.0

        # Deduct points based on severity
        score -= self.report.critical_count * 25
        score -= self.report.error_count * 10
        score -= self.report.warning_count * 5
        score -= self.report.info_count * 1

        return max(0.0, score)
