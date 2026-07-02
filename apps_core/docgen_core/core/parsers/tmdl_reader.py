"""
TMDL (Tabular Model Definition Language) Reader
Utilities for parsing TMDL files from PBIP projects
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging


class TMDLReader:
    """Reader for TMDL format files"""

    def __init__(self, definition_path: Path):
        """
        Initialize TMDL reader

        Args:
            definition_path: Path to the definition folder (.SemanticModel/definition)
        """
        self.definition_path = Path(definition_path)
        self.logger = logging.getLogger(__name__)

    def read_model(self) -> Dict[str, Any]:
        """
        Read model.tmdl file

        Returns:
            Dictionary with model configuration
        """
        model_file = self.definition_path / 'model.tmdl'

        if not model_file.exists():
            self.logger.warning(f"model.tmdl not found at {model_file}")
            return {}

        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            'content': content,
            'table_references': self._extract_table_references(content)
        }

    def read_relationships(self) -> List[Dict[str, Any]]:
        """
        Read relationships.tmdl file

        Returns:
            List of relationship dictionaries
        """
        rel_file = self.definition_path / 'relationships.tmdl'

        if not rel_file.exists():
            self.logger.warning(f"relationships.tmdl not found")
            return []

        with open(rel_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._parse_relationships(content)

    def read_table(self, table_name: str) -> Dict[str, Any]:
        """
        Read a specific table TMDL file

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table definition
        """
        tables_dir = self.definition_path / 'tables'

        if not tables_dir.exists():
            self.logger.warning(f"tables/ directory not found")
            return {}

        # Try to find the table file
        table_file = None
        for filename in os.listdir(tables_dir):
            if filename.endswith('.tmdl'):
                file_path = tables_dir / filename
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    # Check if this file defines the table we're looking for
                    if f"table '{table_name}'" in first_line or f'table {table_name}' in first_line:
                        table_file = file_path
                        break

        if not table_file:
            self.logger.warning(f"Table file for '{table_name}' not found")
            return {}

        with open(table_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return self._parse_table(content, table_name)

    def read_all_tables(self) -> List[Dict[str, Any]]:
        """
        Read all table TMDL files

        Returns:
            List of table dictionaries
        """
        tables_dir = self.definition_path / 'tables'

        if not tables_dir.exists():
            return []

        tables = []
        for filename in os.listdir(tables_dir):
            if filename.endswith('.tmdl'):
                file_path = tables_dir / filename
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                table = self._parse_table(content)
                if table:
                    tables.append(table)

        return tables

    def _extract_table_references(self, content: str) -> List[str]:
        """Extract table references from model.tmdl"""
        # Pattern: ref table 'TableName' or ref table TableName
        pattern = r"ref table ['\"]?([^'\";\n]+)['\"]?"
        matches = re.findall(pattern, content)
        return [match.strip() for match in matches]

    def _parse_relationships(self, content: str) -> List[Dict[str, Any]]:
        """Parse relationships from relationships.tmdl"""
        relationships = []

        # Split by relationship blocks
        rel_blocks = re.split(r'\nrelationship ', content)

        for block in rel_blocks[1:]:  # Skip first empty block
            rel = self._parse_relationship_block(block)
            if rel:
                relationships.append(rel)

        return relationships

    def _parse_relationship_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single relationship block"""
        lines = block.strip().split('\n')

        rel = {
            'fromTable': None,
            'fromColumn': None,
            'toTable': None,
            'toColumn': None,
            'crossFilteringBehavior': 'oneDirection',
            'fromCardinality': 'many',
            'toCardinality': 'one',
            'isActive': True
        }

        for line in lines:
            line = line.strip()

            # fromColumn: 'Table'.'Column' or Table.Column
            if line.startswith('fromColumn:'):
                match = re.search(
                    r"fromColumn:\s*(?:'([^']+)'|([^\s.]+))\.(?:'([^']+)'|([^\s.]+))",
                    line
                )
                if match:
                    rel['fromTable'] = (match.group(1) or match.group(2)).strip()
                    rel['fromColumn'] = (match.group(3) or match.group(4)).strip()

            # toColumn: 'Table'.'Column' or Table.Column
            elif line.startswith('toColumn:'):
                match = re.search(
                    r"toColumn:\s*(?:'([^']+)'|([^\s.]+))\.(?:'([^']+)'|([^\s.]+))",
                    line
                )
                if match:
                    rel['toTable'] = (match.group(1) or match.group(2)).strip()
                    rel['toColumn'] = (match.group(3) or match.group(4)).strip()

            # crossFilteringBehavior
            elif line.startswith('crossFilteringBehavior:'):
                behavior = line.split(':', 1)[1].strip()
                rel['crossFilteringBehavior'] = behavior

            # fromCardinality
            elif line.startswith('fromCardinality:'):
                card = line.split(':', 1)[1].strip()
                rel['fromCardinality'] = card

            # toCardinality
            elif line.startswith('toCardinality:'):
                card = line.split(':', 1)[1].strip()
                rel['toCardinality'] = card

            # isActive
            elif line.startswith('isActive:'):
                active = line.split(':', 1)[1].strip().lower()
                rel['isActive'] = active == 'true'

        # Validate required fields
        if all([rel['fromTable'], rel['fromColumn'], rel['toTable'], rel['toColumn']]):
            return rel

        return None

    def _parse_table(self, content: str, table_name: str = None) -> Optional[Dict[str, Any]]:
        """Parse table definition from TMDL content"""
        # Extract table name from first line if not provided
        if not table_name:
            table_match = re.match(r"table ['\"]?([^'\"\n]+)['\"]?", content)
            if not table_match:
                return None
            table_name = table_match.group(1).strip()

        table = {
            'name': table_name,
            'columns': [],
            'measures': [],
            'partitions': [],
            'hierarchies': []
        }

        # Parse measures
        table['measures'] = self._parse_measures(content, table_name)

        # Parse columns
        table['columns'] = self._parse_columns(content, table_name)

        # Parse partitions (detect calculated tables)
        table['partitions'] = self._parse_partitions(content, table_name)

        # Parse hierarchies
        table['hierarchies'] = self._parse_hierarchies(content, table_name)

        return table

    def _parse_measures(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse DAX measures from table content"""
        measures = []

        # Pattern: measure 'Name' = expression or measure 'Name' = ``` expression ```
        measure_pattern = r"measure ['\"]?([^'\"=]+)['\"]?\s*=\s*(`{3}[\s\S]*?`{3}|[^\n]+(?:\n\t\t[^\n]+)*)"

        matches = re.finditer(measure_pattern, content)

        for match in matches:
            measure_name = match.group(1).strip()
            expression = match.group(2).strip()

            # Clean backticks if present
            expression = expression.replace('```', '').strip()

            # Look for additional properties after the measure
            start_pos = match.end()
            next_section = content[start_pos:start_pos+500]

            # Extract formatString, displayFolder, description
            format_string = None
            display_folder = None
            description = None

            format_match = re.search(r'formatString:\s*"([^"]*)"', next_section)
            if format_match:
                format_string = format_match.group(1)

            folder_match = re.search(r'displayFolder:\s*"([^"]*)"', next_section)
            if folder_match:
                display_folder = folder_match.group(1)

            desc_match = re.search(r'description:\s*"([^"]*)"', next_section)
            if desc_match:
                description = desc_match.group(1)

            measures.append({
                'name': measure_name,
                'expression': expression,
                'table': table_name,
                'formatString': format_string,
                'displayFolder': display_folder,
                'description': description
            })

        return measures

    def _parse_columns(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse columns from table content"""
        columns = []

        # Pattern: column 'Name' or column Name
        column_pattern = r"column ['\"]?([^'\"=\n]+)['\"]?"

        matches = re.finditer(column_pattern, content)

        for match in matches:
            column_name = match.group(1).strip()

            # Check if it's a calculated column (has =)
            start_pos = match.end()
            next_lines = content[start_pos:start_pos+300]

            is_calculated = False
            expression = None
            data_type = None

            # Check for = sign (calculated column)
            if '=' in next_lines.split('\n')[0]:
                is_calculated = True
                expr_match = re.search(r'=\s*(`{3}[\s\S]*?`{3}|[^\n]+)', next_lines)
                if expr_match:
                    expression = expr_match.group(1).strip().replace('```', '')

            # Extract dataType
            type_match = re.search(r'dataType:\s*(\w+)', next_lines)
            if type_match:
                data_type = type_match.group(1)

            column = {
                'name': column_name,
                'table': table_name,
                'dataType': data_type
            }

            if is_calculated and expression:
                column['expression'] = expression
                column['type'] = 'calculated'

            columns.append(column)

        return columns

    def _parse_partitions(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse partitions (detect calculated tables)"""
        partitions = []

        # Look for partition blocks
        if re.search(r'partition\s+\S+\s*=\s*calculated', content):
            # This is a calculated table
            expr_match = re.search(
                r'partition.*?=\s*calculated\s+.*?source\s*=\s*```(.*?)```',
                content,
                re.DOTALL
            )
            if not expr_match:
                expr_match = re.search(
                    r'partition.*?=\s*calculated\s+.*?source\s*=\s*\n\s+(.*?)(?:\n\n|\n\t|\Z)',
                    content,
                    re.DOTALL
                )

            expression = expr_match.group(1).strip() if expr_match else None

            partitions.append({
                'name': table_name,
                'mode': 'import',
                'source': {
                    'type': 'calculated',
                    'expression': expression
                }
            })

        return partitions

    def _parse_hierarchies(self, content: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse hierarchies from table content"""
        hierarchies = []

        # Pattern: hierarchy 'Name'
        hierarchy_pattern = r"hierarchy ['\"]?([^'\"]+)['\"]?"

        matches = re.finditer(hierarchy_pattern, content)

        for match in matches:
            hierarchy_name = match.group(1).strip()

            # Extract levels
            start_pos = match.end()
            next_section = content[start_pos:start_pos+500]

            # Look for level definitions
            level_pattern = r"level ['\"]?([^'\"]+)['\"]?"
            levels = re.findall(level_pattern, next_section)

            hierarchies.append({
                'name': hierarchy_name,
                'table': table_name,
                'levels': levels
            })

        return hierarchies
