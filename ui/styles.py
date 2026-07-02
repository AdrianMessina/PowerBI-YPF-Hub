"""Power BI Fixer — Design System v3.1
Aesthetic: Industrial Data Observatory
Display font: Space Grotesk (geometric, technical character)
Body font: DM Sans (clean readability)
Data font: JetBrains Mono (precision)
Color: Blue-tinted dark + YPF Yellow surgical accent
Texture: Noise grain overlay for depth
Anchor: Diagonal accent slash on header (signature element)
DFII: 13/15
"""

MAIN_CSS = """
<style>
    /* ═══════════════════════════════════════════════════════════════
       POWER BI FIXER — DESIGN SYSTEM v3.1
       "Industrial Data Observatory"
       Display: Space Grotesk | Body: DM Sans | Data: JetBrains Mono
       DFII: Impact 4 + Fit 5 + Feasibility 4 + Performance 4 − Risk 4 = 13
       Anchor: Diagonal accent slash + noise texture
       ═══════════════════════════════════════════════════════════════ */

    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── DESIGN TOKENS ─────────────────────────────────────────── */
    :root {
        /* Brand */
        --brand-accent: #F2C811;
        --brand-accent-hover: #FFD84A;
        --brand-accent-muted: rgba(242, 200, 17, 0.12);
        --brand-accent-glow: rgba(242, 200, 17, 0.25);

        /* Surfaces — blue-tinted dark palette (PBI CLI style) */
        --surface-root: #0B0E14;
        --surface-1: #111520;
        --surface-2: #181D2A;
        --surface-3: #1E2536;
        --surface-4: #252D3D;
        --surface-raised: #2C3548;

        /* Glass */
        --glass-bg: rgba(255, 255, 255, 0.04);
        --glass-border: rgba(255, 255, 255, 0.08);
        --glass-hover: rgba(255, 255, 255, 0.07);

        /* Text */
        --text-primary: #E8ECF4;
        --text-secondary: #8B95A8;
        --text-muted: #5A6478;
        --text-inverse: #0B0E14;

        /* Semantic — status colors */
        --status-ok: #10B981;
        --status-ok-bg: rgba(16, 185, 129, 0.10);
        --status-warn: #F59E0B;
        --status-warn-bg: rgba(245, 158, 11, 0.10);
        --status-danger: #D13438;
        --status-danger-bg: rgba(209, 52, 56, 0.10);
        --status-info: #0078D4;
        --status-info-bg: rgba(0, 120, 212, 0.10);

        /* Category colors — per fixer/section type */
        --cat-report: #3B82F6;
        --cat-report-dim: rgba(59, 130, 246, 0.12);
        --cat-model: #8B5CF6;
        --cat-model-dim: rgba(139, 92, 246, 0.12);
        --cat-bpa: #10B981;
        --cat-bpa-dim: rgba(16, 185, 129, 0.12);
        --cat-memory: #EC4899;
        --cat-memory-dim: rgba(236, 72, 153, 0.12);
        --cat-perf: #F59E0B;
        --cat-perf-dim: rgba(245, 158, 11, 0.12);

        /* Borders — visible blue-gray tint */
        --border-subtle: #1A2030;
        --border-default: #252D3D;
        --border-strong: #354155;
        --border-accent: rgba(242, 200, 17, 0.35);

        /* Shadows */
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.35);
        --shadow-lg: 0 8px 32px rgba(0,0,0,0.45);
        --shadow-xl: 0 16px 48px rgba(0,0,0,0.5);
        --shadow-glow: 0 0 24px var(--brand-accent-glow);

        /* Radius */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 20px;
        --radius-full: 9999px;

        /* Typography — 3-tier system */
        --font-display: 'Space Grotesk', 'DM Sans', system-ui, sans-serif;
        --font-body: 'DM Sans', system-ui, -apple-system, sans-serif;
        --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;

        /* Motion */
        --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
        --duration-fast: 150ms;
        --duration-normal: 200ms;
        --duration-slow: 350ms;
    }

    /* ── GLOBAL RESETS ──────────────────────────────────────────── */
    *:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not(.material-symbols-outlined):not(.material-icons) {
        font-family: var(--font-body) !important;
    }

    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
    }

    html, body, [data-testid="stAppViewContainer"],
    .main, [data-testid="stApp"] {
        background: var(--surface-root) !important;
        color: var(--text-primary);
    }

    /* Subtle grid background texture */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
        background-size: 64px 64px;
        pointer-events: none;
        z-index: 0;
    }

    /* Noise grain overlay — adds tactile depth (canvas-design principle) */
    [data-testid="stAppViewContainer"]::after {
        content: '';
        position: fixed;
        inset: 0;
        opacity: 0.025;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 0;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, .stDeployButton { display: none !important; }
    header[data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: 1px solid var(--border-subtle);
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: var(--surface-raised);
        border-radius: var(--radius-full);
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    /* ── SIDEBAR TOGGLE ICONS ──────────────────────────────────── */
    button[data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] button span {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    }

    button[data-testid="stSidebarCollapseButton"]:hover {
        color: var(--brand-accent) !important;
    }

    [data-testid="collapsedControl"] {
        background: var(--surface-2) !important;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        border: 1px solid var(--border-default);
        border-left: none;
    }

    [data-testid="collapsedControl"] button {
        color: var(--brand-accent) !important;
        background: transparent !important;
    }

    [data-testid="collapsedControl"] button span {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
        color: var(--brand-accent) !important;
    }

    /* ── SIDEBAR ───────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: var(--surface-1) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Sidebar metrics — glass cards */
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: var(--glass-bg);
        padding: 0.75rem 1rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--glass-border);
        transition: border-color var(--duration-normal) var(--ease-out);
    }

    [data-testid="stSidebar"] [data-testid="stMetric"]:hover {
        border-color: var(--border-accent);
    }

    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-family: var(--font-mono) !important;
        font-weight: 600;
        color: var(--brand-accent) !important;
    }

    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted) !important;
    }

    /* Sidebar buttons */
    [data-testid="stSidebar"] button {
        background: var(--brand-accent) !important;
        color: var(--text-inverse) !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all var(--duration-normal) var(--ease-out) !important;
        cursor: pointer !important;
    }

    [data-testid="stSidebar"] button:hover {
        background: var(--brand-accent-hover) !important;
        box-shadow: var(--shadow-glow) !important;
    }

    /* ── MAIN CONTAINER ────────────────────────────────────────── */
    .main .block-container {
        max-width: 1400px;
        padding: 2rem 2.5rem !important;
    }

    /* ── APP HEADER ────────────────────────────────────────────── */
    .app-header {
        background: var(--surface-2);
        padding: 2rem 2.5rem;
        border-radius: var(--radius-lg);
        margin-bottom: 1.75rem;
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--brand-accent);
        position: relative;
        overflow: hidden;
    }

    /* DIFFERENTIATION ANCHOR — diagonal accent slash
       "If screenshotted with logo removed, how would someone recognize it?"
       Answer: the signature diagonal yellow cut across the header corner. */
    .app-header::after {
        content: '';
        position: absolute;
        top: -20px;
        right: -20px;
        width: 120px;
        height: 120px;
        background: var(--brand-accent);
        opacity: 0.06;
        transform: rotate(45deg);
        pointer-events: none;
    }

    .app-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 160px; height: 100%;
        background: linear-gradient(90deg, var(--brand-accent-muted), transparent);
        pointer-events: none;
    }

    .app-header h1 {
        color: var(--text-primary);
        font-family: var(--font-display) !important;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.04em;
        position: relative;
        z-index: 1;
    }

    .app-header h1 .highlight {
        color: var(--brand-accent);
    }

    .app-header p {
        color: var(--text-secondary);
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }

    /* ── TABS ──────────────────────────────────────────────────── */
    .stTabs {
        background: transparent;
        border-radius: 0;
        padding: 0;
        box-shadow: none;
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--surface-1);
        border-radius: var(--radius-lg);
        padding: 4px;
        border: 1px solid var(--border-subtle);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: var(--radius-md);
        color: var(--text-muted);
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.65rem 1.25rem;
        transition: all var(--duration-normal) var(--ease-out);
        border: none;
        cursor: pointer;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary);
        background: var(--glass-hover);
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--brand-accent) !important;
        color: var(--text-inverse) !important;
        font-weight: 600;
        box-shadow: var(--shadow-sm);
    }

    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* ── METRIC CARDS ──────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--surface-2);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        transition: all var(--duration-normal) var(--ease-out);
    }

    [data-testid="stMetric"]:hover {
        border-color: var(--border-accent);
        box-shadow: var(--shadow-md);
    }

    [data-testid="stMetricValue"] {
        font-family: var(--font-mono) !important;
        font-weight: 600;
        color: var(--text-primary) !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted) !important;
        font-weight: 500;
    }

    /* ── BUTTONS ────────────────────────────────────────────────── */
    .stButton > button {
        background: var(--brand-accent);
        color: var(--text-inverse);
        border: none;
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.6rem 1.4rem;
        transition: all var(--duration-normal) var(--ease-out);
        cursor: pointer;
        letter-spacing: -0.01em;
    }

    .stButton > button:hover {
        background: var(--brand-accent-hover);
        box-shadow: var(--shadow-glow);
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    .stButton > button[kind="secondary"] {
        background: transparent;
        color: var(--text-primary);
        border: 1px solid var(--border-default);
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: var(--brand-accent);
        background: var(--brand-accent-muted);
        color: var(--brand-accent);
    }

    /* ── TEXT INPUTS ────────────────────────────────────────────── */
    .stTextInput > div > div > input {
        background: var(--surface-2) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-size: 0.9rem;
        padding: 0.7rem 1rem;
        transition: all var(--duration-normal) var(--ease-out);
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--brand-accent) !important;
        box-shadow: 0 0 0 3px var(--brand-accent-muted) !important;
        background: var(--surface-3) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
    }

    /* ── DATAFRAMES (glide-data-grid wrapper) ─────────────────── */
    .stDataFrame, [data-testid="stDataFrame"] {
        border-radius: var(--radius-lg) !important;
        overflow: hidden;
        border: 1px solid var(--border-default) !important;
    }

    /* Force dark on the iframe/canvas container */
    .stDataFrame > div,
    [data-testid="stDataFrame"] > div {
        border-radius: var(--radius-lg) !important;
    }

    /* Native table fallback (st.table) */
    .stDataFrame table, .stTable table {
        font-size: 0.85rem;
        background: var(--surface-1) !important;
    }

    .stDataFrame thead th, .stTable thead th {
        background: var(--surface-3) !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.06em;
        border-bottom: 1px solid var(--border-default) !important;
    }

    .stDataFrame tbody td, .stTable tbody td {
        background: var(--surface-1) !important;
        color: var(--text-primary) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }

    .stDataFrame tbody tr:hover td, .stTable tbody tr:hover td {
        background: var(--surface-2) !important;
    }

    /* Glide data grid header override */
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-family: var(--font-body) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── EXPANDERS ──────────────────────────────────────────────── */
    [data-testid="stExpander"] {
        background: var(--surface-2);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md) !important;
        overflow: hidden;
        margin-bottom: 0.5rem;
    }

    [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
        font-weight: 600;
        padding: 0.75rem 1rem;
    }

    [data-testid="stExpander"] summary:hover {
        background: var(--glass-hover);
    }

    [data-testid="stExpander"] span[data-testid="stIconMaterial"],
    [data-testid="stExpander"] svg,
    details summary span {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    }

    /* ── ALERTS ─────────────────────────────────────────────────── */
    .stAlert {
        border-radius: var(--radius-md) !important;
        border-left-width: 3px !important;
        border-color: var(--border-subtle) !important;
        background: var(--surface-2) !important;
        color: var(--text-primary) !important;
    }

    div[data-baseweb="notification"] {
        border-radius: var(--radius-md);
        background: var(--surface-2) !important;
    }

    /* ── CHARTS (Plotly) ───────────────────────────────────────── */
    .js-plotly-plot {
        border-radius: var(--radius-lg);
        overflow: hidden;
    }

    .js-plotly-plot .main-svg {
        background: transparent !important;
    }

    /* ── DIVIDERS ───────────────────────────────────────────────── */
    hr {
        border: none;
        height: 1px;
        background: var(--border-subtle);
        margin: 1.5rem 0;
    }

    /* ── DOWNLOAD BUTTONS ──────────────────────────────────────── */
    .stDownloadButton > button {
        background: var(--surface-3) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 500 !important;
        transition: all var(--duration-normal) var(--ease-out) !important;
        cursor: pointer !important;
    }

    .stDownloadButton > button:hover {
        border-color: var(--brand-accent) !important;
        background: var(--brand-accent-muted) !important;
        color: var(--brand-accent) !important;
    }

    /* ── MULTISELECT / SELECT ──────────────────────────────────── */
    [data-baseweb="select"] > div {
        background: var(--surface-2) !important;
        border-color: var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
    }

    [data-baseweb="select"] > div:focus-within {
        border-color: var(--brand-accent) !important;
        box-shadow: 0 0 0 3px var(--brand-accent-muted) !important;
    }

    [data-baseweb="popover"] > div {
        background: var(--surface-3) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
    }

    [data-baseweb="menu"] li {
        color: var(--text-primary) !important;
    }

    [data-baseweb="menu"] li:hover {
        background: var(--glass-hover) !important;
    }

    /* ── CHECKBOX ───────────────────────────────────────────────── */
    .stCheckbox label {
        color: var(--text-secondary) !important;
    }

    .stCheckbox [data-baseweb="checkbox"] div {
        border-color: var(--border-default) !important;
    }

    /* ── WELCOME CONTAINER ─────────────────────────────────────── */
    .welcome-container {
        background: var(--surface-2);
        border-radius: var(--radius-xl);
        padding: 3rem 3.5rem;
        border: 1px solid var(--border-subtle);
        position: relative;
        overflow: hidden;
    }

    /* Top accent line */
    .welcome-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--brand-accent), transparent 60%);
    }

    /* Diagonal slash anchor (matches header) */
    .welcome-container::after {
        content: '';
        position: absolute;
        bottom: -30px; right: -30px;
        width: 140px; height: 140px;
        background: var(--brand-accent);
        opacity: 0.04;
        transform: rotate(45deg);
        pointer-events: none;
    }

    .welcome-container h2 {
        color: var(--text-primary);
        font-weight: 800;
        font-size: 1.6rem;
        letter-spacing: -0.03em;
        margin-bottom: 0.75rem;
    }

    /* ── FEATURE CARDS (PBI CLI style with ::before stripe) ──── */
    .feature-card {
        background: var(--surface-2);
        padding: 1.25rem 1.5rem;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-default);
        transition: all 0.25s var(--ease-out);
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }

    .feature-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
        background: var(--brand-accent);
        opacity: 0;
        transition: opacity 0.25s;
    }

    .feature-card:hover {
        background: var(--surface-3);
        border-color: var(--brand-accent);
        transform: translateY(-1px);
    }

    .feature-card:hover::before { opacity: 1; }

    .feature-card h4 {
        margin: 0 0 0.3rem 0;
        color: var(--text-primary) !important;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: -0.01em;
    }

    .feature-card p {
        color: var(--text-secondary) !important;
        font-size: 12.5px;
        line-height: 1.5;
        margin: 0;
    }

    .feature-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: var(--radius-sm);
        background: var(--brand-accent-muted);
        color: var(--brand-accent);
        font-size: 14px;
        margin-bottom: 0.65rem;
        font-weight: 700;
        border: 1px solid rgba(242,200,17,0.15);
    }

    /* ── CMD BADGE (monospace tag for fixer IDs) ───────────── */
    .cmd-badge {
        font-family: var(--font-mono) !important;
        font-size: 10px;
        font-weight: 500;
        padding: 1px 6px;
        border-radius: 4px;
        background: rgba(255,255,255,0.06);
        color: var(--text-muted);
    }

    /* ── STATUS DOTS (animated indicators) ─────────────────── */
    .status-dot {
        display: inline-block;
        width: 7px; height: 7px;
        border-radius: 50%;
        background: var(--text-muted);
        vertical-align: middle;
        margin-right: 6px;
    }
    .status-dot.ok { background: var(--status-ok); box-shadow: 0 0 6px rgba(16,185,129,0.5); }
    .status-dot.warn { background: var(--status-warn); box-shadow: 0 0 6px rgba(245,158,11,0.4); }
    .status-dot.danger { background: var(--status-danger); }

    @keyframes statusPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── SCORE DISPLAY ─────────────────────────────────────────── */
    .score-container {
        background: var(--surface-2);
        border-radius: var(--radius-xl);
        padding: 2rem;
        border: 1px solid var(--border-subtle);
        text-align: center;
    }

    .score-badge {
        display: inline-block;
        padding: 0.35rem 1.25rem;
        border-radius: var(--radius-full);
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 1rem;
    }

    .score-badge.excellent {
        background: var(--status-ok-bg);
        color: var(--status-ok);
        border: 1px solid rgba(52, 211, 153, 0.2);
    }

    .score-badge.good {
        background: var(--status-info-bg);
        color: var(--status-info);
        border: 1px solid rgba(96, 165, 250, 0.2);
    }

    .score-badge.warning {
        background: var(--status-warn-bg);
        color: var(--status-warn);
        border: 1px solid rgba(251, 191, 36, 0.2);
    }

    .score-badge.poor {
        background: var(--status-danger-bg);
        color: var(--status-danger);
        border: 1px solid rgba(248, 113, 113, 0.2);
    }

    /* ── SECTION HEADERS — Space Grotesk display font ─────────── */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        letter-spacing: -0.03em;
    }

    p, span, li, label, div {
        color: var(--text-secondary);
    }

    /* Markdown text in main area */
    .stMarkdown p {
        color: var(--text-secondary) !important;
    }

    .stMarkdown h4, .stMarkdown h3, .stMarkdown h2 {
        color: var(--text-primary) !important;
    }

    .stMarkdown strong {
        color: var(--text-primary) !important;
        font-weight: 600;
    }

    .stMarkdown code {
        background: var(--surface-3) !important;
        color: var(--brand-accent) !important;
        padding: 0.15rem 0.4rem;
        border-radius: var(--radius-sm);
        font-family: var(--font-mono) !important;
        font-size: 0.85em;
    }

    /* Caption */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-muted) !important;
    }

    /* ── BADGES ─────────────────────────────────────────────────── */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: var(--radius-full);
        font-size: 0.68rem;
        font-weight: 600;
        margin-right: 0.4rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 1px solid transparent;
    }

    .badge-report {
        background: var(--cat-report-dim);
        color: var(--cat-report);
        border-color: rgba(59, 130, 246, 0.2);
    }

    .badge-model {
        background: var(--cat-model-dim);
        color: var(--cat-model);
        border-color: rgba(139, 92, 246, 0.2);
    }

    .badge-bpa {
        background: var(--cat-bpa-dim);
        color: var(--cat-bpa);
        border-color: rgba(16, 185, 129, 0.2);
    }

    .badge-fixable {
        background: var(--brand-accent-muted);
        color: var(--brand-accent);
        border-color: rgba(242, 200, 17, 0.2);
    }

    /* ── RESPONSIVE ────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem !important;
        }
        .app-header {
            padding: 1.5rem;
        }
        .app-header h1 {
            font-size: 1.35rem;
        }
        .welcome-container {
            padding: 2rem;
        }
    }

    /* ── TOUCH TARGETS (44px minimum per Apple/Google) ────────── */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stSidebar"] button {
        min-height: 44px !important;
    }

    /* ── ENTRANCE ANIMATION ────────────────────────────────────── */
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stTabs [role="tabpanel"] {
        animation: fadeSlideIn 0.3s var(--ease-out);
    }

    /* ── FOCUS STATES (Accessibility) ──────────────────────────── */
    *:focus-visible {
        outline: 2px solid var(--brand-accent) !important;
        outline-offset: 2px;
        border-radius: var(--radius-sm);
    }

    /* All clickable elements */
    button, a, [role="button"], [role="tab"],
    .stButton > button, .stDownloadButton > button,
    [data-baseweb="tab"],
    .feature-card {
        cursor: pointer !important;
    }

    /* ── SPINNER / LOADING ─────────────────────────────────────── */
    .stSpinner > div {
        border-color: var(--brand-accent) transparent transparent transparent !important;
    }

    /* ── PROGRESS BARS ─────────────────────────────────────────── */
    [data-testid="stProgress"] > div > div {
        background: var(--brand-accent) !important;
    }

    /* ── TOAST / SUCCESS MESSAGES ───────────────────────────────── */
    [data-testid="stToast"] {
        background: var(--surface-3) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-lg) !important;
        color: var(--text-primary) !important;
    }

    /* ── SIDEBAR DIVIDER ───────────────────────────────────────── */
    [data-testid="stSidebar"] hr {
        border-color: var(--border-subtle) !important;
        opacity: 0.5;
    }

    /* ── PLOTLY MODEBAR ────────────────────────────────────────── */
    .modebar-btn path {
        fill: var(--text-muted) !important;
    }
    .modebar-btn:hover path {
        fill: var(--brand-accent) !important;
    }

    /* ── REDUCED MOTION ────────────────────────────────────────── */
    @media (prefers-reduced-motion: reduce) {
        * {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
</style>
"""
