"""
Documentation Generator Showcase - What gets documented automatically
Compact intro showcase that appears below the app header
Theme: Industrial Data Observatory (dark + YPF Yellow accent)
"""
import streamlit as st


def render_docgen_showcase():
    """
    Renders a concise intro showcase explaining what the documentation generator documents.
    Positioned right after the app header, matching the style of other apps.
    """
    st.markdown("""
    <style>
    .docgen-intro {
        font-family: 'DM Sans', sans-serif;
        background: linear-gradient(135deg, rgba(242,200,17,0.06) 0%, rgba(242,200,17,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid #F2C811;
        border-radius: 0 14px 14px 0;
        padding: 1.5rem 2rem;
        margin: 1.5rem 0;
    }

    .docgen-intro h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #E8ECF4;
        margin: 0 0 0.6rem 0;
        letter-spacing: -0.03em;
    }

    .docgen-intro p {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.92rem;
        color: #8B95A8;
        line-height: 1.65;
        margin: 0 0 1.25rem 0;
    }

    .capabilities-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
        margin: 0;
    }

    .capability-item {
        background: #181D2A;
        border: 1px solid #252D3D;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        transition: all 240ms cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }

    .capability-item::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 2px; height: 100%;
        background: #F2C811;
        opacity: 0;
        transition: opacity 240ms ease;
    }

    .capability-item:hover {
        background: #1E2536;
        border-color: rgba(242,200,17,0.35);
        transform: translateX(2px);
    }

    .capability-item:hover::before {
        opacity: 1;
    }

    .capability-icon {
        display: inline-block;
        font-size: 1.15rem;
        margin-right: 0.6rem;
        vertical-align: middle;
    }

    .capability-text {
        display: inline-block;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.86rem;
        font-weight: 500;
        color: #E8ECF4;
        vertical-align: middle;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .capability-item {
        animation: fadeInUp 400ms cubic-bezier(0.16, 1, 0.3, 1) backwards;
    }

    .capability-item:nth-child(1) { animation-delay: 50ms; }
    .capability-item:nth-child(2) { animation-delay: 100ms; }
    .capability-item:nth-child(3) { animation-delay: 150ms; }
    .capability-item:nth-child(4) { animation-delay: 200ms; }
    .capability-item:nth-child(5) { animation-delay: 250ms; }
    .capability-item:nth-child(6) { animation-delay: 300ms; }
    </style>

    <div class="docgen-intro">
        <h3>¿Qué documenta automáticamente?</h3>
        <p>
            Analiza tu proyecto Power BI y genera documentación técnica-funcional completa en formato Word:
        </p>
        <div class="capabilities-grid">
            <div class="capability-item">
                <span class="capability-icon">🗂️</span>
                <span class="capability-text">Tablas del modelo</span>
            </div>
            <div class="capability-item">
                <span class="capability-icon">📊</span>
                <span class="capability-text">Medidas DAX</span>
            </div>
            <div class="capability-item">
                <span class="capability-icon">🔗</span>
                <span class="capability-text">Relaciones</span>
            </div>
            <div class="capability-item">
                <span class="capability-icon">📐</span>
                <span class="capability-text">Columnas calculadas</span>
            </div>
            <div class="capability-item">
                <span class="capability-icon">📈</span>
                <span class="capability-text">Visualizaciones</span>
            </div>
            <div class="capability-item">
                <span class="capability-icon">🎨</span>
                <span class="capability-text">Diagrama ER</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
