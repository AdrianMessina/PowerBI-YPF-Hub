"""
PBIP Parser - Modern Power BI Project Format
Parses .pbip projects with TMDL and JSON files
"""

import json
from pathlib import Path
from typing import Optional, List
import logging

from .base_parser import BasePowerBIParser
from .tmdl_reader import TMDLReader
from .format_detector import FormatDetector, PowerBIFormat
from ..models import (
    ReportMetadata, DataModel, Table, Column, ColumnDataType, TableType,
    Relationship, Cardinality, CrossFilterDirection,
    DAXMeasure, PowerQuery, DataSourceType,
    RLSRole, TablePermission, SecurityConfiguration,
    ReportLayout, Page, Visual, VisualType, Bookmark,
    Hierarchy,
    Filter, FilterType, FilterField, FilterExpression, SlicerConfig
)


class PBIPParser(BasePowerBIParser):
    """Parser for PBIP (Power BI Project) format"""

    def __init__(self, pbip_path: str):
        """
        Initialize PBIP parser

        Args:
            pbip_path: Path to .pbip file or project directory
        """
        super().__init__(pbip_path)
        self.report_path, self.semantic_model_path = FormatDetector.resolve_pbip_paths(self.file_path)

        if not self.report_path and not self.semantic_model_path:
            raise ValueError(f"Could not resolve PBIP paths from {pbip_path}")

    def supports_format(self) -> bool:
        """Check if this parser supports the file format"""
        try:
            format_type = FormatDetector.detect(self.file_path)
            return format_type == PowerBIFormat.PBIP
        except:
            return False

    def validate_file(self) -> bool:
        """Validate PBIP project structure"""
        if not self.report_path and not self.semantic_model_path:
            raise ValueError("No .Report or .SemanticModel folder found")

        # Check for definition folders
        if self.semantic_model_path:
            definition_path = self.semantic_model_path / 'definition'
            if not definition_path.exists():
                raise ValueError(f"definition/ folder not found in {self.semantic_model_path}")

        return True

    def parse(self) -> ReportMetadata:
        """
        Parse PBIP project and extract all metadata

        Returns:
            ReportMetadata with complete information
        """
        self._log_info(f"Parsing PBIP project: {self.file_path.name}")

        # Initialize metadata
        metadata = ReportMetadata(
            report_name=self.get_report_name(),
            report_path=str(self.file_path),
            report_type='pbip'
        )

        # Parse semantic model (data model)
        if self.semantic_model_path:
            self._log_info("Parsing semantic model...")
            metadata.data_model = self._parse_semantic_model()
            metadata.queries = self._parse_queries()
            metadata.security = self._parse_security()

        # Parse report layout (visuals, pages)
        if self.report_path:
            self._log_info("Parsing report layout...")
            metadata.layout = self._parse_report_layout()

        self._log_success(f"PBIP parsing complete: {len(metadata.data_model.tables)} tables, "
                         f"{len(metadata.data_model.relationships)} relationships, "
                         f"{len(metadata.data_model.measures)} measures")

        return metadata

    def _parse_semantic_model(self) -> DataModel:
        """Parse the semantic model (tables, relationships, measures)"""
        definition_path = self.semantic_model_path / 'definition'

        # Check if TMDL format
        model_tmdl = definition_path / 'model.tmdl'

        if model_tmdl.exists():
            self._log_info("Detected TMDL format")
            return self._parse_tmdl_model(definition_path)
        else:
            self._log_info("Detected BIM format")
            return self._parse_bim_model(definition_path)

    def _parse_tmdl_model(self, definition_path: Path) -> DataModel:
        """Parse TMDL format model"""
        reader = TMDLReader(definition_path)

        # Read all tables
        tables_data = reader.read_all_tables()
        tables = []
        all_measures = []

        for table_data in tables_data:
            # Parse columns
            columns = []
            for col_data in table_data.get('columns', []):
                column = Column(
                    name=col_data['name'],
                    table=table_data['name'],
                    data_type=self._map_data_type(col_data.get('dataType')),
                    is_calculated=col_data.get('type') == 'calculated',
                    expression=col_data.get('expression')
                )
                columns.append(column)

            # Determine table type
            table_type = TableType.REGULAR
            if table_data.get('partitions'):
                for partition in table_data['partitions']:
                    if partition.get('source', {}).get('type') == 'calculated':
                        table_type = TableType.CALCULATED
                        break

            # Parse hierarchies
            hierarchies = []
            for hier_data in table_data.get('hierarchies', []):
                hierarchy = Hierarchy(
                    name=hier_data['name'],
                    table=table_data['name'],
                    levels=hier_data.get('levels', [])
                )
                hierarchies.append(hierarchy)

            # Create table
            table = Table(
                name=table_data['name'],
                columns=columns,
                table_type=table_type,
                hierarchies=hierarchies,
                source_expression=self._get_partition_expression(table_data.get('partitions', []))
            )
            tables.append(table)

            # Collect measures
            for measure_data in table_data.get('measures', []):
                measure = DAXMeasure(
                    name=measure_data['name'],
                    expression=measure_data['expression'],
                    table=table_data['name'],
                    description=measure_data.get('description'),
                    display_folder=measure_data.get('displayFolder'),
                    format_string=measure_data.get('formatString')
                )
                all_measures.append(measure)

        # Read relationships
        relationships_data = reader.read_relationships()
        relationships = []

        for rel_data in relationships_data:
            relationship = Relationship(
                from_table=rel_data['fromTable'],
                from_column=rel_data['fromColumn'],
                to_table=rel_data['toTable'],
                to_column=rel_data['toColumn'],
                cardinality=Cardinality.from_parts(
                    rel_data['fromCardinality'],
                    rel_data['toCardinality']
                ),
                cross_filter_direction=CrossFilterDirection.from_behavior(
                    rel_data['crossFilteringBehavior']
                ),
                is_active=rel_data.get('isActive', True)
            )
            relationships.append(relationship)

        # Create data model
        data_model = DataModel(
            tables=tables,
            relationships=relationships,
            measures=all_measures
        )

        return data_model

    def _parse_bim_model(self, definition_path: Path) -> DataModel:
        """Parse BIM (JSON) format model"""
        # Look for dataset.bim or model.bim
        model_file = None
        for filename in ['dataset.bim', 'model.bim', 'Dataset.bim']:
            potential_path = definition_path / filename
            if potential_path.exists():
                model_file = potential_path
                break

        if not model_file:
            self._log_warning("No BIM file found")
            return DataModel()

        with open(model_file, 'r', encoding='utf-8-sig') as f:
            model_data = json.load(f)

        return self._parse_bim_data(model_data)

    def _parse_bim_data(self, model_data: dict) -> DataModel:
        """Parse BIM JSON data structure"""
        model = model_data.get('model', {})

        tables = []
        all_measures = []

        # Parse tables
        for table_data in model.get('tables', []):
            columns = []
            for col_data in table_data.get('columns', []):
                column = Column(
                    name=col_data.get('name', 'Unknown'),
                    table=table_data.get('name', 'Unknown'),
                    data_type=self._map_data_type(col_data.get('dataType')),
                    is_calculated='expression' in col_data,
                    expression=col_data.get('expression')
                )
                columns.append(column)

            # Determine table type
            table_type = TableType.REGULAR
            for partition in table_data.get('partitions', []):
                source = partition.get('source', {})
                if source.get('type') == 'calculated':
                    table_type = TableType.CALCULATED
                    break

            table = Table(
                name=table_data.get('name', 'Unknown'),
                columns=columns,
                table_type=table_type
            )
            tables.append(table)

            # Collect measures
            for measure_data in table_data.get('measures', []):
                measure = DAXMeasure(
                    name=measure_data.get('name', 'Unknown'),
                    expression=measure_data.get('expression', ''),
                    table=table_data.get('name', 'Unknown'),
                    description=measure_data.get('description'),
                    format_string=measure_data.get('formatString')
                )
                all_measures.append(measure)

        # Parse relationships
        relationships = []
        for rel_data in model.get('relationships', []):
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

    def _parse_queries(self) -> list:
        """Parse Power Query M queries from table partitions"""
        queries = []
        definition_path = self.semantic_model_path / 'definition'
        model_tmdl = definition_path / 'model.tmdl'

        if not model_tmdl.exists():
            return queries

        try:
            reader = TMDLReader(definition_path)
            tables_data = reader.read_all_tables()

            for table_data in tables_data:
                table_name = table_data.get('name', 'Unknown')

                # Skip auto-generated date tables
                if 'LocalDateTable' in table_name or 'DateTableTemplate' in table_name:
                    continue

                for partition in table_data.get('partitions', []):
                    source = partition.get('source', {})
                    source_type = source.get('type', '')
                    expression = source.get('expression', '')

                    if expression and source_type in ('query', 'calculated'):
                        queries.append(PowerQuery(
                            name=table_name,
                            expression=expression,
                            table=table_name
                        ))
        except Exception as e:
            self._log_warning(f"Error parsing Power Query queries: {e}")

        return queries

    def _parse_security(self) -> SecurityConfiguration:
        """Parse RLS roles and security"""
        # TODO: Implement security parsing from model
        return SecurityConfiguration()

    def _parse_report_layout(self) -> ReportLayout:
        """Parse report layout (pages, visuals)"""
        definition_path = self.report_path / 'definition'

        # Parse report-level filters first
        report_filters = self._parse_report_filters()

        # Check for pages/ folder first (new format with definition/pages/)
        pages_dir = definition_path / 'pages'
        pages_json = pages_dir / 'pages.json'

        if pages_dir.exists() and pages_json.exists():
            self._log_info(f"Detected new PBIP format with pages/ folder")
            layout = self._parse_pages_folder(definition_path)
        else:
            # Fallback to report.json (old format with sections)
            report_json = definition_path / 'report.json'
            if report_json.exists():
                self._log_info(f"Using old format report.json")
                layout = self._parse_report_json(report_json)
            else:
                self._log_warning("No report layout found")
                layout = ReportLayout()

        # Add report filters to layout
        layout.report_filters = report_filters
        return layout

    def _parse_report_json(self, report_json: Path) -> ReportLayout:
        """Parse report.json (old format)"""
        with open(report_json, 'r', encoding='utf-8-sig') as f:
            report_data = json.load(f)

        pages = []
        for section in report_data.get('sections', []):
            page = Page(
                name=section.get('name', ''),
                display_name=section.get('displayName', section.get('name', '')),
                visuals=[],  # TODO: Parse visuals from visualContainers
                is_hidden=section.get('hidden', False)
            )
            pages.append(page)

        return ReportLayout(pages=pages)

    def _parse_pages_folder(self, definition_path: Path) -> ReportLayout:
        """Parse pages from pages/ folder (new format)"""
        pages_dir = definition_path / 'pages'

        if not pages_dir.exists():
            self._log_warning(f"pages/ directory not found at {pages_dir}")
            return ReportLayout()

        # Read pages.json
        pages_json = pages_dir / 'pages.json'
        if not pages_json.exists():
            self._log_warning(f"pages.json not found at {pages_json}")
            return ReportLayout()

        with open(pages_json, 'r', encoding='utf-8-sig') as f:
            pages_metadata = json.load(f)

        page_order = pages_metadata.get('pageOrder', [])
        self._log_info(f"Found {len(page_order)} pages in pages.json")

        pages = []
        total_visuals = 0

        for page_id in page_order:
            page_dir = pages_dir / page_id
            if not page_dir.exists():
                self._log_warning(f"Page directory not found: {page_id}")
                continue

            # Read page.json
            page_json = page_dir / 'page.json'
            if page_json.exists():
                with open(page_json, 'r', encoding='utf-8-sig') as f:
                    page_data = json.load(f)

                page_name = page_data.get('displayName', page_id)

                # Parse page-level filters
                page_filters = self._parse_page_filters(page_data, page_name)

                # Parse visuals
                visuals = self._parse_visuals(page_dir, page_name)
                total_visuals += len(visuals)

                page = Page(
                    name=page_data.get('name', page_id),
                    display_name=page_name,
                    visuals=visuals,
                    filters=page_filters,
                    is_hidden=page_data.get('hidden', False)
                )
                pages.append(page)
                self._log_info(f"  Parsed page '{page_name}' with {len(visuals)} visuals")

        self._log_info(f"Parsed {len(pages)} pages with {total_visuals} total visuals")
        return ReportLayout(pages=pages)

    def _parse_visuals(self, page_dir: Path, page_name: str) -> List[Visual]:
        """Parse visuals from visuals/ folder"""
        visuals_dir = page_dir / 'visuals'

        if not visuals_dir.exists():
            return []

        visuals = []

        # Iterate through all visual directories
        for visual_dir in visuals_dir.iterdir():
            if not visual_dir.is_dir():
                continue

            visual_json = visual_dir / 'visual.json'
            if not visual_json.exists():
                continue

            try:
                with open(visual_json, 'r', encoding='utf-8-sig') as f:
                    visual_data = json.load(f)

                # Get visual name and type
                visual_name = visual_data.get('name', visual_dir.name)
                visual_obj = visual_data.get('visual', {})
                visual_type = visual_obj.get('visualType', 'unknown')

                # Parse visual filters using existing method
                filters, is_slicer, slicer_config = self._parse_visual_filters(visual_data, page_name)

                # Skip slicers - already handled separately
                if is_slicer:
                    continue

                # Get visual position
                position = visual_data.get('position', {})

                # Create Visual object
                visual = Visual(
                    name=visual_name,
                    visual_type=visual_type,
                    page=page_name,
                    title=None,  # Could extract from objects if needed
                    position=position,
                    filters=filters,
                    is_hidden=False
                )

                visuals.append(visual)

            except Exception as e:
                self._log_warning(f"Could not parse visual {visual_dir.name}: {e}")

        if visuals:
            visuals_with_filters = [v for v in visuals if v.filters]
            self._log_info(f"Parsed {len(visuals)} visuals for page '{page_name}' ({len(visuals_with_filters)} with filters)")

        return visuals

    def _map_data_type(self, data_type: Optional[str]) -> ColumnDataType:
        """Map TMDL/BIM data type to ColumnDataType enum"""
        if not data_type:
            return ColumnDataType.UNKNOWN

        type_map = {
            'string': ColumnDataType.STRING,
            'int64': ColumnDataType.INT64,
            'double': ColumnDataType.DOUBLE,
            'boolean': ColumnDataType.BOOLEAN,
            'dateTime': ColumnDataType.DATETIME,
            'decimal': ColumnDataType.DECIMAL
        }

        return type_map.get(data_type.lower(), ColumnDataType.UNKNOWN)

    def _get_partition_expression(self, partitions: list) -> Optional[str]:
        """Extract expression from calculated table partition"""
        for partition in partitions:
            source = partition.get('source', {})
            if source.get('type') == 'calculated':
                return source.get('expression')
        return None

    # === FILTER PARSING METHODS ===

    def _parse_report_filters(self) -> list:
        """Parse report-level filters from report.json"""
        try:
            definition_path = self.report_path / 'definition'
            report_json = definition_path / 'report.json'

            if not report_json.exists():
                self._log_info("No report.json found for filter parsing")
                return []

            with open(report_json, 'r', encoding='utf-8-sig') as f:
                report_data = json.load(f)

            filter_config = report_data.get('filterConfig', {})
            filters_data = filter_config.get('filters', [])

            self._log_info(f"Parsing {len(filters_data)} report-level filters")
            filters = []

            for filter_data in filters_data:
                try:
                    filter_obj = self._parse_filter_config(filter_data, scope="Report")
                    if filter_obj:
                        filters.append(filter_obj)
                except Exception as e:
                    self._log_warning(f"Could not parse report filter: {e}")

            self._log_info(f"Found {len(filters)} report-level filters")
            return filters

        except Exception as e:
            self._log_warning(f"Error parsing report filters: {e}")
            return []

    def _parse_page_filters(self, page_data: dict, page_name: str) -> list:
        """Parse page-level filters from page.json"""
        try:
            filter_config = page_data.get('filterConfig', {})
            filters_data = filter_config.get('filters', [])

            if not filters_data:
                return []

            self._log_info(f"Parsing {len(filters_data)} page-level filters for page '{page_name}'")
            filters = []

            for filter_data in filters_data:
                try:
                    filter_obj = self._parse_filter_config(filter_data, scope=f"Page: {page_name}")
                    if filter_obj:
                        filters.append(filter_obj)
                except Exception as e:
                    self._log_warning(f"Could not parse page filter: {e}")

            return filters

        except Exception as e:
            self._log_warning(f"Error parsing page filters: {e}")
            return []

    def _parse_visual_filters(self, visual_data: dict, page_name: str) -> tuple:
        """
        Parse visual-level filters and detect slicers

        Returns:
            tuple: (filters_list, is_slicer, slicer_config)
        """
        try:
            # Check if this is a slicer
            visual_type = visual_data.get('visualType', '')
            is_slicer = visual_type == 'slicer'

            # Parse filters
            filter_config = visual_data.get('filterConfig', {})
            filters_data = filter_config.get('filters', [])

            filters = []
            for filter_data in filters_data:
                try:
                    filter_obj = self._parse_filter_config(filter_data, scope=f"Visual ({page_name})")
                    if filter_obj:
                        filters.append(filter_obj)
                except Exception as e:
                    self._log_warning(f"Could not parse visual filter: {e}")

            # Parse slicer configuration if applicable
            slicer_config = None
            if is_slicer:
                slicer_config = self._parse_slicer_config(visual_data)

            return (filters, is_slicer, slicer_config)

        except Exception as e:
            self._log_warning(f"Error parsing visual filters: {e}")
            return ([], False, None)

    def _parse_filter_config(self, filter_data: dict, scope: str) -> Optional[Filter]:
        """Parse a filter configuration from JSON to Filter object"""
        try:
            # Extract filter type
            filter_type_str = filter_data.get('type', 'Unknown')
            filter_type = FilterType.from_string(filter_type_str)

            # Extract field reference
            from_parts = filter_data.get('from', [])
            if not from_parts:
                return None

            # Get table and column from first part
            first_part = from_parts[0] if isinstance(from_parts, list) else from_parts
            table = first_part.get('entity', '') if isinstance(first_part, dict) else ''
            column = first_part.get('property', '') if isinstance(first_part, dict) else ''

            if not table or not column:
                return None

            field = FilterField(table=table, column=column)

            # Parse filter expression
            filter_expr_data = filter_data.get('filter', {})
            expression = self._parse_filter_expression(filter_expr_data, filter_type)

            # Get filter metadata
            name = filter_data.get('name', f"{table}_{column}")
            how_created = filter_data.get('howCreated', 'User')
            is_locked = filter_data.get('isLockedInViewMode', False)
            is_hidden = filter_data.get('isHiddenInViewMode', False)

            # Create Filter object
            filter_obj = Filter(
                name=name,
                field=field,
                expression=expression,
                scope=scope,
                how_created=how_created,
                is_locked=is_locked,
                is_hidden=is_hidden
            )

            return filter_obj

        except Exception as e:
            self._log_warning(f"Error parsing filter config: {e}")
            return None

    def _parse_filter_expression(self, filter_expr_data: dict, filter_type: FilterType) -> FilterExpression:
        """Parse filter expression from JSON"""
        try:
            values = []
            conditions = []
            is_inverted = False

            # Handle different filter types
            if filter_type == FilterType.CATEGORICAL:
                # Extract selected values
                if 'In' in filter_expr_data:
                    in_expr = filter_expr_data['In']
                    values_data = in_expr.get('Values', [])
                    for val_data in values_data:
                        if isinstance(val_data, list) and len(val_data) > 0:
                            literal = val_data[0].get('Literal', {})
                            value = literal.get('Value')
                            if value is not None:
                                values.append(value)

                # Check if inverted (exclude mode)
                if 'Not' in filter_expr_data:
                    is_inverted = True

            elif filter_type == FilterType.ADVANCED:
                # Extract conditions
                # Advanced filters can be complex - simplified parsing
                if 'And' in filter_expr_data:
                    and_conditions = filter_expr_data['And']
                    for cond in and_conditions:
                        conditions.append(cond)
                elif 'Or' in filter_expr_data:
                    or_conditions = filter_expr_data['Or']
                    for cond in or_conditions:
                        conditions.append(cond)

            elif filter_type == FilterType.BASIC:
                # Basic filter - similar to categorical
                if 'In' in filter_expr_data:
                    in_expr = filter_expr_data['In']
                    values_data = in_expr.get('Values', [])
                    for val_data in values_data:
                        if isinstance(val_data, list) and len(val_data) > 0:
                            literal = val_data[0].get('Literal', {})
                            value = literal.get('Value')
                            if value is not None:
                                values.append(value)

            expression = FilterExpression(
                filter_type=filter_type,
                values=values,
                conditions=conditions,
                is_inverted=is_inverted,
                raw_data=filter_expr_data
            )

            return expression

        except Exception as e:
            self._log_warning(f"Error parsing filter expression: {e}")
            return FilterExpression(filter_type=filter_type, raw_data=filter_expr_data)

    def _parse_slicer_config(self, visual_data: dict) -> Optional[dict]:
        """Parse slicer configuration"""
        try:
            # Extract slicer field
            query_data = visual_data.get('query', {})
            commands = query_data.get('Commands', [])

            if not commands:
                return None

            first_command = commands[0] if isinstance(commands, list) else commands
            select_data = first_command.get('SemanticQueryDataShapeCommand', {})
            query = select_data.get('Query', {})
            from_data = query.get('From', [])

            if not from_data:
                return None

            first_from = from_data[0]
            table = first_from.get('Entity', '')

            # Get column
            select = query.get('Select', [])
            if not select:
                return None

            first_select = select[0]
            column_data = first_select.get('Column', {})
            expression = column_data.get('Expression', {})
            source_ref = expression.get('SourceRef', {})
            source = source_ref.get('Source', '')

            property_name = column_data.get('Property', '')

            if not property_name:
                return None

            # Get slicer settings
            slicer_objects = visual_data.get('objects', {})
            general = slicer_objects.get('general', [{}])[0] if 'general' in slicer_objects else {}

            mode = "Basic"
            orientation = "Vertical"

            # Try to detect mode from settings
            if 'slicer' in slicer_objects:
                slicer_settings = slicer_objects['slicer'][0] if isinstance(slicer_objects['slicer'], list) else slicer_objects['slicer']
                properties = slicer_settings.get('properties', {})

                # Check for dropdown or list mode
                if 'selectionMode' in properties:
                    mode_value = properties['selectionMode']
                    if isinstance(mode_value, dict):
                        mode = mode_value.get('expr', {}).get('Literal', {}).get('Value', 'Basic')

            slicer_config = {
                'table': table,
                'column': property_name,
                'mode': mode,
                'orientation': orientation
            }

            return slicer_config

        except Exception as e:
            self._log_warning(f"Error parsing slicer config: {e}")
            return None
