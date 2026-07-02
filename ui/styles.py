"""PBI Hub — Design System: Diagnostic Console

Look inspirado en PBI Error Helper:
  - Content area light (#F8FAFC + #FFFFFF)
  - Sidebar dark con gradient (#080E1A -> #1E293B)
  - Accent: YPF Blue #0451E4
  - Typography: Fira Sans + Fira Code
  - Max width ~1200px

Mantiene clases legacy que usan los modulos migrados
(main-header, sub-header, metric-card, feature-card, help-box) adaptadas
a light theme.
"""

MAIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700;800&display=swap');

:root {
    /* YPF Blue palette */
    --blue: #0451E4;
    --blue-hover: #0340B8;
    --blue-deep: #022A8A;
    --blue-glow: rgba(4,81,228,0.14);
    --blue-subtle: rgba(4,81,228,0.05);
    --blue-tint: rgba(4,81,228,0.10);

    /* YPF Yellow (secondary accent) */
    --yellow: #F2C811;
    --yellow-hover: #FFD84A;
    --yellow-subtle: rgba(242,200,17,0.10);

    /* Dark subtle surfaces (content area) */
    --surface-0: #1F2937;
    --surface-1: #1A1F2E;
    --surface-2: #252B3A;
    --surface-3: #2F3647;

    /* Dark sidebar */
    --dark-0: #080E1A;
    --dark-1: #0F172A;
    --dark-2: #1E293B;
    --dark-3: #334155;

    /* Ink (text) — light for dark bg */
    --ink: #E8ECF4;
    --ink-2: #CBD5E1;
    --ink-3: #94A3B8;
    --ink-4: #6B7280;
    --ink-on-dark: #CBD5E1;
    --ink-white: #F1F5F9;

    /* Lines */
    --line: rgba(255,255,255,0.10);
    --line-light: rgba(255,255,255,0.06);
    --line-dark: rgba(255,255,255,0.07);

    /* Severity */
    --sev-alta: #EF4444;
    --sev-alta-bg: rgba(239,68,68,0.12);
    --sev-media: #F59E0B;
    --sev-media-bg: rgba(245,158,11,0.12);
    --sev-baja: #10B981;
    --sev-baja-bg: rgba(16,185,129,0.12);

    /* Radius */
    --r-sm: 6px;
    --r-md: 8px;
    --r-lg: 12px;
    --r-xl: 16px;
    --r-full: 9999px;

    /* Shadows (darker for dark bg) */
    --sh-xs: 0 1px 2px rgba(0,0,0,0.15);
    --sh-sm: 0 1px 3px rgba(0,0,0,0.25), 0 1px 2px rgba(0,0,0,0.12);
    --sh-md: 0 4px 12px rgba(0,0,0,0.30);
    --sh-lg: 0 10px 28px rgba(0,0,0,0.40);
    --sh-blue: 0 4px 20px rgba(4,81,228,0.25);
    --sh-hover: 0 8px 24px rgba(4,81,228,0.18), 0 2px 8px rgba(0,0,0,0.12);
    --sh-console: inset 0 2px 8px rgba(0,0,0,0.30), 0 4px 20px rgba(0,0,0,0.20);

    /* Motion */
    --ease: cubic-bezier(0.25, 0.46, 0.45, 0.94);
    --t-fast: 120ms;
    --t-norm: 200ms;
    --t-slow: 320ms;

    /* Fonts */
    --sans: 'Fira Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --mono: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;

    /* Legacy tokens (Industrial Data Observatory compat) */
    --brand-accent: var(--blue);
    --brand-accent-hover: var(--blue-hover);
    --brand-accent-muted: var(--blue-subtle);
    --brand-accent-glow: var(--blue-glow);
    --text-primary: var(--ink);
    --text-secondary: var(--ink-3);
    --border-subtle: var(--line-light);
    --border-default: var(--line);
    --radius-sm: var(--r-sm);
    --radius-md: var(--r-md);
    --radius-lg: var(--r-lg);
    --duration-normal: var(--t-norm);
    --ease-out: var(--ease);
    --font-body: var(--sans);
}

/* ============ STREAMLIT CHROME ============ */
#MainMenu, footer, .stDeployButton { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
}
.stApp {
    background: var(--surface-1) !important;
}
.stAppViewBlockContainer,
[data-testid="stAppViewBlockContainer"] {
    padding-top: 1rem !important;
    max-width: 1200px !important;
}
.block-container { padding-top: 1rem !important; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* ============ TYPOGRAPHY ============ */
html, body, [class*="css"] {
    font-family: var(--sans) !important;
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
}
code, pre, .stCodeBlock, [data-testid="stCode"] {
    font-family: var(--mono) !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: var(--sans) !important;
    color: var(--ink);
    letter-spacing: -0.025em;
    line-height: 1.2;
}

/* Main page headers (legacy from modules) */
.main-header {
    font-family: var(--sans) !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--ink) !important;
    letter-spacing: -0.035em !important;
    line-height: 1.1 !important;
    margin: 0 0 0.5rem !important;
}
.sub-header {
    font-family: var(--sans) !important;
    color: var(--ink-3) !important;
    font-size: 0.95rem !important;
    line-height: 1.55 !important;
    margin: 0 0 1.5rem !important;
    max-width: 720px !important;
}

/* ============ SIDEBAR ============ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--dark-0) 0%, var(--dark-1) 60%, var(--dark-2) 100%) !important;
    border-right: 1px solid var(--line-dark) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0.5rem 0.25rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: var(--ink-on-dark); }
[data-testid="stSidebar"] hr { border-color: var(--line-dark); margin: 0.65rem 0; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p {
    color: var(--ink-on-dark) !important;
}

/* Sidebar brand block */
.sidebar-brand {
    padding: 0.5rem 0.75rem 0.85rem;
    text-align: center;
}
.sidebar-brand .brand-line {
    height: 2px;
    background: linear-gradient(90deg, var(--blue) 0%, var(--blue-hover) 60%, transparent 100%);
    margin: 0.75rem auto 0.85rem;
    width: 100%;
}
.sidebar-brand .product-name {
    color: #FFF; font-size: 1.05rem; font-weight: 700;
    letter-spacing: -0.02em; margin: 0; font-family: var(--sans);
}
.sidebar-brand .product-sub {
    color: var(--ink-on-dark); font-size: 0.62rem; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.14em;
    margin: 0.25rem 0 0; font-family: var(--mono);
}

/* Sidebar labels (section headers inside sidebar) */
.sidebar-label {
    color: #94A3B8; font-size: 0.6rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.14em;
    padding: 0.85rem 0.85rem 0.4rem; font-family: var(--mono);
}

/* Sidebar radio */
[data-testid="stSidebar"] .stRadio > label { display: none !important; }
[data-testid="stSidebar"] .stRadio > div { gap: 1px; }
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {
    background: transparent; cursor: pointer !important;
    border-radius: 4px; padding: 0.05rem 0;
    transition: background var(--t-fast) var(--ease);
    position: relative;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {
    background: rgba(4,81,228,0.14);
}
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stRadio label *,
[data-testid="stSidebar"] .stRadio p,
[data-testid="stSidebar"] .stRadio span {
    color: var(--ink-on-dark) !important;
    font-family: var(--sans) !important;
    font-size: 0.86rem !important;
    font-weight: 400 !important;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover label,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover span {
    color: #FFF !important;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"] {
    background: rgba(4,81,228,0.20);
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"]::before {
    content: ''; position: absolute;
    left: 0; top: 18%; bottom: 18%;
    width: 2px; background: var(--blue);
    border-radius: 0 2px 2px 0;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"] label,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"] span {
    color: #FFF !important; font-weight: 600 !important;
}

/* Sidebar footer */
.sidebar-footer {
    margin-top: 1.25rem; padding: 0.85rem 0.75rem 0.5rem;
    border-top: 1px solid var(--line-dark);
}
.sidebar-footer .footer-text {
    color: #64748B; font-size: 0.6rem; text-align: center;
    font-family: var(--mono); letter-spacing: 0.06em; margin: 0 0 0.6rem 0;
}

/* Sidebar inputs (uploader, text_input, buttons) */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.03);
    border: 1px dashed rgba(255,255,255,0.15);
    border-radius: var(--r-md);
    padding: 0.5rem;
}
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.05) !important;
    color: #FFF !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: #64748B !important;
}
[data-testid="stSidebar"] .stButton button {
    background: var(--blue) !important;
    color: #FFF !important;
    border: none !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--sans) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: background var(--t-fast) var(--ease);
}
[data-testid="stSidebar"] .stButton button:hover {
    background: var(--blue-hover) !important;
}
[data-testid="stSidebar"] [data-testid="stAlert"] {
    font-size: 0.8rem;
}

/* Sidebar expanders (must stay dark) */
[data-testid="stSidebar"] .streamlit-expanderHeader,
[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary {
    background: rgba(255,255,255,0.03) !important;
    color: var(--ink-on-dark) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    font-family: var(--sans) !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary:hover {
    background: rgba(4,81,228,0.14) !important;
}

/* ============ CONTENT AREA ============ */

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--surface-0);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.2rem 1.35rem;
    box-shadow: var(--sh-sm);
    transition: box-shadow var(--t-fast) var(--ease);
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--sh-md);
}
[data-testid="stMetricLabel"] {
    color: var(--ink-4) !important;
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: var(--ink) !important;
    font-family: var(--sans) !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.025em;
}
[data-testid="stMetricDelta"] {
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
}

/* Feature cards (Home) */
.feature-card {
    background: var(--surface-0);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.5rem;
    box-shadow: var(--sh-sm);
    transition: all var(--t-norm) var(--ease);
    margin-bottom: 1rem;
}
.feature-card:hover {
    box-shadow: var(--sh-hover);
    border-color: rgba(4,81,228,0.15);
    transform: translateY(-1px);
}
.feature-card h3 {
    color: var(--ink);
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0 0 0.5rem;
    letter-spacing: -0.02em;
}
.feature-card p {
    color: var(--ink-3);
    font-size: 0.9rem;
    line-height: 1.55;
    margin: 0.5rem 0;
}
.feature-card ul {
    color: var(--ink-3);
    font-size: 0.85rem;
    margin: 0.5rem 0 0 1rem;
    padding: 0;
}
.feature-card ul li {
    margin: 0.2rem 0;
}

/* Info/help/alert boxes */
.help-box {
    background: var(--blue-subtle);
    border: 1px solid rgba(4,81,228,0.15);
    border-radius: var(--r-md);
    padding: 1rem 1.2rem;
    color: var(--ink-2);
    margin: 1rem 0;
}
.help-box h4 {
    color: var(--blue);
    font-size: 0.95rem;
    font-weight: 700;
    margin: 0 0 0.5rem;
}
.help-box p,
.help-box li,
.help-box ul,
.help-box strong {
    color: var(--ink-2);
}
.help-box strong { color: var(--ink); }

/* Section header (used in DocGen form sections) */
.section-header {
    background: var(--surface-0);
    border-left: 3px solid var(--blue);
    color: var(--ink);
    padding: 0.6rem 1rem;
    font-weight: 700;
    font-size: 0.9rem;
    margin: 1.25rem 0 0.75rem 0;
    border-radius: 0 var(--r-md) var(--r-md) 0;
    font-family: var(--sans);
    letter-spacing: -0.01em;
}
[data-testid="stInfo"] {
    background: var(--blue-subtle) !important;
    border: 1px solid rgba(4,81,228,0.15) !important;
    border-radius: var(--r-md) !important;
    color: var(--ink-2) !important;
}
[data-testid="stSuccess"] {
    background: var(--sev-baja-bg) !important;
    border: 1px solid rgba(5,150,105,0.20) !important;
    border-radius: var(--r-md) !important;
    color: var(--ink-2) !important;
}
[data-testid="stWarning"] {
    background: var(--sev-media-bg) !important;
    border: 1px solid rgba(217,119,6,0.20) !important;
    border-radius: var(--r-md) !important;
    color: var(--ink-2) !important;
}
[data-testid="stError"] {
    background: var(--sev-alta-bg) !important;
    border: 1px solid rgba(220,38,38,0.20) !important;
    border-radius: var(--r-md) !important;
    color: var(--ink-2) !important;
}

/* Force bright text inside stInfo/stWarning/stSuccess/stError markdown */
main [data-testid="stInfo"] p,
main [data-testid="stInfo"] li,
main [data-testid="stInfo"] strong,
main [data-testid="stSuccess"] p,
main [data-testid="stSuccess"] li,
main [data-testid="stSuccess"] strong,
main [data-testid="stWarning"] p,
main [data-testid="stWarning"] li,
main [data-testid="stWarning"] strong,
main [data-testid="stError"] p,
main [data-testid="stError"] li,
main [data-testid="stError"] strong {
    color: var(--ink) !important;
}

/* Ensure main content area markdown text is always readable on dark bg */
main [data-testid="stMarkdownContainer"],
main [data-testid="stMarkdownContainer"] p,
main [data-testid="stMarkdownContainer"] li,
main [data-testid="stMarkdownContainer"] ol,
main [data-testid="stMarkdownContainer"] ul {
    color: var(--ink-2) !important;
}
main [data-testid="stMarkdownContainer"] strong {
    color: var(--ink) !important;
}
main [data-testid="stMarkdownContainer"] h1,
main [data-testid="stMarkdownContainer"] h2,
main [data-testid="stMarkdownContainer"] h3,
main [data-testid="stMarkdownContainer"] h4,
main [data-testid="stMarkdownContainer"] h5,
main [data-testid="stMarkdownContainer"] h6 {
    color: var(--ink) !important;
}

/* Expander content — bright text on subtle bg */
main [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
main [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
main [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li,
main [data-testid="stExpander"] [data-testid="stMarkdownContainer"] ol {
    color: var(--ink-2) !important;
}
main [data-testid="stExpander"] > details > div {
    background: var(--surface-0) !important;
    border-radius: 0 0 var(--r-md) var(--r-md) !important;
    padding: 0.75rem 1rem !important;
}

/* ============ BUTTONS ============ */
.stButton > button {
    background: var(--blue);
    color: #FFF;
    border: none;
    border-radius: var(--r-sm);
    font-family: var(--sans);
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.5rem 1.15rem;
    transition: all var(--t-fast) var(--ease);
    box-shadow: var(--sh-xs);
}
.stButton > button:hover {
    background: var(--blue-hover);
    box-shadow: var(--sh-blue);
}
.stButton > button:disabled {
    background: var(--surface-3) !important;
    color: var(--ink-4) !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"] {
    background: var(--surface-0);
    color: var(--ink);
    border: 1px solid var(--line);
}
.stButton > button[kind="secondary"]:hover {
    background: var(--surface-1);
    border-color: var(--blue);
}
.stDownloadButton > button {
    background: var(--blue);
    color: #FFF;
    border: none;
    border-radius: var(--r-sm);
    font-family: var(--sans);
    font-weight: 600;
    font-size: 0.9rem;
}

/* ============ TABS ============ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--line);
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--ink-4) !important;
    font-family: var(--sans) !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1.15rem !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--ink) !important;
    background: var(--surface-1) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--blue) !important;
    border-bottom-color: var(--blue) !important;
}

/* ============ TEXT INPUT / TEXTAREA ============ */
main .stTextInput input,
main .stTextArea textarea,
main .stSelectbox > div {
    background: var(--surface-0) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--r-sm) !important;
    color: var(--ink) !important;
    font-family: var(--sans) !important;
}
main .stTextInput input:focus,
main .stTextArea textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(4,81,228,0.1) !important;
}

/* ============ DATAFRAMES ============ */
[data-testid="stDataFrame"] {
    background: var(--surface-0);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--sh-sm);
}

/* ============ EXPANDERS (content area) ============ */
main .streamlit-expanderHeader,
main [data-testid="stExpander"] > details > summary {
    background: var(--surface-0) !important;
    color: var(--ink) !important;
    font-family: var(--sans) !important;
    font-weight: 600 !important;
    border-radius: var(--r-md) !important;
    border: 1px solid var(--line) !important;
}
main [data-testid="stExpander"] > details > summary:hover {
    background: var(--surface-1) !important;
    border-color: var(--blue) !important;
}
main [data-testid="stExpander"] {
    background: transparent !important;
    border-radius: var(--r-md) !important;
    margin-bottom: 0.5rem;
}

/* ============ DIVIDERS ============ */
main hr,
main [data-testid="stMarkdownContainer"] hr {
    border: none;
    border-top: 1px solid var(--line);
    margin: 1.5rem 0;
}

/* ============ PROGRESS ============ */
.stProgress > div > div {
    background: var(--blue) !important;
}

/* ============ SLIDER ============ */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--blue) !important;
    border-color: var(--blue) !important;
}

/* ============ CAPTIONS ============ */
main .stCaption,
main [data-testid="stCaptionContainer"] {
    color: var(--ink-4) !important;
    font-family: var(--sans) !important;
    font-size: 0.8rem !important;
}

/* ============ FILE UPLOADER (content area) ============ */
main [data-testid="stFileUploader"] {
    background: var(--surface-0);
    border: 2px dashed var(--line);
    border-radius: var(--r-md);
    padding: 1rem;
}
main [data-testid="stFileUploader"]:hover {
    border-color: var(--blue);
    background: var(--blue-subtle);
}

</style>
"""
