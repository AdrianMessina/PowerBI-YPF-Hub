"""
PBIX Parser - Legacy Power BI Format
Parses .pbix files (ZIP with JSON and binary data)
"""

import zipfile
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .base_parser import BasePowerBIParser
from .format_detector import FormatDetector, PowerBIFormat
from ..models import (
    ReportMetadata, DataModel, Table, Column, ColumnDataType, TableType,
    Relationship, Cardinality, CrossFilterDirection,
    DAXMeasure, PowerQuery, DataSourceType,
    RLSRole, TablePermission, SecurityConfiguration,
    ReportLayout, Page, Visual, VisualType, Bookmark
)


class PBIXParser(BasePowerBIParser):
    """Parser for PBIX (Power BI Desktop) format"""

    def __init__(self, pbix_path: str):
        """
        Initialize PBIX parser

        Args:
            pbix_path: Path to .pbix file
        """
        super().__init__(pbix_path)

    def supports_format(self) -> bool:
        """Check if this parser supports the file format"""
        try:
            format_type = FormatDetector.detect(self.file_path)
            return format_type == PowerBIFormat.PBIX
        except:
            return False

    def validate_file(self) -> bool:
        """Validate PBIX file structure"""
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                # Check for required files
                if 'DataModel' not in file_list:
                    raise ValueError("DataModel file not found in PBIX")
                return True
        except zipfile.BadZipFile:
            raise ValueError(f"{self.file_path} is not a valid ZIP/PBIX file")

    def parse(self) -> ReportMetadata:
        """
        Parse PBIX file and extract all metadata

        Returns:
            ReportMetadata with complete information
        """
        self._log_info(f"Parsing PBIX file: {self.file_path.name}")

        # Initialize metadata
        metadata = ReportMetadata(
            report_name=self.get_report_name(),
            report_path=str(self.file_path),
            report_type='pbix'
        )

        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                # Parse data model
                self._log_info("Parsing data model...")
                metadata.data_model = self._parse_data_model(zip_ref)

                # Parse report layout
                self._log_info("Parsing report layout...")
                metadata.layout = self._parse_layout(zip_ref)

                # Parse security
                metadata.security = self._parse_security(zip_ref)

            self._log_success(f"PBIX parsing complete: {len(metadata.data_model.tables)} tables, "
                             f"{len(metadata.data_model.relationships)} relationships, "
                             f"{len(metadata.data_model.measures)} measures")

        except Exception as e:
            self._log_error(f"Error parsing PBIX: {str(e)}")
            raise

        return metadata

    def _parse_data_model(self, zip_ref: zipfile.ZipFile) -> DataModel:
        """Parse DataModel from PBIX"""
        try:
            # Read DataModel file
            self._log_info("Reading DataModel from PBIX...")
            datamodel_bytes = zip_ref.read('DataModel')
            datamodel_str = datamodel_bytes.decode('utf-16-le', errors='ignore')

            self._log_info(f"DataModel size: {len(datamodel_str)} chars")

            # Fallback: Extract using regex patterns (more reliable for PBIX)
            self._log_info("Using regex extraction for PBIX...")
            return self._parse_model_regex(datamodel_str)

        except KeyError:
            self._log_error("DataModel file not found in PBIX")
            return DataModel()
        except Exception as e:
            self._log_error(f"Error parsing data model: {e}")
            import traceback
            self._log_error(traceback.format_exc())
            return DataModel()

    def _parse_model_json(self, model_data: dict) -> DataModel:
        """Parse model from JSON structure"""
        tables = []
        all_measures = []

        # Parse tables
        for table_data in model_data.get('tables', []):
            columns = []

            # Parse columns
            for col_data in table_data.get('columns', []):
                column = Column(
                    name=col_data.get('name', 'Unknown'),
                    table=table_data.get('name', 'Unknown'),
                    data_type=self._map_data_type(col_data.get('dataType')),
                    is_calculated='expression' in col_data or 'type' in col_data and col_data['type'] == 'calculated',
                    expression=col_data.get('expression'),
                    is_hidden=col_data.get('isHidden', False),
                    source_column=col_data.get('sourceColumn')
                )
                columns.append(column)

            # Determine table type
            table_type = TableType.REGULAR
            for partition in table_data.get('partitions', []):
                source = partition.get('source', {})
                if source.get('type') == 'calculated' or 'expression' in source:
                    table_type = TableType.CALCULATED
                    break

            table = Table(
                name=table_data.get('name', 'Unknown'),
                columns=columns,
                table_type=table_type,
                is_hidden=table_data.get('isHidden', False),
                description=table_data.get('description')
            )
            tables.append(table)

            # Parse measures
            for measure_data in table_data.get('measures', []):
                # Extract expression (can be string or array)
                expression = measure_data.get('expression', '')
                if isinstance(expression, list):
                    expression = ''.join(expression)

                measure = DAXMeasure(
                    name=measure_data.get('name', 'Unknown'),
                    expression=expression,
                    table=table_data.get('name', 'Unknown'),
                    description=measure_data.get('description'),
                    format_string=measure_data.get('formatString'),
                    is_hidden=measure_data.get('isHidden', False),
                    display_folder=measure_data.get('displayFolder')
                )
                all_measures.append(measure)

        # Parse relationships
        relationships = []
        for rel_data in model_data.get('relationships', []):
            relationship = Relationship(
                from_table=rel_data.get('fromTable', ''),
                from_column=rel_data.get('fromColumn', ''),
                to_table=rel_data.get('toTable', ''),
                to_column=rel_data.get('toColumn', ''),
                cardinality=Cardinality.from_parts(
                    rel_data.get('fromCardinality', 'many'),
                    rel_data.get('toCardinality', 'one')
                ),
                cross_filter_direction=CrossFilterDirection.from_behavior(
                    rel_data.get('crossFilteringBehavior', 'oneDirection')
                ),
                is_active=rel_data.get('isActive', True)
            )
            relationships.append(relationship)

        return DataModel(tables=tables, relationships=relationships, measures=all_measures)

    def _parse_model_regex(self, datamodel_str: str) -> DataModel:
        """Parse model using regex patterns (fallback)"""
        tables = []
        all_measures = []
        relationships = []

        self._log_info("Extracting tables with regex...")

        # Extract table names - more flexible patterns
        table_patterns = [
            r'"Name"\s*:\s*"([^"]+)"[^}]*"(?:Table|table)"',  # JSON style
            r'Name="([^"]+)"[^>]*(?:Table|table)',  # XML style
        ]

        table_names = set()
        for pattern in table_patterns:
            matches = re.findall(pattern, datamodel_str, re.IGNORECASE)
            table_names.update(matches)
            if matches:
                self._log_info(f"Found {len(matches)} tables with pattern")

        if not table_names:
            self._log_warning("No tables found with regex patterns")

        for table_name in table_names:
            # Skip special tables
            if table_name in ['UserHierarchy', 'Measure', 'Column', 'Relationship']:
                continue

            table = Table(
                name=table_name,
                columns=[],  # Simplified for now
                table_type=TableType.REGULAR
            )
            tables.append(table)

        self._log_info(f"Extracted {len(tables)} tables")

        # Extract measures with multiple patterns
        self._log_info("Extracting measures with regex...")

        measure_patterns = [
            r'"Name"\s*:\s*"([^"]+)"[^}]*?"Expression"\s*:\s*\[?"([^"\]]+)"\]?',
            r'<Measure[^>]*Name="([^"]+)"[^>]*>[\s\S]*?<Expression>([^<]+)</Expression>',
        ]

        for pattern in measure_patterns:
            measure_matches = re.findall(pattern, datamodel_str, re.DOTALL)
            if measure_matches:
                self._log_info(f"Found {len(measure_matches)} measures with pattern")

                for name, expression in measure_matches:
                    # Clean expression
                    clean_expression = expression.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
                    clean_expression = clean_expression.strip()

                    if clean_expression and name not in [m.name for m in all_measures]:
                        measure = DAXMeasure(
                            name=name,
                            expression=clean_expression,
                            table='Unknown'
                        )
                        all_measures.append(measure)

        self._log_info(f"Extracted {len(all_measures)} measures")

        # Extract relationships with multiple patterns
        self._log_info("Extracting relationships with regex...")

        rel_patterns = [
            r'"fromTable"\s*:\s*"([^"]+)"[^}]*"fromColumn"\s*:\s*"([^"]+)"[^}]*"toTable"\s*:\s*"([^"]+)"[^}]*"toColumn"\s*:\s*"([^"]+)"',
            r'<Relationship[^>]*>[\s\S]*?FromTable="([^"]+)"[\s\S]*?FromColumn="([^"]+)"[\s\S]*?ToTable="([^"]+)"[\s\S]*?ToColumn="([^"]+)"',
        ]

        for pattern in rel_patterns:
            rel_matches = re.findall(pattern, datamodel_str, re.DOTALL)
            if rel_matches:
                self._log_info(f"Found {len(rel_matches)} relationships with pattern")

                for from_table, from_col, to_table, to_col in rel_matches:
                    # Check for duplicates
                    is_duplicate = any(
                        r.from_table == from_table and r.from_column == from_col and
                        r.to_table == to_table and r.to_column == to_col
                        for r in relationships
                    )

                    if not is_duplicate:
                        relationship = Relationship(
                            from_table=from_table,
                            from_column=from_col,
                            to_table=to_table,
                            to_column=to_col,
                            cardinality=Cardinality.MANY_TO_ONE,
                            cross_filter_direction=CrossFilterDirection.SINGLE
                        )
                        relationships.append(relationship)

        self._log_info(f"Extracted {len(relationships)} relationships")

        data_model = DataModel(tables=tables, relationships=relationships, measures=all_measures)
        self._log_success(f"Regex parsing complete: {len(tables)} tables, {len(relationships)} rels, {len(all_measures)} measures")

        return data_model

    def _parse_layout(self, zip_ref: zipfile.ZipFile) -> ReportLayout:
        """Parse Report/Layout from PBIX"""
        try:
            layout_bytes = zip_ref.read('Report/Layout')
            layout_str = layout_bytes.decode('utf-16-le')
            layout_data = json.loads(layout_str)

            pages = []
            for section in layout_data.get('sections', []):
                # Count visuals
                visuals = section.get('visualContainers', [])

                page = Page(
                    name=section.get('name', ''),
                    display_name=section.get('displayName', section.get('name', '')),
                    visuals=[],  # Simplified
                    is_hidden=section.get('hidden', False),
                    width=section.get('width'),
                    height=section.get('height')
                )

                # Parse visuals (simplified)
                for visual in visuals:
                    config = visual.get('config', '{}')
                    if isinstance(config, str):
                        try:
                            config_json = json.loads(config)
                            visual_type = config_json.get('singleVisual', {}).get('visualType', 'other')

                            vis = Visual(
                                name=visual.get('name', ''),
                                visual_type=VisualType.from_string(visual_type),
                                page=page.name
                            )
                            page.visuals.append(vis)
                        except:
                            pass

                pages.append(page)

            return ReportLayout(pages=pages)

        except Exception as e:
            self._log_warning(f"Error parsing layout: {e}")
            return ReportLayout()

    def _parse_security(self, zip_ref: zipfile.ZipFile) -> SecurityConfiguration:
        """Parse security (RLS) from DataModel"""
        try:
            datamodel_bytes = zip_ref.read('DataModel')
            datamodel_str = datamodel_bytes.decode('utf-16-le', errors='ignore')

            roles = []

            # Extract role names
            role_pattern = r'"Role".*?"Name":\s*"([^"]+)"'
            role_names = re.findall(role_pattern, datamodel_str)

            for role_name in role_names:
                role = RLSRole(name=role_name)
                roles.append(role)

            # Extract table permissions
            filter_pattern = r'"TablePermission".*?"Table":\s*"([^"]+)".*?"FilterExpression":\s*\["([^"]*?)"\]'
            filters = re.findall(filter_pattern, datamodel_str, re.DOTALL)

            for table, filter_expr in filters:
                perm = TablePermission(
                    table=table,
                    filter_expression=filter_expr.replace('\\n', ' ').replace('\\r', '')
                )
                if roles:
                    roles[0].table_permissions.append(perm)

            return SecurityConfiguration(rls_roles=roles)

        except Exception as e:
            self._log_warning(f"Error parsing security: {e}")
            return SecurityConfiguration()

    def _map_data_type(self, data_type: Optional[str]) -> ColumnDataType:
        """Map data type string to ColumnDataType enum"""
        if not data_type:
            return ColumnDataType.UNKNOWN

        type_map = {
            'string': ColumnDataType.STRING,
            'int64': ColumnDataType.INT64,
            'double': ColumnDataType.DOUBLE,
            'boolean': ColumnDataType.BOOLEAN,
            'datetime': ColumnDataType.DATETIME,
            'decimal': ColumnDataType.DECIMAL
        }

        return type_map.get(data_type.lower(), ColumnDataType.UNKNOWN)
