"""
Power BI Model Layout Organizer - Aplicación Web Interactiva
"""

import streamlit as st
import os
import zipfile
import json
import sys
import tempfile
from pathlib import Path

# Importar el módulo principal
import pbix_layout_tool as layout_tool

st.set_page_config(
    page_title="Power BI Layout Organizer",
    page_icon="📊",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF6B6B;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">📊 Power BI Model Layout Organizer</div>', unsafe_allow_html=True)
st.markdown("**Organiza automáticamente los diagramas de modelo de Power BI**")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Organizar Layout", "🔍 Extraer Relaciones", "📊 Análisis", "ℹ️ Ayuda"])

# =============================================================================
# TAB 1: ORGANIZAR LAYOUT
# =============================================================================
with tab1:
    st.header("Organizar Layout de Modelo")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("1. Cargar Archivo PBIX")
        uploaded_pbix = st.file_uploader(
            "Selecciona tu archivo .pbix",
            type=['pbix'],
            help="El archivo Power BI Desktop que deseas organizar"
        )

        if uploaded_pbix:
            st.success(f"✓ Archivo cargado: {uploaded_pbix.name}")

    with col2:
        st.subheader("2. Configuración")

        fact_prefixes = st.text_input(
            "Prefijos de Tablas de Hechos",
            value="fct_,fact_,FCT_,FACT_",
            help="Separados por coma"
        )

        dim_prefixes = st.text_input(
            "Prefijos de Dimensiones",
            value="dim_,DIM_,Dim_,d_,D_",
            help="Separados por coma"
        )

        radius = st.slider(
            "Radio del Layout Estrella",
            min_value=300,
            max_value=1000,
            value=520,
            step=20,
            help="Distancia desde el fact a las dimensiones"
        )

        create_tabs = st.checkbox(
            "Crear Tabs Focalizados",
            value=False,
            help="Genera una pestaña por cada tabla de hechos"
        )

    st.subheader("3. Cargar Relaciones (Opcional)")

    col3, col4 = st.columns(2)

    with col3:
        uploaded_relations = st.file_uploader(
            "Archivo relations.json",
            type=['json'],
            help="Archivo JSON con las relaciones del modelo"
        )

        if uploaded_relations:
            try:
                relations_data = json.load(uploaded_relations)
                st.success(f"✓ {len(relations_data)} relaciones cargadas")

                with st.expander("Ver Relaciones"):
                    st.json(relations_data)
            except Exception as e:
                st.error(f"Error al leer relations.json: {str(e)}")

    with col4:
        st.info("""
        **Sin archivo de relaciones:**
        - Se usará un layout radial simple
        - No habrá detección de snowflake

        **Con archivo de relaciones:**
        - Layout optimizado por tipo (Star/Grid)
        - Soporte para dimensiones snowflake
        """)

    st.markdown("---")

    # Botón para procesar
    if st.button("🚀 Organizar Layout", type="primary", use_container_width=True):
        if not uploaded_pbix:
            st.error("⚠️ Por favor carga un archivo PBIX primero")
        else:
            with st.spinner("Procesando archivo..."):
                try:
                    # Crear archivos temporales
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Guardar PBIX
                        pbix_path = os.path.join(temp_dir, "input.pbix")
                        with open(pbix_path, 'wb') as f:
                            f.write(uploaded_pbix.getbuffer())

                        # Guardar relations si existe
                        relations_path = None
                        if uploaded_relations:
                            relations_path = os.path.join(temp_dir, "relations.json")
                            with open(relations_path, 'w') as f:
                                json.dump(relations_data, f)

                        output_path = os.path.join(temp_dir, "output_arranged.pbix")

                        # Leer DiagramLayout
                        layout = layout_tool.read_diagram_layout(pbix_path)

                        if layout is None:
                            st.error("❌ No se encontró DiagramLayout. Abre el archivo en Power BI Desktop primero.")
                        else:
                            # Extraer tablas
                            table_names = layout_tool.extract_table_names(layout)

                            if not table_names:
                                st.error("❌ No se encontraron tablas en el modelo.")
                            else:
                                # Clasificar tablas
                                fact_prefixes_list = fact_prefixes.split(',')
                                dim_prefixes_list = dim_prefixes.split(',')

                                fact_tables, dim_tables, other_tables = layout_tool.classify_tables(
                                    table_names, fact_prefixes_list, dim_prefixes_list
                                )

                                # Mostrar clasificación
                                st.markdown("### 📋 Clasificación de Tablas")

                                col_f, col_d, col_o = st.columns(3)

                                with col_f:
                                    st.metric("Tablas de Hechos", len(fact_tables))
                                    if fact_tables:
                                        with st.expander("Ver Hechos"):
                                            for f in fact_tables:
                                                st.write(f"- {f}")

                                with col_d:
                                    st.metric("Dimensiones", len(dim_tables))
                                    if dim_tables:
                                        with st.expander("Ver Dimensiones"):
                                            for d in dim_tables:
                                                st.write(f"- {d}")

                                with col_o:
                                    st.metric("Otras Tablas", len(other_tables))
                                    if other_tables:
                                        with st.expander("Ver Otras"):
                                            for o in other_tables:
                                                st.write(f"- {o}")

                                # Cargar relaciones
                                fact_to_dims = {}
                                snowflake = {}
                                orphan_dims = set(dim_tables)

                                if relations_path:
                                    relations = layout_tool.parse_relations(relations_path)
                                    fact_to_dims, snowflake, orphan_dims = layout_tool.build_adjacency(
                                        relations, fact_tables, dim_tables
                                    )

                                    st.markdown("### 🔗 Análisis de Relaciones")

                                    col_r1, col_r2, col_r3 = st.columns(3)

                                    with col_r1:
                                        st.metric("Links Fact→Dim", sum(len(v) for v in fact_to_dims.values()))

                                    with col_r2:
                                        st.metric("Links Snowflake", sum(len(v) for v in snowflake.values()))

                                    with col_r3:
                                        st.metric("Dims Huérfanas", len(orphan_dims))

                                # Calcular layout
                                node_sizes = layout_tool.extract_node_sizes(layout)
                                positions = layout_tool.compute_layout(
                                    fact_tables, dim_tables, other_tables,
                                    fact_to_dims, snowflake, orphan_dims,
                                    radius=radius,
                                    table_width=250,
                                    table_height=200,
                                    node_sizes=node_sizes
                                )

                                # Aplicar posiciones
                                from copy import deepcopy
                                modified_layout = layout_tool.apply_positions(
                                    deepcopy(layout), positions, 250, 200
                                )

                                # Crear tabs si se solicitó
                                if create_tabs and fact_tables:
                                    modified_layout = layout_tool.create_diagram_tabs(
                                        modified_layout, fact_tables, fact_to_dims, snowflake,
                                        radius=radius,
                                        table_width=250,
                                        table_height=200,
                                        node_sizes=node_sizes
                                    )
                                    st.success(f"✓ Creados {len(modified_layout['diagrams'])} diagramas (1 master + {len(fact_tables)} por fact)")

                                # Guardar
                                new_json_bytes = json.dumps(modified_layout, indent=2, ensure_ascii=False).encode("utf-16-le")
                                layout_tool.repack_pbix(pbix_path, output_path, {layout_tool.DIAGRAM_LAYOUT_PATH: new_json_bytes})

                                # Leer archivo de salida
                                with open(output_path, 'rb') as f:
                                    output_data = f.read()

                                st.markdown("### ✅ Layout Organizado Exitosamente")

                                # Botón de descarga
                                output_filename = uploaded_pbix.name.replace('.pbix', '_arranged.pbix')
                                st.download_button(
                                    label="⬇️ Descargar PBIX Organizado",
                                    data=output_data,
                                    file_name=output_filename,
                                    mime="application/octet-stream",
                                    type="primary"
                                )

                                st.success("🎉 Descarga el archivo y ábrelo en Power BI Desktop para ver el layout organizado!")

                except Exception as e:
                    st.error(f"❌ Error al procesar: {str(e)}")
                    st.exception(e)

# =============================================================================
# TAB 2: EXTRAER RELACIONES
# =============================================================================
with tab2:
    st.header("Extraer Relaciones desde .pbit")

    st.info("""
    **¿Qué es un archivo .pbit?**

    Un archivo .pbit (Power BI Template) es un archivo ZIP que contiene el esquema del modelo
    en formato legible (DataModelSchema). Este esquema incluye todas las relaciones del modelo.

    **Cómo crear un .pbit:**
    1. Abre tu modelo en Power BI Desktop
    2. Ve a: **Archivo → Guardar Como → Plantilla de Power BI (.pbit)**
    3. Sube el archivo aquí para extraer las relaciones
    """)

    uploaded_pbit = st.file_uploader(
        "Selecciona tu archivo .pbit",
        type=['pbit'],
        help="Power BI Template file"
    )

    if uploaded_pbit:
        st.success(f"✓ Archivo cargado: {uploaded_pbit.name}")

        if st.button("🔍 Extraer Relaciones", type="primary"):
            with st.spinner("Extrayendo relaciones..."):
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Guardar PBIT
                        pbit_path = os.path.join(temp_dir, "template.pbit")
                        with open(pbit_path, 'wb') as f:
                            f.write(uploaded_pbit.getbuffer())

                        # Extraer relaciones
                        with zipfile.ZipFile(pbit_path, 'r') as zf:
                            schema_file = None
                            for name in zf.namelist():
                                if "DataModelSchema" in name:
                                    schema_file = name
                                    break

                            if schema_file is None:
                                st.error("❌ No se encontró DataModelSchema en el .pbit")
                            else:
                                raw = zf.read(schema_file)

                                # Intentar decodificar
                                schema = None

                                # Estrategia 1: UTF-16-LE
                                try:
                                    text = raw.decode('utf-16-le')
                                    brace = text.find('{')
                                    if brace != -1:
                                        schema = json.loads(text[brace:])
                                except:
                                    pass

                                # Estrategia 2: UTF-8
                                if schema is None:
                                    try:
                                        brace = raw.find(b'{')
                                        if brace != -1:
                                            schema = json.loads(raw[brace:].decode('utf-8'))
                                    except:
                                        pass

                                if schema is None:
                                    st.error("❌ No se pudo parsear el DataModelSchema")
                                else:
                                    # Extraer relaciones
                                    model = schema.get("model", schema.get("Model", {}))
                                    raw_rels = model.get("relationships", model.get("Relationships", []))

                                    if not raw_rels:
                                        st.warning("⚠️ El modelo no contiene relaciones")
                                    else:
                                        relations = []

                                        st.markdown(f"### ✅ {len(raw_rels)} Relaciones Encontradas")

                                        # Tabla de relaciones
                                        rel_data = []
                                        for r in raw_rels:
                                            src_tbl = r.get("fromTable", r.get("SourceTable", "?"))
                                            ref_tbl = r.get("toTable", r.get("ReferencedTable", "?"))
                                            src_col = r.get("fromColumn", r.get("SourceColumn", "?"))
                                            ref_col = r.get("toColumn", r.get("ReferencedColumn", "?"))

                                            relations.append({"from": src_tbl, "to": ref_tbl})
                                            rel_data.append({
                                                "Desde": src_tbl,
                                                "Hacia": ref_tbl,
                                                "Columnas": f"{src_col} → {ref_col}"
                                            })

                                        import pandas as pd
                                        df_relations = pd.DataFrame(rel_data)
                                        st.dataframe(df_relations, use_container_width=True)

                                        # JSON para descargar
                                        relations_json = json.dumps(relations, indent=4, ensure_ascii=False)

                                        st.download_button(
                                            label="⬇️ Descargar relations.json",
                                            data=relations_json,
                                            file_name="relations.json",
                                            mime="application/json",
                                            type="primary"
                                        )

                                        st.success("💡 Usa este archivo relations.json en la pestaña 'Organizar Layout'")

                except Exception as e:
                    st.error(f"❌ Error al extraer: {str(e)}")
                    st.exception(e)

# =============================================================================
# TAB 3: ANÁLISIS
# =============================================================================
with tab3:
    st.header("Análisis de Archivo PBIX")

    st.info("Esta sección te permite analizar la estructura de tu archivo PBIX sin modificarlo")

    uploaded_analysis = st.file_uploader(
        "Selecciona un archivo .pbix para analizar",
        type=['pbix'],
        key="analysis_upload"
    )

    if uploaded_analysis:
        if st.button("📊 Analizar Estructura"):
            with st.spinner("Analizando..."):
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        pbix_path = os.path.join(temp_dir, "analyze.pbix")
                        with open(pbix_path, 'wb') as f:
                            f.write(uploaded_analysis.getbuffer())

                        # Leer layout
                        layout = layout_tool.read_diagram_layout(pbix_path)

                        if layout is None:
                            st.warning("⚠️ No se encontró DiagramLayout")
                        else:
                            table_names = layout_tool.extract_table_names(layout)
                            node_sizes = layout_tool.extract_node_sizes(layout)

                            st.markdown(f"### 📋 Resumen")
                            st.metric("Total de Tablas", len(table_names))

                            # Clasificar
                            fact_tables, dim_tables, other_tables = layout_tool.classify_tables(
                                table_names,
                                ["fct_", "fact_", "FCT_", "FACT_"],
                                ["dim_", "DIM_", "Dim_", "d_", "D_"]
                            )

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Tablas de Hechos", len(fact_tables))
                            with col2:
                                st.metric("Dimensiones", len(dim_tables))
                            with col3:
                                st.metric("Otras", len(other_tables))

                            # Tabla detallada
                            st.markdown("### 📊 Detalle de Tablas")

                            import pandas as pd
                            table_data = []

                            for name in table_names:
                                if name in fact_tables:
                                    tipo = "Fact"
                                elif name in dim_tables:
                                    tipo = "Dimension"
                                else:
                                    tipo = "Otra"

                                size = node_sizes.get(name, (250, 200))

                                table_data.append({
                                    "Tabla": name,
                                    "Tipo": tipo,
                                    "Ancho": size[0],
                                    "Alto": size[1]
                                })

                            df = pd.DataFrame(table_data)
                            st.dataframe(df, use_container_width=True)

                            # Descargar CSV
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Descargar Análisis (CSV)",
                                data=csv,
                                file_name="pbix_analysis.csv",
                                mime="text/csv"
                            )

                except Exception as e:
                    st.error(f"❌ Error en análisis: {str(e)}")
                    st.exception(e)

# =============================================================================
# TAB 4: AYUDA
# =============================================================================
with tab4:
    st.header("📖 Guía de Uso")

    st.markdown("""
    ## ¿Qué hace esta aplicación?

    Esta herramienta organiza automáticamente el diagrama de modelo de Power BI en layouts limpios
    y optimizados, sin necesidad de arrastrar manualmente las tablas.

    ### Modos de Layout

    #### 🌟 Star Layout (Una Tabla de Hechos)
    - El fact se coloca en el centro
    - Las dimensiones forman un anillo alrededor
    - Las dimensiones snowflake se colocan detrás de sus padres

    #### 📐 Grid Layout (Múltiples Tablas de Hechos)
    - Los facts se apilan verticalmente a la izquierda
    - Todas las dimensiones se alinean horizontalmente abajo
    - Las dimensiones con hijos snowflake van al final

    ### Flujo de Trabajo Recomendado

    1. **Extraer Relaciones**
       - Guarda tu modelo como .pbit en Power BI Desktop
       - Usa la pestaña "Extraer Relaciones" para obtener relations.json

    2. **Organizar Layout**
       - Sube tu archivo .pbix
       - Sube el archivo relations.json (opcional pero recomendado)
       - Configura prefijos y opciones
       - Haz clic en "Organizar Layout"

    3. **Abrir en Power BI**
       - Descarga el archivo _arranged.pbix
       - Ábrelo en Power BI Desktop
       - ¡Verás tu modelo perfectamente organizado!

    ### Configuración de Prefijos

    **Tablas de Hechos**: `fct_`, `fact_`, `FCT_`, `FACT_`
    - Ejemplo: `fct_Orders`, `fact_Sales`

    **Dimensiones**: `dim_`, `DIM_`, `Dim_`, `d_`, `D_`
    - Ejemplo: `dim_Customer`, `dim_Product`

    ### Tabs Focalizados

    La opción "Crear Tabs Focalizados" genera:
    - **Diagrama 0**: Vista maestra con todas las tablas
    - **Diagrama 1-N**: Una pestaña por cada fact, mostrando solo ese fact + sus dimensiones conectadas

    Esto es útil para modelos grandes donde la vista completa puede ser abrumadora.

    ### Consejos

    - Si algo sale mal, puedes eliminar el archivo `DiagramLayout` del .pbix (renombra a .zip) y Power BI lo regenerará
    - El radio del Star Layout controla qué tan lejos están las dimensiones del fact central
    - Sin archivo relations.json, la herramienta usará un layout radial simple

    """)

    st.markdown("---")

    st.markdown("""
    ### 🐛 Solución de Problemas

    **"No se encontró DiagramLayout"**
    - Abre el archivo .pbix en Power BI Desktop primero
    - Ve a la vista de Modelo
    - Guarda el archivo
    - Intenta de nuevo

    **"No se encontraron tablas"**
    - Verifica que tu modelo tenga tablas
    - Asegúrate de que el archivo no esté corrupto

    **"Error al parsear DataModelSchema"**
    - Asegúrate de usar un archivo .pbit (no .pbix) para extraer relaciones
    - El archivo debe ser generado desde Power BI Desktop actual
    """)

