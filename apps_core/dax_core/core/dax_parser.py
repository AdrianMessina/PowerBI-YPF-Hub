"""
Parser de código DAX
Extrae información estructural del código DAX
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

# Funciones comunes de DAX
DAX_FUNCTIONS = [
    'CALCULATE', 'FILTER', 'ALL', 'ALLSELECTED', 'ALLEXCEPT', 'VALUES', 'DISTINCT',
    'SUM', 'SUMX', 'AVERAGE', 'AVERAGEX', 'COUNT', 'COUNTX', 'COUNTA', 'COUNTAX',
    'MIN', 'MINX', 'MAX', 'MAXX', 'CONCATENATEX', 'RANKX',
    'EARLIER', 'EARLIEST', 'RELATED', 'RELATEDTABLE', 'USERELATIONSHIP',
    'IF', 'SWITCH', 'AND', 'OR', 'NOT', 'TRUE', 'FALSE',
    'BLANK', 'ISBLANK', 'IFERROR', 'ISERROR',
    'VAR', 'RETURN',
    'SUMMARIZE', 'SUMMARIZECOLUMNS', 'ADDCOLUMNS', 'SELECTCOLUMNS',
    'CROSSJOIN', 'GENERATE', 'GENERATEALL', 'NATURALINNERJOIN', 'NATURALLEFTOUTERJOIN',
    'KEEPFILTERS', 'REMOVEFILTERS', 'SELECTEDVALUE',
    'DIVIDE', 'FORMAT', 'CONCATENATE',
    'CALENDAR', 'CALENDARAUTO', 'DATE', 'DATEVALUE',
    'TOTALYTD', 'TOTALQTD', 'TOTALMTD', 'DATEADD', 'DATESYTD',
    'HASONEVALUE', 'HASONEFILTER', 'ISCROSSFILTERED', 'ISFILTERED',
    'LOOKUPVALUE', 'TREATAS', 'SUBSTITUTEWITHINDEX'
]

ITERATOR_FUNCTIONS = [
    'SUMX', 'AVERAGEX', 'COUNTX', 'COUNTAX', 'MINX', 'MAXX',
    'CONCATENATEX', 'RANKX', 'PRODUCTX', 'MEDIANX', 'PERCENTILX.INC', 'PERCENTILX.EXC'
]


@dataclass
class FunctionCall:
    """Representa una llamada a función en el código"""
    name: str
    line: int
    column: int
    nested: bool = False
    parent: Optional[str] = None


@dataclass
class Variable:
    """Representa una variable DAX"""
    name: str
    usage_count: int


@dataclass
class ParsedDaxExpression:
    """Expresión DAX parseada con toda su información estructural"""
    raw: str
    object_type: str  # 'measure', 'calculated-column', 'calculated-table'
    name: Optional[str] = None
    functions: List[FunctionCall] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    has_variables: bool = False
    variables: List[Variable] = field(default_factory=list)


def strip_dax_comments(code: str) -> str:
    """
    Elimina comentarios DAX del código antes del análisis.
    Soporta tres tipos de comentarios:
      -- line comment
      // line comment
      /* block comment */
    """
    # Paso 1: Eliminar block comments /* ... */ (pueden ser multilinea)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    # Paso 2: Eliminar line comments (-- y //)
    code = re.sub(r'--[^\n]*', '', code)
    code = re.sub(r'//[^\n]*', '', code)

    return code


def parse_dax_code(code: str) -> ParsedDaxExpression:
    """
    Parsea código DAX y extrae información estructural

    Args:
        code: Código DAX a parsear

    Returns:
        ParsedDaxExpression con toda la información extraída
    """
    trimmed_code = strip_dax_comments(code.strip())

    # Detectar tipo de objeto
    object_type = detect_object_type(trimmed_code)

    # Extraer nombre
    name = extract_name(trimmed_code, object_type)

    # Extraer variables
    variables = extract_variables(trimmed_code)

    # Extraer funciones con posición
    functions = extract_functions(trimmed_code)

    # Extraer referencias a tablas y columnas
    tables, columns = extract_table_column_references(trimmed_code)

    # Extraer referencias a medidas
    measures = extract_measure_references(trimmed_code)

    return ParsedDaxExpression(
        raw=code,
        object_type=object_type,
        name=name,
        functions=functions,
        tables=tables,
        columns=columns,
        measures=measures,
        has_variables=len(variables) > 0,
        variables=variables
    )


def detect_object_type(code: str) -> str:
    """Detecta si es medida, columna calculada o tabla calculada"""
    # Tabla calculada: generalmente empieza con nombre = FUNCION_TABLA
    table_pattern = re.compile(
        r'^\s*[\w\s]+\s*=\s*(FILTER|SUMMARIZE|ADDCOLUMNS|SELECTCOLUMNS|CROSSJOIN|CALENDAR|CALENDARAUTO|GENERATE|DISTINCT|VALUES|ALL)',
        re.IGNORECASE
    )

    # Columna calculada: usa EARLIER o RELATED
    column_indicators = re.compile(r'\b(EARLIER|EARLIEST|PATH|PATHITEM)\b', re.IGNORECASE)

    if table_pattern.search(code):
        return 'calculated-table'

    if column_indicators.search(code):
        return 'calculated-column'

    # Por defecto es medida (caso más común)
    return 'measure'


def extract_name(code: str, object_type: str) -> Optional[str]:
    """Extrae el nombre del objeto DAX"""
    # Patrón: Nombre = ...
    name_pattern = re.compile(r'^\s*(\[?[\w\s]+\]?)\s*=')
    match = name_pattern.search(code)
    if match:
        return match.group(1).strip().replace('[', '').replace(']', '')
    return None


def extract_variables(code: str) -> List[Variable]:
    """Extrae variables VAR del código"""
    var_pattern = re.compile(r'\bVAR\s+([\w_]+)\s*=', re.IGNORECASE)
    variables = {}

    # Encontrar todas las declaraciones VAR
    for match in var_pattern.finditer(code):
        var_name = match.group(1)
        variables[var_name] = 0

    # Contar usos (excluyendo la declaración)
    for var_name in variables.keys():
        usage_pattern = re.compile(rf'\b{var_name}\b', re.IGNORECASE)
        matches = usage_pattern.findall(code)
        # -1 porque no contamos la declaración
        variables[var_name] = max(0, len(matches) - 1)

    return [Variable(name=name, usage_count=count) for name, count in variables.items()]


def extract_functions(code: str) -> List[FunctionCall]:
    """Extrae todas las llamadas a funciones DAX"""
    functions = []
    lines = code.split('\n')

    for line_idx, line in enumerate(lines):
        for func_name in DAX_FUNCTIONS:
            pattern = re.compile(rf'\b{func_name}\s*\(', re.IGNORECASE)
            for match in pattern.finditer(line):
                functions.append(FunctionCall(
                    name=func_name.upper(),
                    line=line_idx + 1,
                    column=match.start(),
                    nested=False
                ))

    # Detectar iteradores anidados
    for func in functions:
        if func.name in ITERATOR_FUNCTIONS:
            func_line = lines[func.line - 1]
            after_func = func_line[func.column:]

            # Verificar si hay otro iterador dentro
            has_nested_iterator = any(
                iter_func in after_func.upper()
                for iter_func in ITERATOR_FUNCTIONS
            )

            if has_nested_iterator:
                func.nested = True

    return functions


def extract_table_column_references(code: str) -> Tuple[List[str], List[str]]:
    """Extrae referencias a tablas y columnas (Tabla[Columna])"""
    tables = set()
    columns = set()

    # Patrón para Tabla[Columna] o 'Tabla'[Columna]
    table_column_pattern = re.compile(r"['\"]?(\w+)['\"]?\[(\w+)\]")

    for match in table_column_pattern.finditer(code):
        tables.add(match.group(1))
        columns.add(f"{match.group(1)}[{match.group(2)}]")

    return list(tables), list(columns)


def extract_measure_references(code: str) -> List[str]:
    """Extrae referencias a medidas [Nombre Medida]"""
    measures = set()

    # Patrón para [Medida]
    measure_pattern = re.compile(r'\[([^\]]+)\]')

    for match in measure_pattern.finditer(code):
        # Excluir si es parte de Tabla[Columna]
        start = max(0, match.start() - 10)
        before_bracket = code[start:match.start()]
        if not re.search(r"['\"]?\w+['\"]?$", before_bracket):
            measures.add(match.group(1))

    return list(measures)


def calculate_complexity(parsed: ParsedDaxExpression) -> int:
    """
    Calcula un score de complejidad (0-100)

    Args:
        parsed: Expresión DAX parseada

    Returns:
        Score de complejidad entre 0 y 100
    """
    complexity = 0

    # Complejidad base por funciones
    complexity += len(parsed.functions) * 2

    # Iteradores anidados agregan complejidad significativa
    nested_iterators = sum(1 for f in parsed.functions if f.nested)
    complexity += nested_iterators * 15

    # CALCULATE agrega transición de contexto
    calculate_count = sum(1 for f in parsed.functions if f.name == 'CALCULATE')
    complexity += calculate_count * 5

    # Variables reducen complejidad
    complexity -= len(parsed.variables) * 3

    # Múltiples referencias a tablas agregan complejidad
    complexity += len(parsed.tables) * 2

    # Normalizar a 0-100
    return max(0, min(100, complexity))
