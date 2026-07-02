"""
Model validator - Validates overall data model integrity
"""

import logging
from typing import Set
from ..models.data_model import DataModel, Table, TableType
from ..models.relationship import Cardinality, CrossFilterDirection
from .validation_report import ValidationReport, ValidationIssue, ValidationSeverity


logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates Power BI data model integrity"""

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
        Run all validation checks

        Returns:
            ValidationReport with all findings
        """
        logger.info("Starting model validation...")

        # Run all checks
        self._check_orphaned_tables()
        self._check_missing_fact_tables()
        self._check_hidden_table_relationships()
        self._check_calculated_table_relationships()
        self._check_column_existence_in_relationships()
        self._check_self_referencing_relationships()

        # Calculate quality score
        self.report.quality_score = self._calculate_quality_score()

        logger.info(f"Validation complete. Quality score: {self.report.quality_score:.1f}")

        return self.report

    def _check_orphaned_tables(self):
        """Check for tables without any relationships"""
        for table in self.data_model.tables:
            # Skip calculated and measure-only tables
            if table.table_type in [TableType.CALCULATED, TableType.MEASURE_ONLY]:
                continue

            # Check if table has any relationships
            related_rels = self.data_model.get_table_relationships(table.name)

            if not related_rels:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="Orphaned Tables",
                    message=f"Table '{table.name}' has no relationships",
                    details=f"This table is not connected to any other table in the model.",
                    affected_objects=[table.name],
                    recommendation="Consider adding a relationship to connect this table, or hide it if it's not needed in the model."
                ))

    def _check_missing_fact_tables(self):
        """Check if model has at least one fact table"""
        fact_tables = self.data_model.get_fact_tables()

        if not fact_tables:
            self.report.add_issue(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="Model Structure",
                message="No fact tables detected",
                details="The model does not appear to have any fact tables (tables with primarily numeric columns).",
                affected_objects=[],
                recommendation="Verify that your data model includes fact tables with measures."
            ))

    def _check_hidden_table_relationships(self):
        """Check for relationships involving hidden tables"""
        for rel in self.data_model.relationships:
            from_table = self.data_model.get_table(rel.from_table)
            to_table = self.data_model.get_table(rel.to_table)

            if from_table and from_table.is_hidden:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="Hidden Tables",
                    message=f"Relationship from hidden table '{rel.from_table}'",
                    details=f"Table '{rel.from_table}' is hidden but has a relationship to '{rel.to_table}'.",
                    affected_objects=[rel.from_table, rel.to_table],
                    recommendation="This is common for bridge tables. Verify this is intentional."
                ))

            if to_table and to_table.is_hidden:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="Hidden Tables",
                    message=f"Relationship to hidden table '{rel.to_table}'",
                    details=f"Table '{rel.to_table}' is hidden but has a relationship from '{rel.from_table}'.",
                    affected_objects=[rel.from_table, rel.to_table],
                    recommendation="This is common for bridge tables. Verify this is intentional."
                ))

    def _check_calculated_table_relationships(self):
        """Check for relationships involving calculated tables"""
        for rel in self.data_model.relationships:
            from_table = self.data_model.get_table(rel.from_table)
            to_table = self.data_model.get_table(rel.to_table)

            if from_table and from_table.table_type == TableType.CALCULATED:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="Calculated Tables",
                    message=f"Relationship from calculated table '{rel.from_table}'",
                    details=f"Calculated table '{rel.from_table}' has a relationship to '{rel.to_table}'.",
                    affected_objects=[rel.from_table, rel.to_table],
                    recommendation="Ensure the calculated table logic is optimized for performance."
                ))

    def _check_column_existence_in_relationships(self):
        """Verify that columns referenced in relationships actually exist"""
        for rel in self.data_model.relationships:
            # Check from column
            from_table = self.data_model.get_table(rel.from_table)
            if from_table:
                from_column = from_table.get_column(rel.from_column)
                if not from_column:
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="Invalid Relationships",
                        message=f"Column '{rel.from_column}' not found in table '{rel.from_table}'",
                        details=f"Relationship references a non-existent column.",
                        affected_objects=[f"{rel.from_table}.{rel.from_column}"],
                        recommendation="Fix the relationship or add the missing column."
                    ))

            # Check to column
            to_table = self.data_model.get_table(rel.to_table)
            if to_table:
                to_column = to_table.get_column(rel.to_column)
                if not to_column:
                    self.report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="Invalid Relationships",
                        message=f"Column '{rel.to_column}' not found in table '{rel.to_table}'",
                        details=f"Relationship references a non-existent column.",
                        affected_objects=[f"{rel.to_table}.{rel.to_column}"],
                        recommendation="Fix the relationship or add the missing column."
                    ))

    def _check_self_referencing_relationships(self):
        """Check for relationships where a table relates to itself (parent-child)"""
        for rel in self.data_model.relationships:
            if rel.from_table == rel.to_table:
                self.report.add_issue(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="Self-Referencing Relationships",
                    message=f"Table '{rel.from_table}' has a self-referencing relationship",
                    details=f"Column '{rel.from_column}' relates to '{rel.to_column}' in the same table.",
                    affected_objects=[rel.from_table],
                    recommendation="This is common for parent-child hierarchies. Ensure PATH functions are used correctly."
                ))

    def _calculate_quality_score(self) -> float:
        """
        Calculate overall quality score (0-100)
        Based on number and severity of issues
        """
        score = 100.0

        # Deduct points based on severity
        score -= self.report.critical_count * 25  # -25 per critical
        score -= self.report.error_count * 10     # -10 per error
        score -= self.report.warning_count * 5    # -5 per warning
        score -= self.report.info_count * 1       # -1 per info

        # Ensure score doesn't go below 0
        return max(0.0, score)
