"""
DAX Description Generator
Genera descripciones de propósito de negocio para medidas DAX usando análisis heurístico
"""

from typing import Optional
import re


class DAXDescriptionGenerator:
    """Genera descripciones inteligentes de medidas DAX"""

    # Keywords en nombres de medidas
    MEASURE_PATTERNS = {
        'total': ['total', 'suma', 'sum'],
        'promedio': ['promedio', 'average', 'avg', 'medio'],
        'cantidad': ['cantidad', 'count', 'qty', 'numero', 'número'],
        'porcentaje': ['%', 'porcentaje', 'percentage', 'pct', 'tasa', 'rate', 'ratio'],
        'maximo': ['max', 'maximo', 'máximo', 'mayor'],
        'minimo': ['min', 'minimo', 'mínimo', 'menor'],
        'diferencia': ['diferencia', 'diff', 'variacion', 'variación', 'vs', 'delta'],
        'acumulado': ['acumulado', 'ytd', 'accumulated', 'running'],
        'periodo_anterior': ['anterior', 'previous', 'last', 'año pasado', 'mes pasado', 'py']
    }

    # Business domains from table names
    BUSINESS_DOMAINS = {
        'ventas': ['venta', 'sale', 'factura', 'invoice', 'revenue', 'ingreso'],
        'clientes': ['cliente', 'customer', 'comprador'],
        'productos': ['producto', 'product', 'articulo', 'artículo', 'item'],
        'costos': ['costo', 'cost', 'gasto', 'expense'],
        'inventario': ['inventario', 'inventory', 'stock'],
        'finanzas': ['financiero', 'finance', 'presupuesto', 'budget'],
        'personal': ['empleado', 'employee', 'personal', 'staff']
    }

    # DAX function purposes
    DAX_FUNCTIONS = {
        'SUM': 'suma',
        'SUMX': 'suma iterativa',
        'AVERAGE': 'promedio',
        'AVERAGEX': 'promedio iterativo',
        'COUNT': 'conteo',
        'COUNTX': 'conteo iterativo',
        'COUNTA': 'conteo de valores no vacíos',
        'COUNTROWS': 'conteo de filas',
        'DISTINCTCOUNT': 'conteo de valores únicos',
        'MIN': 'valor mínimo',
        'MAX': 'valor máximo',
        'DIVIDE': 'división segura',
        'CALCULATE': 'cálculo con filtros',
        'FILTER': 'filtrado',
        'ALL': 'ignora filtros',
        'ALLEXCEPT': 'ignora filtros excepto',
        'RANKX': 'ranking',
        'TOPN': 'top N valores'
    }

    # Time intelligence keywords
    TIME_INTELLIGENCE = {
        'SAMEPERIODLASTYEAR': 'mismo período del año anterior',
        'TOTALYTD': 'total acumulado del año',
        'DATESYTD': 'fechas hasta hoy del año',
        'PARALLELPERIOD': 'período paralelo',
        'DATEADD': 'agregar período de tiempo',
        'PREVIOUSMONTH': 'mes anterior',
        'PREVIOUSQUARTER': 'trimestre anterior',
        'PREVIOUSYEAR': 'año anterior'
    }

    def generate_description(self,
                            measure_name: str,
                            expression: str,
                            table_name: str = "",
                            existing_description: Optional[str] = None) -> str:
        """
        Genera descripción de propósito de negocio

        Args:
            measure_name: Nombre de la medida
            expression: Expresión DAX completa
            table_name: Tabla donde está la medida
            existing_description: Descripción existente del TMDL (si hay)

        Returns:
            Descripción de propósito de negocio
        """
        # Si ya tiene descripción, usarla
        if existing_description and existing_description.strip():
            return existing_description.strip()

        # Analyze measure name
        operation_type = self._detect_operation_type(measure_name)

        # Analyze DAX expression
        main_function = self._detect_main_function(expression)
        has_time_intelligence = self._has_time_intelligence(expression)
        has_filters = self._has_filters(expression)

        # Detect business domain
        domain = self._detect_domain(table_name, measure_name)

        # Generate description
        description = self._build_description(
            measure_name=measure_name,
            operation_type=operation_type,
            main_function=main_function,
            domain=domain,
            has_time_intelligence=has_time_intelligence,
            has_filters=has_filters,
            expression=expression
        )

        return description

    def _detect_operation_type(self, measure_name: str) -> str:
        """Detecta tipo de operación del nombre"""
        name_lower = measure_name.lower()

        for op_type, keywords in self.MEASURE_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                return op_type

        return 'calculo'  # default

    def _detect_main_function(self, expression: str) -> Optional[str]:
        """Detecta función DAX principal"""
        expr_upper = expression.upper()

        # Buscar funciones en orden de prioridad
        for func in ['CALCULATE', 'SUMX', 'AVERAGEX', 'COUNTX', 'DIVIDE',
                     'SUM', 'AVERAGE', 'COUNT', 'MIN', 'MAX']:
            if func in expr_upper:
                return func

        return None

    def _has_time_intelligence(self, expression: str) -> bool:
        """Detecta si usa inteligencia de tiempo"""
        expr_upper = expression.upper()
        return any(func in expr_upper for func in self.TIME_INTELLIGENCE.keys())

    def _has_filters(self, expression: str) -> bool:
        """Detecta si aplica filtros"""
        expr_upper = expression.upper()
        return 'CALCULATE' in expr_upper or 'FILTER' in expr_upper

    def _detect_domain(self, table_name: str, measure_name: str) -> str:
        """Detecta dominio de negocio"""
        text = f"{table_name} {measure_name}".lower()

        for domain, keywords in self.BUSINESS_DOMAINS.items():
            if any(kw in text for kw in keywords):
                return domain

        return 'general'

    def _build_description(self,
                          measure_name: str,
                          operation_type: str,
                          main_function: Optional[str],
                          domain: str,
                          has_time_intelligence: bool,
                          has_filters: bool,
                          expression: str) -> str:
        """Construye descripción final"""

        # Templates base por tipo de operación
        templates = {
            'total': "Calcula el total {domain_desc}",
            'promedio': "Calcula el promedio {domain_desc}",
            'cantidad': "Cuenta {domain_desc}",
            'porcentaje': "Calcula el porcentaje o tasa {domain_desc}",
            'maximo': "Encuentra el valor máximo {domain_desc}",
            'minimo': "Encuentra el valor mínimo {domain_desc}",
            'diferencia': "Calcula la diferencia o variación {domain_desc}",
            'acumulado': "Calcula el valor acumulado {domain_desc}",
            'periodo_anterior': "Compara con el período anterior {domain_desc}",
            'calculo': "Realiza un cálculo {domain_desc}"
        }

        # Domain descriptions
        domain_descriptions = {
            'ventas': 'de ventas o ingresos',
            'clientes': 'relacionado con clientes',
            'productos': 'de productos o artículos',
            'costos': 'de costos o gastos',
            'inventario': 'de inventario o stock',
            'finanzas': 'financiero o presupuestario',
            'personal': 'de personal o recursos humanos',
            'general': ''
        }

        # Base description
        template = templates.get(operation_type, templates['calculo'])
        domain_desc = domain_descriptions.get(domain, '')
        description = template.format(domain_desc=domain_desc)

        # Add function detail
        if main_function:
            func_desc = self.DAX_FUNCTIONS.get(main_function)
            if func_desc:
                description += f" utilizando {func_desc}"

        # Add context modifiers
        modifiers = []
        if has_time_intelligence:
            modifiers.append("aplica inteligencia de tiempo")
        if has_filters:
            modifiers.append("con filtros específicos de contexto")

        if modifiers:
            description += ". " + " y ".join(modifiers).capitalize()

        # Analyze for specific patterns
        expr_upper = expression.upper()

        # Detectar comparaciones año anterior
        if 'SAMEPERIODLASTYEAR' in expr_upper or 'PREVIOUSYEAR' in expr_upper:
            description += ". Compara con el mismo período del año anterior"

        # Detectar YTD
        if 'YTD' in expr_upper:
            description += ". Calcula el acumulado del año hasta la fecha"

        # Detectar división/ratios
        if 'DIVIDE' in expr_upper:
            description += ". Realiza división segura evitando errores por división entre cero"

        # Add final period
        if not description.endswith('.'):
            description += '.'

        return description
