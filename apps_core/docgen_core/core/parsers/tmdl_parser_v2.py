"""
TMDL Parser V2 - Improved Structured Parser
Parses TMDL files without fragile regex, using line-by-line structured parsing.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TMDLMeasure:
    """Represents a DAX measure from TMDL"""
    name: str
    expression: str
    table: str
    format_string: Optional[str] = None
    display_folder: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None


@dataclass
class TMDLColumn:
    """Represents a column from TMDL"""
    name: str
    table: str
    data_type: Optional[str] = None
    source_column: Optional[str] = None
    expression: Optional[str] = None  # For calculated columns
    is_hidden: bool = False
    summarize_by: Optional[str] = None


@dataclass
class TMDLRelationship:
    """Represents a relationship from TMDL"""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    from_cardinality: str = "many"
    to_cardinality: str = "one"
    cross_filtering_behavior: str = "oneDirection"
    is_active: bool = True

    def get_cardinality_display(self) -> str:
        """Get user-friendly cardinality display"""
        card_map = {
            'one': '1',
            'many': '*'
        }
        from_c = card_map.get(self.from_cardinality, self.from_cardinality)
        to_c = card_map.get(self.to_cardinality, self.to_cardinality)
        return f"{from_c}:{to_c}"


@dataclass
class TMDLTable:
    """Represents a table from TMDL"""
    name: str
    columns: List[TMDLColumn] = field(default_factory=list)
    measures: List[TMDLMeasure] = field(default_factory=list)
    partitions: List[Dict[str, Any]] = field(default_factory=list)
    hierarchies: List[Dict[str, Any]] = field(default_factory=list)
    is_hidden: bool = False

    @property
    def is_calculated(self) -> bool:
        """Check if this is a calculated table"""
        return any(p.get('source', {}).get('type') == 'calculated' for p in self.partitions)


@dataclass
class TMDLRole:
    """Represents an RLS role from TMDL"""
    name: str
    table_permissions: List[Dict[str, str]] = field(default_factory=list)
    description: Optional[str] = None


class TMDLParserV2:
    """
    Improved TMDL parser with structured line-by-line parsing.
    More robust than regex-based approaches.
    """

    def __init__(self, definition_path: Path):
        """
        Initialize TMDL parser

        Args:
            definition_path: Path to .SemanticModel/definition folder
        """
        self.definition_path = Path(definition_path)
        self.logger = logging.getLogger(__name__)

    def parse_all(self) -> Dict[str, Any]:
        """
        Parse all TMDL files and return complete metadata

        Returns:
            Dictionary with all extracted metadata
        """
        self.logger.info(f"Parsing TMDL from {self.definition_path}")

        metadata = {
            'model': self.parse_model(),
            'tables': self.parse_all_tables(),
            'relationships': self.parse_relationships(),
            'roles': self.parse_roles()
        }

        self.logger.info(f"Parsed {len(metadata['tables'])} tables, "
                        f"{len(metadata['relationships'])} relationships")

        return metadata

    def parse_model(self) -> Dict[str, Any]:
        """Parse model.tmdl file"""
        model_file = self.definition_path / 'model.tmdl'

        if not model_file.exists():
            self.logger.warning(f"model.tmdl not found")
            return {}

        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()

        model = {
            'name': self._extract_model_name(content),
            'culture': self._extract_property(content, 'culture'),
            'default_mode': self._extract_property(content, 'defaultMode'),
        }

        return model

    def parse_all_tables(self) -> List[TMDLTable]:
        """Parse all table TMDL files"""
        tables_dir = self.definition_path / 'tables'

        if not tables_dir.exists():
            self.logger.warning("tables/ directory not found")
            return []

        tables = []
        for file_path in tables_dir.glob('*.tmdl'):
            try:
                table = self.parse_table_file(file_path)
                if table:
                    tables.append(table)
            except Exception as e:
                self.logger.error(f"Error parsing table file {file_path.name}: {e}")

        return tables

    def parse_table_file(self, file_path: Path) -> Optional[TMDLTable]:
        """Parse a single table TMDL file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract table name from first line
        table_name = self._extract_table_name(content)
        if not table_name:
            return None

        table = TMDLTable(name=table_name)

        # Parse components
        table.columns = self._parse_columns(content, table_name)
        table.measures = self._parse_measures(content, table_name)
        table.partitions = self._parse_partitions(content, table_name)
        table.hierarchies = self._parse_hierarchies(content, table_name)
        table.is_hidden = 'isHidden' in content

        return table

    def parse_relationships(self) -> List[TMDLRelationship]:
        """Parse relationships.tmdl file"""
        rel_file = self.definition_path / 'relationships.tmdl'

        if not rel_file.exists():
            self.logger.warning("relationships.tmdl not found")
            return []

        with open(rel_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._parse_relationships_content(content)

    def parse_roles(self) -> List[TMDLRole]:
        """Parse roles from roles/ directory"""
        roles_dir = self.definition_path / 'roles'

        if not roles_dir.exists():
            return []

        roles = []
        for file_path in roles_dir.glob('*.tmdl'):
            try:
                role = self._parse_role_file(file_path)
                if role:
                    roles.append(role)
            except Exception as e:
                self.logger.error(f"Error parsing role file {file_path.name}: {e}")

        return roles

    # --- Private parsing methods ---

    def _extract_model_name(self, content: str) -> Optional[str]:
        """Extract model name from model.tmdl"""
        match = re.search(r'model\s+([^\s{]+)', content)
        return match.group(1).strip('\'"') if match else None

    def _extract_table_name(self, content: str) -> Optional[str]:
        """Extract table name from first line"""
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            match = re.match(r'\s*table\s+[\'"]?([^\'"{\n]+)[\'"]?', line)
            if match:
                return match.group(1).strip()
        return None

    def _extract_property(self, content: str, prop_name: str) -> Optional[str]:
        """Extract a simple property value"""
        pattern = rf'{prop_name}\s*[:=]\s*[\'"]?([^\'";\n]+)[\'"]?'
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None

    def _parse_measures(self, content: str, table_name: str) -> List[TMDLMeasure]:
        """Parse measures using structured approach"""
        measures = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for measure definition
            if line.startswith('measure'):
                measure = self._parse_measure_block(lines, i, table_name)
                if measure:
                    measures.append(measure)

            i += 1

        return measures

    def _parse_measure_block(self, lines: List[str], start_idx: int,
                             table_name: str) -> Optional[TMDLMeasure]:
        """Parse a single measure block"""
        first_line = lines[start_idx].strip()

        # Extract measure name and start of expression
        match = re.match(r'measure\s+[\'"]?([^\'"=]+)[\'"]?\s*=\s*(.*)', first_line)
        if not match:
            return None

        measure_name = match.group(1).strip()
        expr_start = match.group(2).strip()

        # Handle multi-line expressions
        expression = expr_start

        # Check if expression uses triple backticks
        if expr_start.startswith('```'):
            expression = self._extract_multiline_backtick(lines, start_idx)
        else:
            # Single line or continuation
            if not expr_start.endswith(';'):
                # Look for continuation
                i = start_idx + 1
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('formatString', 'displayFolder', 'description', 'measure', 'column', 'partition')):
                    continuation = lines[i].strip()
                    if continuation.startswith('```'):
                        expression = self._extract_multiline_backtick(lines, i)
                        break
                    expression += ' ' + continuation
                    i += 1

        # Clean expression
        expression = expression.replace('```', '').strip()

        # Look for additional properties
        format_string = None
        display_folder = None
        description = None

        # Scan next ~20 lines for properties
        for i in range(start_idx + 1, min(start_idx + 20, len(lines))):
            line = lines[i].strip()

            if line.startswith('formatString'):
                format_string = self._extract_quoted_value(line)
            elif line.startswith('displayFolder'):
                display_folder = self._extract_quoted_value(line)
            elif line.startswith('description'):
                description = self._extract_quoted_value(line)
            elif line.startswith(('measure', 'column', 'partition', 'hierarchy')):
                # Next definition block
                break

        return TMDLMeasure(
            name=measure_name,
            expression=expression,
            table=table_name,
            format_string=format_string,
            display_folder=display_folder,
            description=description
        )

    def _parse_columns(self, content: str, table_name: str) -> List[TMDLColumn]:
        """Parse columns from table content"""
        columns = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('column'):
                column = self._parse_column_block(lines, i, table_name)
                if column:
                    columns.append(column)

            i += 1

        return columns

    def _parse_column_block(self, lines: List[str], start_idx: int,
                           table_name: str) -> Optional[TMDLColumn]:
        """Parse a single column block"""
        first_line = lines[start_idx].strip()

        # Extract column name
        match = re.match(r'column\s+[\'"]?([^\'"=\n]+)[\'"]?', first_line)
        if not match:
            return None

        column_name = match.group(1).strip()

        # Look for properties
        data_type = None
        source_column = None
        expression = None
        is_hidden = False

        # Check if calculated (has =)
        if '=' in first_line:
            expr_start = first_line.split('=', 1)[1].strip()
            if expr_start.startswith('```'):
                expression = self._extract_multiline_backtick(lines, start_idx)
            else:
                expression = expr_start

        # Scan next lines for properties
        for i in range(start_idx + 1, min(start_idx + 15, len(lines))):
            line = lines[i].strip()

            if line.startswith('dataType'):
                data_type = self._extract_property_value(line)
            elif line.startswith('sourceColumn'):
                source_column = self._extract_quoted_value(line)
            elif line.startswith('isHidden'):
                is_hidden = True
            elif line.startswith(('column', 'measure', 'partition', 'hierarchy')):
                break

        return TMDLColumn(
            name=column_name,
            table=table_name,
            data_type=data_type,
            source_column=source_column,
            expression=expression,
            is_hidden=is_hidden
        )

    def _parse_partitions(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse partition definitions"""
        partitions = []

        # Look for partition blocks
        if 'partition' in content.lower():
            lines = content.split('\n')

            for i, line in enumerate(lines):
                if line.strip().startswith('partition'):
                    partition = self._parse_partition_block(lines, i, table_name)
                    if partition:
                        partitions.append(partition)

        return partitions

    def _parse_partition_block(self, lines: List[str], start_idx: int,
                               table_name: str) -> Optional[Dict[str, Any]]:
        """Parse a partition block"""
        partition = {
            'name': table_name,
            'mode': 'import',
            'source': {}
        }

        # Check if calculated
        if 'calculated' in lines[start_idx]:
            partition['source']['type'] = 'calculated'

            # Extract expression
            for i in range(start_idx, min(start_idx + 50, len(lines))):
                line = lines[i].strip()
                if 'source' in line and '=' in line:
                    # Look for expression
                    if '```' in line or (i + 1 < len(lines) and '```' in lines[i + 1]):
                        expression = self._extract_multiline_backtick(lines, i)
                        partition['source']['expression'] = expression
                        break
        else:
            # Query partition - extract M expression
            partition['source']['type'] = 'query'

            for i in range(start_idx, min(start_idx + 100, len(lines))):
                line = lines[i].strip()
                if 'source' in line and '=' in line:
                    if '```' in line or (i + 1 < len(lines) and '```' in lines[i + 1]):
                        expression = self._extract_multiline_backtick(lines, i)
                        if expression:
                            partition['source']['expression'] = expression
                        break

        return partition

    def _parse_hierarchies(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse hierarchy definitions"""
        hierarchies = []

        if 'hierarchy' not in content:
            return hierarchies

        lines = content.split('\n')

        for i, line in enumerate(lines):
            if line.strip().startswith('hierarchy'):
                # Extract hierarchy name
                match = re.match(r'hierarchy\s+[\'"]?([^\'"{\n]+)[\'"]?', line)
                if match:
                    hier_name = match.group(1).strip()

                    # Extract levels
                    levels = []
                    for j in range(i + 1, min(i + 20, len(lines))):
                        level_line = lines[j].strip()
                        if level_line.startswith('level'):
                            level_match = re.match(r'level\s+[\'"]?([^\'":\n]+)[\'"]?', level_line)
                            if level_match:
                                levels.append(level_match.group(1).strip())
                        elif level_line.startswith(('hierarchy', 'measure', 'column', 'partition')):
                            break

                    hierarchies.append({
                        'name': hier_name,
                        'table': table_name,
                        'levels': levels
                    })

        return hierarchies

    def _parse_relationships_content(self, content: str) -> List[TMDLRelationship]:
        """Parse relationships from content"""
        relationships = []

        # Split by relationship keyword
        blocks = re.split(r'\nrelationship\s+', content)

        for block in blocks[1:]:  # Skip first empty block
            rel = self._parse_relationship_block(block)
            if rel:
                relationships.append(rel)

        return relationships

    def _parse_relationship_block(self, block: str) -> Optional[TMDLRelationship]:
        """Parse a single relationship block"""
        lines = block.split('\n')

        rel_data = {
            'from_table': None,
            'from_column': None,
            'to_table': None,
            'to_column': None,
            'from_cardinality': 'many',
            'to_cardinality': 'one',
            'cross_filtering_behavior': 'oneDirection',
            'is_active': True
        }

        for line in lines:
            line = line.strip()

            if line.startswith('fromColumn:'):
                # Extract: fromColumn: TableName[ColumnName]
                match = re.search(r'fromColumn:\s*[\'"]?([^\'".\[]+)[\'"]?[\[.][\'\"]?([^\]\'\"]+)[\'\"]?', line)
                if match:
                    rel_data['from_table'] = match.group(1).strip()
                    rel_data['from_column'] = match.group(2).strip()

            elif line.startswith('toColumn:'):
                match = re.search(r'toColumn:\s*[\'"]?([^\'".\[]+)[\'"]?[\[.][\'\"]?([^\]\'\"]+)[\'\"]?', line)
                if match:
                    rel_data['to_table'] = match.group(1).strip()
                    rel_data['to_column'] = match.group(2).strip()

            elif line.startswith('fromCardinality:'):
                rel_data['from_cardinality'] = self._extract_property_value(line)

            elif line.startswith('toCardinality:'):
                rel_data['to_cardinality'] = self._extract_property_value(line)

            elif line.startswith('crossFilteringBehavior:'):
                rel_data['cross_filtering_behavior'] = self._extract_property_value(line)

            elif line.startswith('isActive:'):
                value = self._extract_property_value(line)
                rel_data['is_active'] = value.lower() == 'true'

        # Validate required fields
        if all([rel_data['from_table'], rel_data['from_column'],
                rel_data['to_table'], rel_data['to_column']]):
            return TMDLRelationship(**rel_data)

        return None

    def _parse_role_file(self, file_path: Path) -> Optional[TMDLRole]:
        """Parse a role TMDL file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract role name
        match = re.match(r'role\s+[\'"]?([^\'"{\n]+)[\'"]?', content)
        if not match:
            return None

        role_name = match.group(1).strip()

        # Extract table permissions
        permissions = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if 'tablePermission' in line:
                # Extract table name and filter expression
                table_match = re.search(r'tablePermission\s+[\'"]?([^\'"=\n]+)[\'"]?', line)
                if table_match:
                    table = table_match.group(1).strip()

                    # Look for filterExpression in next lines
                    filter_expr = None
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if 'filterExpression' in lines[j]:
                            filter_expr = self._extract_quoted_value(lines[j])
                            break

                    permissions.append({
                        'table': table,
                        'filter_expression': filter_expr
                    })

        return TMDLRole(
            name=role_name,
            table_permissions=permissions
        )

    # --- Helper methods ---

    def _extract_multiline_backtick(self, lines: List[str], start_idx: int) -> str:
        """Extract content between triple backticks"""
        content_lines = []
        in_block = False

        for i in range(start_idx, len(lines)):
            line = lines[i]

            if '```' in line:
                if in_block:
                    # End of block
                    break
                else:
                    # Start of block
                    in_block = True
                    # Check if there's content on the same line
                    after_backticks = line.split('```', 1)[1]
                    if after_backticks.strip():
                        content_lines.append(after_backticks)
            elif in_block:
                content_lines.append(line)

        return '\n'.join(content_lines).strip()

    def _extract_quoted_value(self, line: str) -> Optional[str]:
        """Extract value from quotes"""
        match = re.search(r'[:\s][\'"]([^\'"]*)[\'"]', line)
        return match.group(1) if match else None

    def _extract_property_value(self, line: str) -> Optional[str]:
        """Extract property value (quoted or unquoted)"""
        match = re.search(r'[:=]\s*[\'"]?([^\'";\n]+)[\'"]?', line)
        return match.group(1).strip() if match else None
