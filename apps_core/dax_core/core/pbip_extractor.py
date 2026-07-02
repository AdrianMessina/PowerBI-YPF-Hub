"""
Extractor de medidas DAX desde archivos PBIP
Soporta tanto archivos model.bim (JSON) como formato TMDL
"""

import json
import zipfile
import os
from typing import List, Dict, Optional
from pathlib import Path
import tempfile
import shutil


def extract_measures_from_pbip(file_path: str) -> List[Dict]:
    """
    Extrae todas las medidas DAX de un archivo/carpeta PBIP

    Args:
        file_path: Ruta al archivo PBIP (.pbip puede ser carpeta o ZIP)

    Returns:
        Lista de diccionarios con información de cada medida:
        {
            'name': str,
            'expression': str,
            'table': str,
            'description': str (opcional),
            'format': str (opcional)
        }
    """
    measures = []
    temp_dir = None
    cleanup_needed = False

    try:
        definition_path = None

        # Verificar si es un directorio o un archivo
        if os.path.isdir(file_path):
            # Es una carpeta, verificar si es .SemanticModel directamente o carpeta padre
            if file_path.endswith('.SemanticModel'):
                # Es la carpeta .SemanticModel directamente
                definition_path = os.path.join(file_path, 'definition')
            else:
                # Puede ser carpeta padre, buscar .SemanticModel
                definition_path = os.path.join(file_path, 'definition')

                # Si no existe, buscar carpetas .SemanticModel
                if not os.path.exists(definition_path):
                    parent_dir = file_path
                    for item in os.listdir(parent_dir):
                        if item.endswith('.SemanticModel'):
                            semantic_model_path = os.path.join(parent_dir, item)
                            definition_path = os.path.join(semantic_model_path, 'definition')
                            break
        else:
            # Es un archivo
            # Si es un archivo .pbip (JSON), buscar la carpeta .SemanticModel asociada
            if file_path.endswith('.pbip'):
                # Leer el archivo .pbip para obtener información
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        pbip_data = json.load(f)
                except:
                    raise ValueError("El archivo .pbip no es un JSON válido")

                # Obtener el nombre base del archivo (sin extensión)
                pbip_name = Path(file_path).stem
                parent_dir = os.path.dirname(file_path)

                # Buscar la carpeta .SemanticModel asociada
                semantic_model_name = f"{pbip_name}.SemanticModel"
                semantic_model_path = os.path.join(parent_dir, semantic_model_name)

                if os.path.exists(semantic_model_path):
                    definition_path = os.path.join(semantic_model_path, 'definition')
                else:
                    raise ValueError(f"No se encontró la carpeta '{semantic_model_name}' en el mismo directorio del archivo .pbip")
            else:
                # Intentar extraerlo como ZIP
                temp_dir = tempfile.mkdtemp()
                cleanup_needed = True

                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    # Buscar carpeta 'definition' recursivamente en el ZIP extraído
                    # Estructura típica: temp_dir/NombreProyecto.SemanticModel/definition/
                    definition_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        if 'definition' in dirs:
                            candidate = os.path.join(root, 'definition')
                            # Verificar que es la carpeta correcta (debe tener model.tmdl o database.tmdl)
                            if any(f.endswith('.tmdl') or f == 'model.bim'
                                   for f in os.listdir(candidate)):
                                definition_path = candidate
                                break

                    if not definition_path:
                        # Fallback: buscar directamente en raíz
                        definition_path = os.path.join(temp_dir, 'definition')

                except zipfile.BadZipFile:
                    raise ValueError("El archivo no es un ZIP válido ni un archivo .pbip. Si estás intentando cargar un PBIP, asegúrate de pegar la ruta al archivo .pbip o a la carpeta .SemanticModel")

        # Buscar carpeta definition si aún no la encontramos
        if not definition_path or not os.path.exists(definition_path):
            # Intentar buscar en subdirectorios
            found = False
            search_root = temp_dir if temp_dir else file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            for root, dirs, files in os.walk(search_root):
                if 'definition' in dirs:
                    definition_path = os.path.join(root, 'definition')
                    found = True
                    break

            if not found:
                raise ValueError("No se encontró la carpeta 'definition' en el archivo PBIP. Asegúrate de proporcionar la ruta al archivo .pbip o a la carpeta .SemanticModel que contiene los archivos del modelo.")

        # Verificar si existe model.bim (formato JSON)
        model_bim_path = os.path.join(definition_path, 'model.bim')
        if os.path.exists(model_bim_path):
            measures = parse_model_bim(model_bim_path)
        else:
            # Intentar con formato TMDL
            tmdl_path = os.path.join(definition_path, '.tmdl')
            if os.path.exists(tmdl_path):
                measures = parse_tmdl_files(tmdl_path)
            else:
                # Buscar archivos .tmdl directamente en definition
                measures = parse_tmdl_files(definition_path)

    finally:
        # Limpiar archivos temporales solo si se creó temp_dir
        if cleanup_needed and temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return measures


def parse_model_bim(file_path: str) -> List[Dict]:
    """
    Parsea archivo model.bim (formato JSON) y extrae medidas

    Args:
        file_path: Ruta al archivo model.bim

    Returns:
        Lista de medidas encontradas
    """
    measures = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)

        # Navegar por la estructura del model.bim
        # Estructura típica: model -> tables -> measures
        if 'model' in model_data:
            model = model_data['model']
        else:
            model = model_data

        # Obtener tablas
        tables = model.get('tables', [])

        for table in tables:
            table_name = table.get('name', 'Unknown Table')

            # Obtener medidas de la tabla
            table_measures = table.get('measures', [])

            for measure in table_measures:
                measure_info = {
                    'name': measure.get('name', 'Unnamed Measure'),
                    'expression': measure.get('expression', ''),
                    'table': table_name,
                    'description': measure.get('description', ''),
                    'format': measure.get('formatString', '')
                }

                # Solo agregar si tiene expresión
                if measure_info['expression']:
                    measures.append(measure_info)

    except Exception as e:
        print(f"Error al parsear model.bim: {e}")

    return measures


def parse_tmdl_files(tmdl_folder: str) -> List[Dict]:
    """
    Parsea archivos .tmdl (formato de texto) y extrae medidas

    Args:
        tmdl_folder: Carpeta que contiene archivos .tmdl

    Returns:
        Lista de medidas encontradas
    """
    measures = []

    try:
        # Buscar archivos .tmdl recursivamente
        tmdl_files = []
        for root, dirs, files in os.walk(tmdl_folder):
            for file in files:
                if file.endswith('.tmdl'):
                    tmdl_files.append(os.path.join(root, file))

        # Parsear cada archivo .tmdl
        for tmdl_file in tmdl_files:
            file_measures = parse_single_tmdl_file(tmdl_file)
            measures.extend(file_measures)

    except Exception as e:
        print(f"Error al parsear archivos TMDL: {e}")

    return measures


def parse_single_tmdl_file(file_path: str) -> List[Dict]:
    """
    Parsea un archivo .tmdl individual

    El formato TMDL tiene estructura como:
    measure 'Nombre de Medida' =
        CALCULATE(...)

    Args:
        file_path: Ruta al archivo .tmdl

    Returns:
        Lista de medidas en este archivo
    """
    measures = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Detectar tabla del nombre del archivo
        file_name = os.path.basename(file_path)
        table_name = file_name.replace('.tmdl', '').strip()

        # Patrón para detectar medidas en TMDL
        # Formato: measure 'Nombre' = <expresión>
        import re

        # Pattern para capturar medidas
        measure_pattern = re.compile(
            r"measure\s+'([^']+)'\s*=\s*((?:.*?\n)*?)(?=\n\s*(?:measure|column|table|$))",
            re.IGNORECASE | re.MULTILINE
        )

        for match in measure_pattern.finditer(content):
            measure_name = match.group(1)
            measure_expression = match.group(2).strip()

            # Limpiar la expresión (remover comentarios y líneas vacías)
            lines = measure_expression.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remover comentarios //
                if '//' in line:
                    line = line[:line.index('//')]
                line = line.strip()
                if line:
                    cleaned_lines.append(line)

            measure_expression = '\n'.join(cleaned_lines)

            if measure_expression:
                measures.append({
                    'name': measure_name,
                    'expression': measure_expression,
                    'table': table_name,
                    'description': '',
                    'format': ''
                })

    except Exception as e:
        print(f"Error al parsear {file_path}: {e}")

    return measures


def validate_pbip_file(file_path: str) -> tuple[bool, str]:
    """
    Valida que el archivo/carpeta sea un PBIP válido

    Args:
        file_path: Ruta al archivo o carpeta PBIP

    Returns:
        (es_valido, mensaje)
    """
    if not os.path.exists(file_path):
        return False, "El archivo o carpeta no existe"

    try:
        definition_path = None

        # Si es un archivo .pbip (JSON)
        if os.path.isfile(file_path) and file_path.endswith('.pbip'):
            # Leer el archivo .pbip
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    pbip_data = json.load(f)
            except:
                return False, "El archivo .pbip no es un JSON válido"

            # Buscar la carpeta .SemanticModel asociada
            pbip_name = Path(file_path).stem
            parent_dir = os.path.dirname(file_path)
            semantic_model_name = f"{pbip_name}.SemanticModel"
            semantic_model_path = os.path.join(parent_dir, semantic_model_name)

            if not os.path.exists(semantic_model_path):
                return False, f"No se encontró la carpeta '{semantic_model_name}' en el mismo directorio. Asegúrate de que la carpeta .SemanticModel esté presente."

            definition_path = os.path.join(semantic_model_path, 'definition')

        # Si es un directorio
        elif os.path.isdir(file_path):
            # Verificar si es .SemanticModel directamente
            if file_path.endswith('.SemanticModel'):
                definition_path = os.path.join(file_path, 'definition')
            else:
                # Puede ser carpeta padre, intentar buscar definition
                definition_path = os.path.join(file_path, 'definition')

                # Si no existe, buscar carpetas .SemanticModel
                if not os.path.exists(definition_path):
                    parent_dir = file_path
                    for item in os.listdir(parent_dir):
                        if item.endswith('.SemanticModel'):
                            semantic_model_path = os.path.join(parent_dir, item)
                            definition_path = os.path.join(semantic_model_path, 'definition')
                            break

        # Si es otro tipo de archivo (ZIP)
        elif os.path.isfile(file_path):
            # Verificar tamaño mínimo del archivo
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # < 1KB es sospechosamente pequeño
                return False, (
                    f"El archivo ZIP es demasiado pequeño ({file_size} bytes). "
                    "Un proyecto PBIP válido debe tener al menos varios KB. "
                    "Verifica que zipeaste correctamente la carpeta del proyecto."
                )

            # Intentar como ZIP
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()

                    if not file_list:
                        return False, "El archivo ZIP está vacío"

                    # Buscar carpeta definition (en cualquier nivel del path)
                    has_definition = any('/definition/' in f or f.endswith('/definition') or f.startswith('definition/')
                                         for f in file_list)

                    # Buscar archivos TMDL (más confiable)
                    has_tmdl = any(f.endswith('.tmdl') for f in file_list)
                    has_bim = any(f.endswith('model.bim') for f in file_list)

                    if not has_definition and not has_tmdl and not has_bim:
                        # Mostrar estructura del ZIP para debug
                        sample_files = file_list[:5]
                        return False, (
                            "El archivo ZIP no contiene una estructura PBIP válida.\n\n"
                            f"Contenido detectado ({len(file_list)} archivos):\n"
                            + "\n".join(f"  • {f}" for f in sample_files)
                            + ("\n  ..." if len(file_list) > 5 else "")
                            + "\n\nSe esperaba:\n"
                            "  • Una carpeta '.SemanticModel/definition/' con archivos .tmdl, o\n"
                            "  • Un archivo 'model.bim'"
                        )

                    return True, "Archivo ZIP válido"
            except zipfile.BadZipFile:
                return False, "El archivo no es un ZIP válido o está corrupto"
        else:
            return False, "La ruta debe ser un archivo .pbip, una carpeta .SemanticModel, o un archivo ZIP"

        # Verificar que existe definition
        if not definition_path or not os.path.exists(definition_path):
            return False, "No se encontró la carpeta 'definition' en la estructura del PBIP"

        # Verificar si tiene model.bim o archivos .tmdl
        model_bim = os.path.join(definition_path, 'model.bim')
        has_model = os.path.exists(model_bim)

        if not has_model:
            # Buscar archivos .tmdl
            has_tmdl = False
            for root, dirs, files in os.walk(definition_path):
                if any(f.endswith('.tmdl') for f in files):
                    has_tmdl = True
                    break

            if not has_tmdl:
                return False, "No se encontró model.bim ni archivos .tmdl en la carpeta 'definition'"

        return True, "PBIP válido"

    except zipfile.BadZipFile:
        return False, "El archivo no es un ZIP válido. Si estás intentando cargar un PBIP, usa la ruta al archivo .pbip o a la carpeta .SemanticModel."
    except Exception as e:
        return False, f"Error al validar: {str(e)}"


def get_pbip_info(file_path: str) -> Dict:
    """
    Obtiene información general del archivo/carpeta PBIP

    Args:
        file_path: Ruta al archivo o carpeta PBIP

    Returns:
        Diccionario con información del modelo
    """
    info = {
        'file_name': os.path.basename(file_path),
        'file_size': os.path.getsize(file_path) if os.path.isfile(file_path) else 0,
        'format': 'unknown',
        'tables_count': 0,
        'measures_count': 0
    }

    temp_dir = None
    cleanup_needed = False

    try:
        definition_path = None

        # Si es un archivo .pbip (JSON)
        if os.path.isfile(file_path) and file_path.endswith('.pbip'):
            # Buscar la carpeta .SemanticModel asociada
            pbip_name = Path(file_path).stem
            parent_dir = os.path.dirname(file_path)
            semantic_model_name = f"{pbip_name}.SemanticModel"
            semantic_model_path = os.path.join(parent_dir, semantic_model_name)

            if os.path.exists(semantic_model_path):
                definition_path = os.path.join(semantic_model_path, 'definition')
                # Actualizar el tamaño para reflejar el tamaño de la carpeta
                info['file_size'] = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, dirs, files in os.walk(semantic_model_path)
                    for f in files
                )

        # Si es un directorio
        elif os.path.isdir(file_path):
            # Verificar si es .SemanticModel directamente
            if file_path.endswith('.SemanticModel'):
                definition_path = os.path.join(file_path, 'definition')
                info['file_size'] = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, dirs, files in os.walk(file_path)
                    for f in files
                )
            else:
                definition_path = os.path.join(file_path, 'definition')

                # Si no existe, buscar carpetas .SemanticModel
                if not os.path.exists(definition_path):
                    parent_dir = file_path
                    for item in os.listdir(parent_dir):
                        if item.endswith('.SemanticModel'):
                            semantic_model_path = os.path.join(parent_dir, item)
                            definition_path = os.path.join(semantic_model_path, 'definition')
                            info['file_size'] = sum(
                                os.path.getsize(os.path.join(root, f))
                                for root, dirs, files in os.walk(semantic_model_path)
                                for f in files
                            )
                            break

        # Si es otro archivo (ZIP)
        elif os.path.isfile(file_path):
            # Es un archivo ZIP
            temp_dir = tempfile.mkdtemp()
            cleanup_needed = True
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Buscar 'definition' recursivamente
            # Estructura típica: temp_dir/NombreProyecto.SemanticModel/definition/
            definition_path = None
            for root, dirs, files in os.walk(temp_dir):
                if 'definition' in dirs:
                    candidate = os.path.join(root, 'definition')
                    if any(f.endswith('.tmdl') or f == 'model.bim'
                           for f in os.listdir(candidate)):
                        definition_path = candidate
                        break

            if not definition_path:
                definition_path = os.path.join(temp_dir, 'definition')

        # Detectar formato
        model_bim_path = os.path.join(definition_path, 'model.bim')
        if os.path.exists(model_bim_path):
            info['format'] = 'model.bim (JSON)'

            # Contar tablas y medidas
            with open(model_bim_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)

            if 'model' in model_data:
                model = model_data['model']
            else:
                model = model_data

            tables = model.get('tables', [])
            info['tables_count'] = len(tables)

            for table in tables:
                info['measures_count'] += len(table.get('measures', []))

        else:
            # Formato TMDL
            info['format'] = 'TMDL (Text)'

            tmdl_path = definition_path

            # Contar TABLAS reales (archivos en definition/tables/)
            tables_dir = os.path.join(definition_path, 'tables')
            if os.path.exists(tables_dir):
                # Solo contar .tmdl en la carpeta tables/, excluyendo tablas automáticas
                tmdl_table_files = [
                    f for f in os.listdir(tables_dir)
                    if f.endswith('.tmdl')
                    and not f.startswith('LocalDateTable_')
                    and not f.startswith('DateTableTemplate_')
                ]
                info['tables_count'] = len(tmdl_table_files)
            else:
                # Fallback: contar todos los .tmdl (estructura no estándar)
                tmdl_files = []
                for root, dirs, files in os.walk(tmdl_path):
                    for file in files:
                        if file.endswith('.tmdl'):
                            tmdl_files.append(os.path.join(root, file))
                info['tables_count'] = len(tmdl_files)

            # Contar medidas (parsear archivos)
            measures = parse_tmdl_files(tmdl_path)
            info['measures_count'] = len(measures)

    except Exception as e:
        info['error'] = str(e)

    finally:
        # Limpiar solo si se creó temp_dir
        if cleanup_needed and temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return info
