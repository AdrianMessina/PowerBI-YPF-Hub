"""
Generic module showcase — 'What does this module do?' capabilities grid.
Reusable across Analyzer, Auto-Fixer, Tools, Memory Estimator, Layout Organizer, etc.
Theme: Dark subtle (matches PBI Hub design).
"""
import streamlit as st

_CSS_INJECTED_KEY = "_module_showcase_css_injected"


def _inject_css_once():
    """Inject showcase CSS a single time per session."""
    if st.session_state.get(_CSS_INJECTED_KEY):
        return
    st.session_state[_CSS_INJECTED_KEY] = True
    st.markdown("""
    <style>
    .module-showcase {
        font-family: 'Fira Sans', 'DM Sans', sans-serif;
        background: linear-gradient(135deg, rgba(4,81,228,0.08) 0%, rgba(4,81,228,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-left: 3px solid #0451E4;
        border-radius: 0 12px 12px 0;
        padding: 1.35rem 1.75rem;
        margin: 1rem 0 1.5rem;
    }
    .module-showcase h3 {
        font-family: 'Fira Sans', sans-serif !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #E8ECF4 !important;
        margin: 0 0 0.4rem 0 !important;
        letter-spacing: -0.02em !important;
    }
    .module-showcase p.showcase-desc {
        font-family: 'Fira Sans', sans-serif !important;
        font-size: 0.9rem !important;
        color: #CBD5E1 !important;
        line-height: 1.6 !important;
        margin: 0 0 1rem 0 !important;
    }
    .showcase-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.65rem;
        margin: 0;
    }
    .showcase-item {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }
    .showcase-item::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 2px; height: 100%;
        background: #0451E4;
        opacity: 0;
        transition: opacity 200ms ease;
    }
    .showcase-item:hover {
        background: rgba(255,255,255,0.07);
        border-color: rgba(4,81,228,0.35);
        transform: translateX(2px);
    }
    .showcase-item:hover::before { opacity: 1; }
    .showcase-icon {
        display: inline-block;
        font-size: 1.05rem;
        margin-right: 0.55rem;
        vertical-align: middle;
    }
    .showcase-text {
        display: inline-block;
        font-family: 'Fira Sans', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #F1F5F9 !important;
        vertical-align: middle;
    }
    @keyframes showcaseFadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .showcase-item {
        animation: showcaseFadeIn 350ms cubic-bezier(0.16, 1, 0.3, 1) backwards;
    }
    .showcase-item:nth-child(1) { animation-delay: 40ms; }
    .showcase-item:nth-child(2) { animation-delay: 80ms; }
    .showcase-item:nth-child(3) { animation-delay: 120ms; }
    .showcase-item:nth-child(4) { animation-delay: 160ms; }
    .showcase-item:nth-child(5) { animation-delay: 200ms; }
    .showcase-item:nth-child(6) { animation-delay: 240ms; }
    .showcase-item:nth-child(7) { animation-delay: 280ms; }
    .showcase-item:nth-child(8) { animation-delay: 320ms; }
    </style>
    """, unsafe_allow_html=True)


def render_module_showcase(title: str, description: str, items: list[tuple[str, str]]):
    """Render a generic 'what does this module do?' showcase.

    Args:
        title: Header (e.g. "¿Qué hace este módulo?")
        description: Short paragraph explaining the module
        items: List of (icon, text) tuples, e.g. [("🔍", "Score 0-100"), ...]
    """
    _inject_css_once()

    items_html = "".join(
        f'<div class="showcase-item">'
        f'<span class="showcase-icon">{icon}</span>'
        f'<span class="showcase-text">{text}</span>'
        f'</div>'
        for icon, text in items
    )

    st.markdown(f"""
    <div class="module-showcase">
        <h3>{title}</h3>
        <p class="showcase-desc">{description}</p>
        <div class="showcase-grid">
            {items_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
