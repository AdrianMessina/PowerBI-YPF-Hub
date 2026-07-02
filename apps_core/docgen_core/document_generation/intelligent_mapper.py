"""
Intelligent Template Mapper
Maps extracted PBIP/TMDL metadata to Word template context
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IntelligentTemplateMapper:
    """
    Maps Power BI metadata to Word template variables.
    Generates context dictionary for docxtpl rendering.
    """

    def __init__(self, metadata: Any, user_inputs: Optional[Dict[str, Any]] = None):
        """
        Initialize mapper

        Args:
            metadata: Parsed Power BI metadata (from parser)
            user_inputs: Optional dictionary with user-provided fields
        """
        self.metadata = metadata
        self.user_inputs = user_inputs or {}
        self.logger = logging.getLogger(__name__)

    def generate_context(self) -> Dict[str, Any]:
        """
        Generate complete context for template rendering

        Returns:
            Dictionary with all template variables
        """
        self.logger.info("Generating template context from metadata")

        context = {
            # === PORTADA ===
            'nombre_tablero': self._get_report_name(),
            'fecha_generacion': datetime.now().strftime("%d/%m/%Y"),
            'hora_generacion': datetime.now().strftime("%H:%M:%S"),
            'version_documento': self.user_inputs.get('version', '1.0'),
            'autor_original': self._get_author(),

            # === VERSIÓN DEL DOCUMENTO ===
            'versiones': self._generate_version_table(),

            # === OBJETIVO (user input + generated) ===
            'objetivo': self._generate_objetivo(),

            # === ALCANCE (user input + detected) ===
            'alcance': self._generate_alcance(),

            # === USUARIOS ===
            'usuarios': self._generate_usuarios(),

            # === DEFINICIONES (KPIs/Medidas) ===
            'medidas_por_categoria': self._group_measures_by_folder(),
            'total_medidas': self._count_measures(),

            # === ORÍGENES ===
            'tablas_origenes': self._generate_data_sources(),
            'total_tablas': self._count_tables(),

            # === FILTROS ===
            'filtros_powerquery': self._detect_powerquery_filters(),
            'filtros_dax': self._detect_dax_filters(),

            # === FILTROS REPORTE (NEW) ===
            **self._collect_report_filters(),

            # === MODELO ER ===
            'relaciones': self._generate_relationships_table(),
            'estadisticas_modelo': self._generate_model_stats(),

            # === RLS ===
            'roles_rls': self._generate_rls_roles(),
            'tiene_rls': self._has_rls(),

            # === CONSIDERACIONES TÉCNICAS ===
            'frecuencia_actualizacion': self.user_inputs.get('frecuencia', 'No especificada'),
            'modo_conexion': self._detect_connection_mode(),

            # === POWER QUERY ===
            'power_queries': self._generate_power_queries(),

            # === ANEXO ===
            'columnas_por_tabla': self._generate_columns_list(),
            'jerarquias': self._generate_hierarchies(),
            'columnas_calculadas': self._get_calculated_columns(),

            # === METADATA GENERAL ===
            'generado_con': 'Power BI Documentation Generator v3.0',
            'generado_por': 'Claude + YPF IT Team',
        }

        self.logger.info(f"Context generated with {len(context)} variables")
        return context

    # === PORTADA ===

    def _get_report_name(self) -> str:
        """Get report name from metadata or user input"""
        # Priority 1: User provided title
        if self.user_inputs.get('titulo_reporte'):
            return self.user_inputs['titulo_reporte']

        # Priority 2: Metadata
        if hasattr(self.metadata, 'report_name'):
            return self.metadata.report_name

        if isinstance(self.metadata, dict):
            return self.metadata.get('model', {}).get('name', 'Sin Nombre')

        return 'Power BI Report'

    def _get_author(self) -> str:
        """Get author from metadata or user input"""
        if self.user_inputs.get('autor'):
            return self.user_inputs['autor']

        if hasattr(self.metadata, 'author'):
            return self.metadata.author

        return 'No especificado'

    # === VERSIÓN DEL DOCUMENTO ===

    def _generate_version_table(self) -> List[Dict[str, str]]:
        """Generate version history table"""
        return [{
            'version': self.user_inputs.get('version', '1.0'),
            'fecha': datetime.now().strftime("%d/%m/%Y"),
            'autor': self.user_inputs.get('autor', 'Generación automática'),
            'observaciones': self.user_inputs.get('observaciones', 'Generación inicial de documentación técnica')
        }]

    # === OBJETIVO ===

    def _generate_objetivo(self) -> str:
        """Generate objective section with intelligent context detection"""
        # Priority: user input
        if self.user_inputs.get('objetivo'):
            return self.user_inputs['objetivo']

        # Generate automatic objective with context analysis
        report_name = self._get_report_name()
        tables = self._get_tables_list()
        measures_count = self._count_measures()

        # Detect business context from table names
        business_context = self._detect_business_context(tables)

        # Detect main KPIs from measure names
        main_kpis = self._detect_main_kpis()

        # Detect report domain
        domain = self._detect_report_domain(tables, main_kpis)

        # Build specific objective based on detected context
        if domain and main_kpis:
            # Generate specific, context-aware objective
            kpi_list = ', '.join([f"[{kpi}]" for kpi in main_kpis[:5]])

            objetivo = f"""Este reporte tiene como objetivo analizar {domain}, proporcionando métricas clave como {kpi_list}."""

            if business_context:
                objetivo += f" El análisis permite {business_context} y apoyar la toma de decisiones estratégicas."
            else:
                objetivo += f" El análisis permite monitorear el desempeño y apoyar la toma de decisiones del área correspondiente."

            if measures_count > 5:
                objetivo += f" El reporte incluye {measures_count} medidas calculadas que facilitan el análisis detallado de los indicadores."
        else:
            # Fallback to generic objective
            table_names = []
            for t in tables[:3]:
                if isinstance(t, dict):
                    table_names.append(t.get('name', 'Unknown'))
                else:
                    table_names.append(getattr(t, 'name', 'Unknown'))

            objetivo = f"""Este reporte de Power BI '{report_name}' tiene como objetivo proporcionar análisis y visualización de datos provenientes de {len(tables)} tablas del modelo."""

            if measures_count > 0:
                objetivo += f" El reporte incluye {measures_count} medidas calculadas que permiten el análisis detallado de KPIs y métricas de negocio."

        return objetivo

    def _detect_business_context(self, tables: List) -> str:
        """Detect business context from table names"""
        # Keywords for different business contexts
        contexts = {
            'ventas': ['venta', 'sale', 'factura', 'invoice', 'pedido', 'order'],
            'inventario': ['inventario', 'inventory', 'stock', 'producto', 'product', 'articulo'],
            'clientes': ['cliente', 'customer', 'consumidor', 'comprador'],
            'finanzas': ['financiero', 'finance', 'contable', 'accounting', 'presupuesto', 'budget'],
            'recursos_humanos': ['empleado', 'employee', 'personal', 'staff', 'nomina', 'payroll'],
            'operaciones': ['operacion', 'operation', 'proceso', 'process', 'produccion', 'production']
        }

        detected = set()
        for table in tables:
            name = table.get('name', '') if isinstance(table, dict) else getattr(table, 'name', '')
            name_lower = name.lower()

            for context_key, keywords in contexts.items():
                if any(kw in name_lower for kw in keywords):
                    detected.add(context_key)

        # Generate description based on detected contexts
        descriptions = {
            'ventas': 'identificar tendencias comerciales',
            'inventario': 'optimizar la gestión de stock',
            'clientes': 'analizar el comportamiento y satisfacción de clientes',
            'finanzas': 'monitorear la salud financiera',
            'recursos_humanos': 'evaluar el desempeño del personal',
            'operaciones': 'optimizar procesos operativos'
        }

        if detected:
            return ', '.join([descriptions.get(ctx, '') for ctx in detected if descriptions.get(ctx)])
        return ''

    def _detect_main_kpis(self) -> List[str]:
        """Detect main KPIs from measure names"""
        measures = self._get_measures_list()

        # Common KPI patterns
        kpi_patterns = {
            'ventas': ['venta', 'sale', 'revenue', 'ingreso'],
            'margen': ['margen', 'margin', 'profit', 'beneficio', 'ganancia'],
            'cantidad': ['cantidad', 'qty', 'quantity', 'volumen', 'volume'],
            'costo': ['costo', 'cost', 'gasto', 'expense'],
            'cliente': ['cliente', 'customer'],
            'tasa': ['tasa', 'rate', 'ratio', 'porcentaje', 'percentage', '%']
        }

        detected_kpis = []
        for measure in measures[:20]:  # Check first 20 measures
            name = measure.get('name', '')
            name_lower = name.lower()

            # Look for common KPI keywords in measure names
            for kpi_type, patterns in kpi_patterns.items():
                if any(pattern in name_lower for pattern in patterns):
                    detected_kpis.append(name)
                    break

        # Return unique KPIs, limit to 5
        unique_kpis = list(dict.fromkeys(detected_kpis))[:5]
        return unique_kpis

    def _detect_report_domain(self, tables: List, kpis: List[str]) -> str:
        """Detect overall report domain"""
        # Analyze table names and KPIs to determine domain
        all_text = ' '.join([
            t.get('name', '') if isinstance(t, dict) else getattr(t, 'name', '')
            for t in tables
        ] + kpis).lower()

        domains = {
            'el desempeño de ventas y la gestión comercial': ['venta', 'sale', 'cliente', 'customer', 'factura', 'invoice', 'pedido'],
            'la gestión financiera y presupuestaria': ['financiero', 'finance', 'presupuesto', 'budget', 'contable', 'costo'],
            'las operaciones y la producción': ['operacion', 'operation', 'produccion', 'production', 'proceso', 'manufactura'],
            'la gestión de inventario y stock': ['inventario', 'inventory', 'stock', 'producto', 'articulo', 'almacen'],
            'los recursos humanos y personal': ['empleado', 'employee', 'personal', 'staff', 'nomina', 'payroll'],
            'el análisis de datos y métricas de negocio': []  # Default fallback
        }

        for domain, keywords in domains.items():
            if keywords and any(kw in all_text for kw in keywords):
                return domain

        # Default
        return 'el análisis de datos y métricas de negocio'

    # === ALCANCE ===

    def _generate_alcance(self) -> str:
        """Generate scope section"""
        # Priority: user input
        if self.user_inputs.get('alcance'):
            return self.user_inputs['alcance']

        # Detect date ranges and scope
        date_tables = self._detect_date_tables()
        tables = self._get_tables_list()

        alcance = f"El análisis incluye datos de {len(tables)} tablas del modelo."

        if date_tables:
            alcance += f" La dimensión temporal está gestionada por la tabla '{date_tables[0]}'."

        return alcance

    # === USUARIOS ===

    def _generate_usuarios(self) -> str:
        """Generate users section"""
        usuarios = []

        if self.user_inputs.get('administrador'):
            usuarios.append(f"**Administrador:** {self.user_inputs['administrador']}")

        if self.user_inputs.get('solicitante'):
            usuarios.append(f"**Solicitado por:** {self.user_inputs['solicitante']}")

        if not usuarios:
            return "No especificado - Favor completar manualmente"

        return '\n'.join(usuarios)

    # === DEFINICIONES (MEDIDAS) ===

    def _group_measures_by_folder(self) -> List[Dict[str, Any]]:
        """Group measures by display folder"""
        measures = self._get_measures_list()

        folders = {}
        for measure in measures:
            folder = measure.get('display_folder', 'General')
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(measure)

        # Convert to list format for template
        result = []
        for folder_name, folder_measures in folders.items():
            result.append({
                'categoria': folder_name,
                'medidas': [
                    {
                        'nombre': m.get('name', 'Sin nombre'),
                        'tabla': m.get('table', ''),
                        'formula': m.get('expression', ''),
                        'formato': m.get('format_string', ''),
                        'descripcion': m.get('description', '')
                    }
                    for m in folder_measures
                ]
            })

        return result

    def _count_measures(self) -> int:
        """Count total measures"""
        return len(self._get_measures_list())

    def _get_measures_list(self) -> List[Dict]:
        """Get list of ALL measures from ALL tables"""
        if isinstance(self.metadata, dict):
            tables = self.metadata.get('tables', [])
            measures = []
            logger.info(f"Extracting measures from {len(tables)} tables")

            for table in tables:
                table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')

                if isinstance(table, dict):
                    table_measures = table.get('measures', [])
                    if table_measures:
                        logger.info(f"Table '{table_name}': {len(table_measures)} measures")
                    measures.extend(table_measures)
                elif hasattr(table, 'measures'):
                    table_measures = table.measures
                    if table_measures:
                        logger.info(f"Table '{table_name}': {len(table_measures)} measures")
                    measures.extend([self._dataclass_to_dict(m) for m in table_measures])

            logger.info(f"TOTAL MEASURES EXTRACTED: {len(measures)}")
            return measures

        if hasattr(self.metadata, 'measures'):
            measures = [self._dataclass_to_dict(m) for m in self.metadata.measures]
            logger.info(f"TOTAL MEASURES EXTRACTED (from metadata.measures): {len(measures)}")
            return measures

        logger.warning("NO MEASURES FOUND IN METADATA")
        return []

    # === ORÍGENES ===

    def _generate_data_sources(self) -> List[Dict[str, Any]]:
        """Generate data sources information"""
        tables = self._get_tables_list()
        sources = []

        for table in tables:
            table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')

            # Skip LocalDateTable (auto date/time)
            if 'LocalDateTable' in table_name:
                continue

            source_info = {
                'tabla': table_name,
                'tipo_fuente': self._detect_source_type(table),
                'modo': self._get_partition_mode(table),
                'query_m': self._extract_m_query(table),
                'es_calculada': self._is_calculated_table(table),
                'es_autodatetime': 'LocalDateTable' in table_name
            }
            sources.append(source_info)

        return sources

    def _detect_source_type(self, table) -> str:
        """Detect data source type"""
        partitions = self._get_table_partitions(table)

        if not partitions:
            return 'Desconocido'

        # Check if calculated
        if any(p.get('source', {}).get('type') == 'calculated' for p in partitions):
            return 'Tabla Calculada (DAX)'

        # Try to detect from M query
        query = self._extract_m_query(table)
        if query:
            query_lower = query.lower()
            if 'sql.database' in query_lower:
                return 'SQL Server'
            elif 'excel.workbook' in query_lower:
                return 'Excel'
            elif 'sharepoint' in query_lower:
                return 'SharePoint'
            elif 'web.contents' in query_lower:
                return 'Web'
            elif 'odbc' in query_lower:
                return 'ODBC'

        return 'Import'

    def _get_partition_mode(self, table) -> str:
        """Get partition connection mode"""
        partitions = self._get_table_partitions(table)
        if partitions and len(partitions) > 0:
            return partitions[0].get('mode', 'import').capitalize()
        return 'Import'

    def _extract_m_query(self, table) -> str:
        """Extract Power Query M expression"""
        partitions = self._get_table_partitions(table)

        for partition in partitions:
            source = partition.get('source', {})
            if source.get('type') == 'query' and source.get('expression'):
                return source['expression']
            if source.get('type') == 'calculated' and source.get('expression'):
                return f"// Calculated table\n{source['expression']}"

        return ''

    def _is_calculated_table(self, table) -> bool:
        """Check if table is calculated"""
        partitions = self._get_table_partitions(table)
        return any(p.get('source', {}).get('type') == 'calculated' for p in partitions)

    # === FILTROS ===

    def _detect_powerquery_filters(self) -> List[Dict[str, str]]:
        """Detect Power Query filters - ENHANCED VERSION"""
        filters = []
        tables = self._get_tables_list()

        logger.info(f"Detecting filters in {len(tables)} tables")

        for table in tables:
            table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')

            # Skip LocalDateTable
            if 'LocalDateTable' in table_name:
                continue

            query = self._extract_m_query(table)

            if query:
                logger.info(f"Found query for table {table_name}: {len(query)} chars")
                query_lower = query.lower()
                filter_operations = []

                # Filter operations
                if 'table.selectrows' in query_lower:
                    filter_operations.append('Filtrado de filas')
                if 'table.selectcolumns' in query_lower:
                    filter_operations.append('Selección de columnas')
                if 'table.removecolumns' in query_lower:
                    filter_operations.append('Eliminación de columnas')
                if 'table.removerows' in query_lower:
                    filter_operations.append('Eliminación de filas')
                if 'table.distinct' in query_lower:
                    filter_operations.append('Valores únicos')
                if 'table.firstn' in query_lower or 'table.lastn' in query_lower:
                    filter_operations.append('Límite de filas')

                # Transformation operations
                if 'table.transformcolumntypes' in query_lower:
                    filter_operations.append('Transformación de tipos')
                if 'table.renamecolumns' in query_lower:
                    filter_operations.append('Renombrado')
                if 'table.replacevalue' in query_lower:
                    filter_operations.append('Reemplazo de valores')
                if 'table.join' in query_lower or 'table.nestedjoin' in query_lower:
                    filter_operations.append('Join')
                if 'table.group' in query_lower:
                    filter_operations.append('Agrupación')
                if 'table.pivot' in query_lower:
                    filter_operations.append('Pivoteo')
                if 'table.unpivot' in query_lower:
                    filter_operations.append('Unpivot')
                if 'table.sort' in query_lower:
                    filter_operations.append('Ordenamiento')

                # Date operations
                if 'date.year' in query_lower or 'date.month' in query_lower or 'date.day' in query_lower:
                    filter_operations.append('Operaciones de fecha')

                # ANY table operation is a transformation
                if 'table.' in query_lower and not filter_operations:
                    # Count how many Table. operations there are
                    table_ops_count = query_lower.count('table.')
                    if table_ops_count > 0:
                        filter_operations.append(f'{table_ops_count} transformación(es) Power Query')

                if filter_operations:
                    logger.info(f"Table {table_name}: {len(filter_operations)} operations detected")
                    filters.append({
                        'tabla': table_name,
                        'descripcion': f"Operaciones: {', '.join(filter_operations[:3])}" + (f" (+{len(filter_operations) - 3})" if len(filter_operations) > 3 else "")
                    })
            else:
                # No query found - might be direct query or calculated table
                if self._is_calculated_table(table):
                    logger.info(f"Table {table_name}: calculated table (DAX)")
                else:
                    logger.info(f"Table {table_name}: no M query found (direct query?)")

        logger.info(f"Total filters detected: {len(filters)}")
        return filters

    def _detect_dax_filters(self) -> List[Dict[str, str]]:
        """Detect DAX filters in calculated tables"""
        filters = []
        tables = self._get_tables_list()

        for table in tables:
            if self._is_calculated_table(table):
                expr = self._extract_m_query(table)
                if expr and ('filter(' in expr.lower() or 'calculatetable(' in expr.lower()):
                    table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')
                    filters.append({
                        'tabla': table_name,
                        'descripcion': f'Filtros DAX aplicados en tabla calculada'
                    })

        return filters

    def _collect_report_filters(self) -> Dict[str, Any]:
        """Collect all report-level filters (NEW METHOD)"""
        report_filters = []
        page_filters = []
        slicers = []

        # Check if metadata has layout with filters
        if not hasattr(self.metadata, 'layout'):
            logger.info("No layout found in metadata - no report filters")
            return {
                'filtros_reporte': report_filters,
                'filtros_pagina': page_filters,
                'slicers': slicers
            }

        layout = self.metadata.layout

        # 1. Report-level filters
        if hasattr(layout, 'report_filters') and layout.report_filters:
            logger.info(f"Found {len(layout.report_filters)} report-level filters")
            for f in layout.report_filters:
                filter_dict = self._filter_to_dict(f)
                if filter_dict:
                    filter_dict['scope'] = 'Report'
                    report_filters.append(filter_dict)

        # 2. Page-level filters
        if hasattr(layout, 'pages'):
            for page in layout.pages:
                page_name = page.display_name if hasattr(page, 'display_name') else page.name

                # Page filters
                if hasattr(page, 'filters') and page.filters:
                    logger.info(f"Found {len(page.filters)} filters on page '{page_name}'")
                    for f in page.filters:
                        filter_dict = self._filter_to_dict(f)
                        if filter_dict:
                            filter_dict['scope'] = f'Page: {page_name}'
                            page_filters.append(filter_dict)

                # 3. Slicers (from visuals)
                if hasattr(page, 'visuals'):
                    for visual in page.visuals:
                        if hasattr(visual, 'is_slicer') and visual.is_slicer:
                            slicer_info = {
                                'page': page_name,
                                'type': 'Slicer'
                            }

                            # Extract slicer field info
                            if hasattr(visual, 'slicer_config') and visual.slicer_config:
                                config = visual.slicer_config
                                if isinstance(config, dict):
                                    table = config.get('table', 'Unknown')
                                    column = config.get('column', 'Unknown')
                                    slicer_info['field'] = f"{table}.{column}"
                                    slicer_info['type'] = config.get('mode', 'Basic')
                                else:
                                    slicer_info['field'] = 'Unknown field'
                            else:
                                # Try to extract from fields_used
                                if hasattr(visual, 'fields_used') and visual.fields_used:
                                    slicer_info['field'] = visual.fields_used[0] if visual.fields_used else 'Unknown'
                                else:
                                    slicer_info['field'] = 'Unknown field'

                            slicers.append(slicer_info)

        # 3. Visual-level filters (charts with filters, not slicers)
        visual_filters = []
        if hasattr(layout, 'pages'):
            for page in layout.pages:
                page_name = page.display_name if hasattr(page, 'display_name') else page.name

                # Visual filters (non-slicers)
                if hasattr(page, 'visuals'):
                    for visual in page.visuals:
                        # Skip slicers (already in slicers list)
                        if hasattr(visual, 'is_slicer') and visual.is_slicer:
                            continue

                        # Check if visual has filters
                        if hasattr(visual, 'filters') and visual.filters:
                            visual_type = visual.visual_type.value if hasattr(visual.visual_type, 'value') else str(visual.visual_type)

                            for f in visual.filters:
                                filter_dict = self._filter_to_dict(f)
                                if filter_dict:
                                    filter_dict['scope'] = f'Visual: {visual_type} ({page_name})'
                                    filter_dict['visual_name'] = visual.name
                                    visual_filters.append(filter_dict)

        logger.info(f"Collected: {len(report_filters)} report filters, {len(page_filters)} page filters, {len(slicers)} slicers, {len(visual_filters)} visual filters")

        return {
            'filtros_reporte': report_filters,
            'filtros_pagina': page_filters,
            'slicers': slicers,
            'filtros_visual': visual_filters
        }

    def _filter_to_dict(self, filter_obj) -> Optional[Dict[str, Any]]:
        """Convert Filter object to dictionary"""
        try:
            # Handle both dataclass and dict
            if isinstance(filter_obj, dict):
                return filter_obj

            # If it's a dataclass or object with to_dict method
            if hasattr(filter_obj, 'to_dict'):
                return filter_obj.to_dict()

            # Manual extraction
            if hasattr(filter_obj, 'field') and hasattr(filter_obj, 'expression'):
                field_str = str(filter_obj.field) if hasattr(filter_obj.field, '__str__') else 'Unknown'

                # Get expression text
                expr_text = ''
                if hasattr(filter_obj, 'expression_text'):
                    expr_text = filter_obj.expression_text
                elif hasattr(filter_obj.expression, 'to_readable_text'):
                    expr_text = filter_obj.expression.to_readable_text()

                # Get filter type
                filter_type = 'Unknown'
                if hasattr(filter_obj.expression, 'filter_type'):
                    ft = filter_obj.expression.filter_type
                    filter_type = ft.value if hasattr(ft, 'value') else str(ft)

                return {
                    'field': field_str,
                    'type': filter_type,
                    'expression': expr_text,
                    'scope': getattr(filter_obj, 'scope', 'Unknown')
                }

            return None

        except Exception as e:
            logger.warning(f"Could not convert filter to dict: {e}")
            return None

    # === MODELO ER ===

    def _generate_relationships_table(self) -> List[Dict[str, str]]:
        """Generate relationships table"""
        relationships = self._get_relationships_list()

        return [
            {
                'desde': f"{r.get('from_table', '')}.{r.get('from_column', '')}",
                'hacia': f"{r.get('to_table', '')}.{r.get('to_column', '')}",
                'cardinalidad': self._get_cardinality_display(r),
                'direccion': self._get_direction_symbol(r),
                'estado': 'Activa' if r.get('is_active', True) else 'Inactiva'
            }
            for r in relationships
        ]

    def _generate_model_stats(self) -> Dict[str, Any]:
        """Generate model statistics"""
        relationships = self._get_relationships_list()
        tables = self._get_tables_list()

        # Count tables excluding LocalDateTable
        real_tables = [t for t in tables if 'LocalDateTable' not in (t.get('name', '') if isinstance(t, dict) else getattr(t, 'name', ''))]
        auto_datetime_tables = [t for t in tables if 'LocalDateTable' in (t.get('name', '') if isinstance(t, dict) else getattr(t, 'name', ''))]

        bidirectional = sum(1 for r in relationships
                           if r.get('cross_filtering_behavior') == 'bothDirections')

        stats = {
            'total_tablas': len(real_tables),
            'total_relaciones': len(relationships),
            'relaciones_activas': sum(1 for r in relationships if r.get('is_active', True)),
            'relaciones_bidireccionales': bidirectional,
            'total_medidas': self._count_measures()
        }

        if auto_datetime_tables:
            stats['auto_datetime'] = f"Activado ({len(auto_datetime_tables)} tablas auto-generadas)"
        else:
            stats['auto_datetime'] = "Desactivado (recomendado)"

        return stats

    def _get_cardinality_display(self, relationship: Dict) -> str:
        """Get user-friendly cardinality"""
        card_map = {'one': '1', 'many': '*'}
        from_c = card_map.get(relationship.get('from_cardinality', 'many'), '*')
        to_c = card_map.get(relationship.get('to_cardinality', 'one'), '1')
        return f"{from_c}:{to_c}"

    def _get_direction_symbol(self, relationship: Dict) -> str:
        """Get filter direction symbol"""
        if relationship.get('cross_filtering_behavior') == 'bothDirections':
            return '↔'
        return '→'

    # === RLS ===

    def _generate_rls_roles(self) -> List[Dict[str, Any]]:
        """Generate RLS roles information"""
        roles = self._get_roles_list()

        return [
            {
                'nombre': r.get('name', 'Sin nombre'),
                'permisos': [
                    {
                        'tabla': p.get('table', ''),
                        'filtro': p.get('filter_expression', '')
                    }
                    for p in r.get('table_permissions', [])
                ],
                'descripcion': r.get('description', 'Sin descripción')
            }
            for r in roles
        ]

    def _has_rls(self) -> bool:
        """Check if model has RLS configured"""
        return len(self._get_roles_list()) > 0

    # === CONSIDERACIONES TÉCNICAS ===

    def _detect_connection_mode(self) -> str:
        """Detect primary connection mode"""
        tables = self._get_tables_list()
        modes = [self._get_partition_mode(t) for t in tables]

        if not modes:
            return 'Import'

        # Get most common mode
        from collections import Counter
        most_common = Counter(modes).most_common(1)[0][0]
        return most_common

    # === ANEXO ===

    def _generate_columns_list(self) -> List[Dict[str, Any]]:
        """Generate detailed columns list"""
        tables = self._get_tables_list()
        result = []

        for table in tables:
            table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')
            columns = self._get_table_columns(table)

            result.append({
                'tabla': table_name,
                'columnas': [
                    {
                        'nombre': c.get('name', ''),
                        'tipo': c.get('data_type', ''),
                        'calculada': bool(c.get('expression'))
                    }
                    for c in columns
                ]
            })

        return result

    def _generate_power_queries(self) -> List[Dict[str, Any]]:
        """Generate Power Query M expressions list from all tables"""
        queries = []
        tables = self._get_tables_list()

        for table in tables:
            table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')

            # Skip auto-generated date tables
            if 'LocalDateTable' in table_name or 'DateTableTemplate' in table_name:
                continue

            expression = self._extract_m_query(table)
            if expression and not expression.startswith('// Calculated table'):
                queries.append({
                    'tabla': table_name,
                    'expresion': expression,
                    'pasos': expression.count('\n') + 1,
                    'tipo_fuente': self._detect_source_type(table)
                })

        return queries

    def _generate_hierarchies(self) -> List[Dict[str, Any]]:
        """Generate hierarchies list"""
        tables = self._get_tables_list()
        hierarchies = []

        for table in tables:
            table_hierarchies = self._get_table_hierarchies(table)
            for h in table_hierarchies:
                hierarchies.append({
                    'nombre': h.get('name', ''),
                    'tabla': h.get('table', ''),
                    'niveles': h.get('levels', [])
                })

        return hierarchies

    def _get_calculated_columns(self) -> List[Dict[str, str]]:
        """Get all calculated columns"""
        tables = self._get_tables_list()
        calc_columns = []

        for table in tables:
            table_name = table.get('name', 'Unknown') if isinstance(table, dict) else getattr(table, 'name', 'Unknown')
            columns = self._get_table_columns(table)

            for col in columns:
                if col.get('expression'):
                    calc_columns.append({
                        'tabla': table_name,
                        'columna': col.get('name', ''),
                        'expresion': col.get('expression', '')
                    })

        return calc_columns

    # === HELPER METHODS ===

    def _get_tables_list(self) -> List:
        """Get list of tables from metadata"""
        if isinstance(self.metadata, dict):
            return self.metadata.get('tables', [])

        if hasattr(self.metadata, 'tables'):
            return self.metadata.tables

        return []

    def _get_relationships_list(self) -> List:
        """Get list of relationships"""
        if isinstance(self.metadata, dict):
            rels = self.metadata.get('relationships', [])
            return [self._dataclass_to_dict(r) if not isinstance(r, dict) else r for r in rels]

        if hasattr(self.metadata, 'relationships'):
            return [self._dataclass_to_dict(r) for r in self.metadata.relationships]

        return []

    def _get_roles_list(self) -> List:
        """Get list of RLS roles"""
        if isinstance(self.metadata, dict):
            roles = self.metadata.get('roles', [])
            return [self._dataclass_to_dict(r) if not isinstance(r, dict) else r for r in roles]

        if hasattr(self.metadata, 'security_roles'):
            return [self._dataclass_to_dict(r) for r in self.metadata.security_roles]

        return []

    def _count_tables(self) -> int:
        """Count total tables"""
        return len(self._get_tables_list())

    def _detect_date_tables(self) -> List[str]:
        """Detect date/calendar tables"""
        tables = self._get_tables_list()
        date_tables = []

        for table in tables:
            name = table.get('name', '') if isinstance(table, dict) else getattr(table, 'name', '')
            name_lower = name.lower()

            if any(kw in name_lower for kw in ['fecha', 'date', 'calendario', 'calendar', 'tiempo', 'time']):
                date_tables.append(name)

        return date_tables

    def _get_table_partitions(self, table) -> List[Dict]:
        """Get partitions from table"""
        if isinstance(table, dict):
            return table.get('partitions', [])
        if hasattr(table, 'partitions'):
            return [self._dataclass_to_dict(p) if not isinstance(p, dict) else p
                   for p in table.partitions]
        return []

    def _get_table_columns(self, table) -> List[Dict]:
        """Get columns from table"""
        if isinstance(table, dict):
            return table.get('columns', [])
        if hasattr(table, 'columns'):
            return [self._dataclass_to_dict(c) if not isinstance(c, dict) else c
                   for c in table.columns]
        return []

    def _get_table_hierarchies(self, table) -> List[Dict]:
        """Get hierarchies from table"""
        if isinstance(table, dict):
            return table.get('hierarchies', [])
        if hasattr(table, 'hierarchies'):
            return table.hierarchies
        return []

    def _dataclass_to_dict(self, obj) -> Dict:
        """Convert dataclass to dictionary"""
        if isinstance(obj, dict):
            return obj

        from dataclasses import is_dataclass, asdict
        if is_dataclass(obj):
            return asdict(obj)

        # Fallback: use __dict__
        if hasattr(obj, '__dict__'):
            return obj.__dict__

        return {}
