"""
Documentation Generator - Integrado en YPF BI Monitor
Replica funcionalidad completa de Documentation Generator v3 (v4.0)
"""

import streamlit as st
import sys
import logging
from pathlib import Path
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)


def render(logger_suite):
    """Documentation Generator module for PBI Hub."""

    # Imports absolutos - NO requiere manipular sys.path
    from apps_core.docgen_core.core.parsers import create_parser, FormatDetector, PowerBIFormat
    from apps_core.docgen_core.core.parsers.tmdl_parser_v2 import TMDLParserV2
    from apps_core.docgen_core.utils.image_helper import save_uploaded_images, cleanup_temp_images
    from apps_core.docgen_core.visualization import ERDiagramGenerator
    from apps_core.docgen_core.document_generation.docx_builder_v3 import DocxBuilderV3

    # Variable para logger
    usage_logger = logger_suite
    LOGGING_ENABLED = logger_suite is not None

    # Project root para buscar template
    project_root = Path(__file__).parent.parent

    # Import shared styles
    from apps_core.layout_core.shared_styles import render_app_header, render_footer
    from apps_core.layout_core.docgen_showcase import render_docgen_showcase

    # Header — usando main-header + sub-header como otros módulos
    st.markdown(
        '<h1 class="main-header">📄 Documentation Generator</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Generación automática de documentación técnica-funcional en formato Word.</p>',
        unsafe_allow_html=True,
    )

    # Showcase - what gets documented
    render_docgen_showcase()

    # Examples in expander
    with st.expander("👁️ Ver ejemplos de documentación generada", expanded=False):
        st.markdown("**Así se ve la documentación que genera automáticamente:**")

        example_titles = [
            "📄 Portada Corporativa",
            "🗂️ Tablas y Columnas",
            "📊 Medidas DAX",
            "🔗 Diagrama de Relaciones",
            "📈 Análisis de Visualizaciones"
        ]

        for i, title in enumerate(example_titles, 1):
            img_path = project_root / "assets" / f"docgen_example_{i}.jpg"
            if img_path.exists():
                st.markdown(f"**{title}**")
                st.image(str(img_path), use_container_width=True)
                if i < 5:
                    st.markdown("---")

    st.markdown("---")

    # ── Unified project source (sidebar or local override) ────────────
    from shared.loader import get_project

    project = get_project()

    if project is not None:
        pbip_path = Path(project.report_path)

        # If the loaded project path is a directory (Cloud ZIP extract),
        # find the .pbip file inside
        if pbip_path.is_dir():
            pbip_files_in_dir = list(pbip_path.glob("*.pbip"))
            if pbip_files_in_dir:
                pbip_path = pbip_files_in_dir[0]
            else:
                # Search recursively (typical PBIP folder structure)
                pbip_files_in_dir = list(pbip_path.rglob("*.pbip"))
                if pbip_files_in_dir:
                    pbip_path = pbip_files_in_dir[0]

        if not pbip_path.exists():
            st.error(f"❌ No se encontró el archivo .pbip en: `{pbip_path}`")
            st.info("Recargá el proyecto desde el sidebar.")
            st.stop()
    else:
        st.warning(
            "⚠️ **Sin proyecto cargado.** "
            "Cargá un archivo PBIP desde el sidebar (uploader ZIP en Cloud, "
            "ruta local en desktop). El módulo se activará automáticamente."
        )
        st.stop()
    
    st.markdown("---")
    
    # Help box about optional fields
    st.markdown("""
    <div class="help-box">
        <h4>💡 Ayuda para completar el formulario</h4>
        <ul>
            <li><strong>Campos con *</strong>: Opcionales - el sistema los completará automáticamente si los dejas vacíos</li>
            <li><strong>Objetivo y Alcance</strong>: Si no los completas, se generarán basándose en el contenido del reporte</li>
            <li><strong>Imágenes</strong>: Recomendado pero opcional - sube capturas de tu reporte para mejorar el documento</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for images if not exists
    if 'er_image' not in st.session_state:
        st.session_state.er_image = None
    if 'viz_images' not in st.session_state:
        st.session_state.viz_images = []
    
    # Single form with all fields
    with st.form("simple_complete_form"):
    
        # SECTION 1: Images (PROMINENT - at the top)
        st.markdown('<div class="section-header">📸 IMÁGENES (Opcional - Recomendado)</div>', unsafe_allow_html=True)
    
        st.info("💡 **Recomendación**: Sube capturas de pantalla de tu reporte para un documento más completo")
    
        # ER Model image
        st.markdown("**📊 Modelo de Relaciones (ER Diagram)**")
        er_image = st.file_uploader(
            "Sube una captura del diagrama de relaciones",
            type=['png', 'jpg', 'jpeg'],
            key="er_upload",
            help="Captura del Model View en Power BI Desktop"
        )
    
        if er_image:
            st.success(f"✅ Imagen cargada: {er_image.name}")
            # Store in session state immediately
            st.session_state.er_image = er_image
    
        # Visualization images
        st.markdown("**📈 Visualizaciones del Reporte**")
        viz_images = st.file_uploader(
            "Sube capturas de tus dashboards (máximo 10 imágenes)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            key="viz_upload",
            help="Capturas del Report View - páginas principales"
        )
    
        if viz_images:
            count = min(len(viz_images), 10)
            st.success(f"✅ {count} imagen(es) cargada(s)")
            if len(viz_images) > 10:
                st.warning("⚠️ Solo se usarán las primeras 10 imágenes")
            # Store in session state immediately
            st.session_state.viz_images = viz_images
    
        st.markdown("---")
    
        # SECTION 2: Document Information
        st.markdown('<div class="section-header">📝 INFORMACIÓN DEL DOCUMENTO</div>', unsafe_allow_html=True)
    
        # Report Name (for cover page)
        nombre_reporte = st.text_input(
            "Nombre del reporte",
            value="",
            placeholder="Ej: Análisis de ventas",
            help="Nombre que aparecerá en la portada del documento"
        )
    
        col1, col2 = st.columns(2)
    
        with col1:
            version = st.text_input("Versión", value="1.0", help="Ej: 1.0, 2.1")
    
        with col2:
            autor = st.text_input("Autor", value="YPF - Equipo de desarrollo de visualización", help="Nombre del responsable")
    
        observaciones = st.text_input(
            "Observaciones de la versión",
            value="Generación inicial de documentación técnica",
            help="Qué cambios incluye esta versión"
        )
    
        st.markdown("---")
    
        # SECTION 3: Report Details (Optional)
        st.markdown('<div class="section-header">🎯 DETALLES DEL REPORTE (Opcional)</div>', unsafe_allow_html=True)
        st.caption("* = Se autocompleta si se deja vacío")
    
        objetivo = st.text_area(
            "Objetivo del reporte *",
            placeholder="Ej: Proporcionar análisis de ventas regionales del Q1 2026...",
            help="¿Cuál es el propósito de negocio de este reporte? (se generará automáticamente si se deja vacío)",
            height=100
        )
    
        alcance = st.text_area(
            "Alcance del análisis *",
            placeholder="Ej: Incluye datos de ventas desde enero 2024, todas las regiones operativas...",
            help="¿Qué datos, periodos y métricas cubre? (se generará automáticamente si se deja vacío)",
            height=100
        )
    
        col1, col2 = st.columns(2)
    
        with col1:
            administrador = st.text_input(
                "Administrador del reporte *",
                placeholder="Ej: María González - Analytics Team",
                help="Responsable del reporte (opcional)"
            )
    
        with col2:
            solicitante = st.text_input(
                "Solicitante *",
                placeholder="Ej: Dirección Comercial",
                help="Área que solicitó el reporte (opcional)"
            )
    
        st.markdown("---")
    
        # SECTION 4: Technical Configuration (Optional)
        st.markdown('<div class="section-header">🔄 CONFIGURACIÓN TÉCNICA (Opcional)</div>', unsafe_allow_html=True)
    
        # Dataset refresh schedule
        st.markdown("**📊 Horario de actualización del conjunto de datos (Dataset)**")
    
        col1, col2 = st.columns(2)
        with col1:
            dataset_frecuencia = st.selectbox(
                "Frecuencia",
                ["No especificada", "Diaria", "Semanal", "Mensual", "Tiempo real"],
                key="dataset_freq",
                help="Frecuencia de actualización del dataset"
            )
    
        with col2:
            dataset_horarios = st.text_input(
                "Horarios",
                placeholder="Ej: 12:00 a.m., 6:00 p.m., 12:00 p.m., 6:00 a.m.",
                key="dataset_hours",
                help="Horarios de actualización separados por comas"
            )
    
        # Dataflow refresh schedule
        st.markdown("**🔄 Horario de actualización del flujo (Dataflow)**")
    
        col1, col2 = st.columns(2)
        with col1:
            flujo_frecuencia = st.selectbox(
                "Frecuencia",
                ["No especificada", "Diaria", "Semanal", "Mensual", "Tiempo real"],
                key="flujo_freq",
                help="Frecuencia de actualización del flujo de datos"
            )
    
        with col2:
            flujo_horarios = st.text_input(
                "Horarios",
                placeholder="Ej: 11:30 a.m., 5:30 p.m., 11:30 p.m., 5:30 a.m.",
                key="flujo_hours",
                help="Horarios de actualización separados por comas"
            )
    
        # Build complete frequency strings
        if dataset_frecuencia != "No especificada":
            if dataset_horarios:
                frecuencia_dataset = f"{dataset_frecuencia} - Horarios: {dataset_horarios}"
            else:
                frecuencia_dataset = dataset_frecuencia
        else:
            frecuencia_dataset = "No especificada"
    
        if flujo_frecuencia != "No especificada":
            if flujo_horarios:
                frecuencia_flujo = f"{flujo_frecuencia} - Horarios: {flujo_horarios}"
            else:
                frecuencia_flujo = flujo_frecuencia
        else:
            frecuencia_flujo = "No especificada"
    
        st.markdown("---")
    
        # Generate button
        generate = st.form_submit_button(
            "🚀 GENERAR DOCUMENTO WORD",
            use_container_width=True,
            type="primary"
        )
    
    # Show cached images status outside form
    if st.session_state.get('er_image') or st.session_state.get('viz_images'):
        st.markdown("---")
        st.markdown("### 📋 Imágenes Preparadas")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.get('er_image'):
                st.info(f"✅ ER Diagram: {st.session_state.er_image.name}")
        with col2:
            if st.session_state.get('viz_images'):
                viz_count = len(st.session_state.viz_images)
                st.info(f"✅ Visualizaciones: {viz_count} imagen(es)")
    
    # Generation logic
    if generate:
        try:
            # Log document generation start
            if LOGGING_ENABLED and usage_logger:
                usage_logger.log_event('docgen_started', {
                    'pbip_file': pbip_path.name if 'pbip_path' in locals() else 'unknown'
                })

            # Progress indicators
            progress = st.progress(0)
            status = st.empty()
    
            # Step 1: Process images (use session state)
            status.write("📸 Procesando imágenes...")
            progress.progress(10)
    
            er_image_path = None
            viz_image_paths = []

            # Use form variables directly (session state doesn't persist in forms until after submission)
            uploaded_er = er_image
            uploaded_viz = viz_images
    
            if uploaded_er:
                saved_er = save_uploaded_images(uploaded_er, prefix="er_model")
                if saved_er:
                    er_image_path = saved_er[0]
                    logger.info(f"ER image saved to: {er_image_path}")
    
            if uploaded_viz:
                viz_images_limited = uploaded_viz[:10]
                viz_image_paths = save_uploaded_images(viz_images_limited, prefix="viz")
                logger.info(f"Saved {len(viz_image_paths)} visualization images")
    
            # Step 2: Parse PBIP
            status.write("📖 Leyendo archivo Power BI...")
            progress.progress(25)
    
            format_detector = FormatDetector()
            detected_format = format_detector.detect(str(pbip_path))
    
            if detected_format == PowerBIFormat.PBIP:
                # Find .SemanticModel folder
                pbip_dir = pbip_path.parent
                model_folders = list(pbip_dir.glob("*.SemanticModel"))
    
                if not model_folders:
                    st.error("❌ No se encontró carpeta .SemanticModel en el proyecto PBIP")
                    st.stop()
    
                definition_path = model_folders[0] / "definition"
    
                if not definition_path.exists():
                    st.error(f"❌ No se encontró carpeta definition: {definition_path}")
                    st.stop()
    
                parser = TMDLParserV2(definition_path)
                metadata = parser.parse_all()
            else:
                parser = create_parser(str(pbip_path))
                metadata = parser.parse()
    
            # Step 3: Generate ER diagram (auto)
            status.write("🎨 Generando diagrama de relaciones...")
            progress.progress(50)
    
            er_diagram_path = None
            try:
                er_generator = ERDiagramGenerator()
                er_diagram_path = er_generator.generate_from_metadata(
                    metadata,
                    output_dir=str(project_root / "output")
                )
            except Exception as e:
                logger.warning(f"Could not generate ER diagram: {e}")
    
            # Step 4: Build Word document
            status.write("📄 Construyendo documento Word...")
            progress.progress(70)
    
            # Complete user inputs with optional fields
            user_inputs = {
                'titulo_reporte': nombre_reporte.strip() if nombre_reporte.strip() else None,  # Clave correcta
                'version': version,
                'autor': autor,
                'observaciones': observaciones,
                'objetivo': objetivo.strip() if objetivo.strip() else None,  # Auto-complete if empty
                'alcance': alcance.strip() if alcance.strip() else None,    # Auto-complete if empty
                'administrador': administrador.strip() if administrador.strip() else None,
                'solicitante': solicitante.strip() if solicitante.strip() else None,
                'frecuencia_dataset': frecuencia_dataset,
                'frecuencia_flujo': frecuencia_flujo
            }
    
            # Find template - Buscar en múltiples ubicaciones
            template_locations = [
                # Ubicación principal: dentro del proyecto (funciona para todos los usuarios)
                project_root / "templates" / "docgen" / "plantilla_corporativa_ypf.docx",
                # Fallback: directamente en templates
                project_root / "templates" / "plantilla_corporativa_ypf.docx",
                # Fallback: carpeta padre del proyecto
                project_root.parent / "Plantilla Documentacion Técnica Funcional Power Bi.docx",
            ]

            template_path = None
            for location in template_locations:
                if location.exists():
                    template_path = location
                    break

            if not template_path:
                st.error("Template no encontrado. Verifica que exista:")
                st.code("templates/docgen/plantilla_corporativa_ypf.docx")
                st.info("Descarga el template desde el repositorio de GitHub y colocalo en la carpeta 'templates/docgen/'")
                st.stop()
    
            # Build
            def progress_callback(step, message):
                progress.progress(step)
                status.write(f"[{step}%] {message}")
    
            builder = DocxBuilderV3(str(template_path))
            output_path = builder.build(
                metadata=metadata,
                user_inputs=user_inputs,
                er_diagram_path=er_diagram_path,
                er_image_path=er_image_path,
                visualization_images=viz_image_paths,
                progress_callback=progress_callback
            )
    
            progress.progress(100)
            status.empty()

            # Log document generation completion
            if LOGGING_ENABLED and usage_logger:
                img_count = (1 if er_image_path else 0) + len(viz_image_paths)
                usage_logger.log_event('docgen_completed', {
                    'pbip_file': pbip_path.name,
                    'images_count': img_count,
                    'has_manual_objetivo': bool(objetivo.strip()),
                    'has_manual_alcance': bool(alcance.strip())
                })

            # Success!
            st.success("✅ ¡Documento generado exitosamente!")
    
            # Show summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📄 Documento", "Completo")
            with col2:
                img_count = (1 if er_image_path else 0) + len(viz_image_paths)
                st.metric("📸 Imágenes", f"{img_count}")
            with col3:
                objetivo_status = "Manual" if objetivo.strip() else "Auto"
                st.metric("🎯 Objetivo", objetivo_status)
            with col4:
                alcance_status = "Manual" if alcance.strip() else "Auto"
                st.metric("📏 Alcance", alcance_status)
    
            # Download button
            st.markdown("---")
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="⬇️ DESCARGAR DOCUMENTO WORD",
                    data=f,
                    file_name=Path(output_path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            # Cleanup temporary images
            if er_image_path or viz_image_paths:
                try:
                    all_temp_images = []
                    if er_image_path:
                        all_temp_images.append(er_image_path)
                    if viz_image_paths:
                        all_temp_images.extend(viz_image_paths)
                    cleanup_temp_images(all_temp_images)
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")
    
        except Exception as e:
            st.error(f"❌ Error al generar el documento: {str(e)}")
            with st.expander("🔍 Ver detalles del error"):
                import traceback
                st.code(traceback.format_exc())
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p><strong>Power BI Documentation Generator v4.0</strong></p>
        <p>YPF S.A. | Equipo de desarrollo de visualización | 2026</p>
    </div>
    """, unsafe_allow_html=True)
