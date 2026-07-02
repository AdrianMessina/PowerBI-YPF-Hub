"""
YPF BI Monitor - Shared Styles Module
Design System: Industrial Data Observatory (v3.1)
Display: Space Grotesk | Body: DM Sans | Data: JetBrains Mono
Anchor: Diagonal accent slash + noise texture
"""
import streamlit as st
from pathlib import Path


# Design tokens (Python-accessible, mirror of CSS vars)
YPF_ACCENT = "#F2C811"        # YPF Yellow — surgical accent
YPF_ACCENT_HOVER = "#FFD84A"
SURFACE_ROOT = "#0B0E14"
SURFACE_1 = "#111520"
SURFACE_2 = "#181D2A"
SURFACE_3 = "#1E2536"
TEXT_PRIMARY = "#E8ECF4"
TEXT_SECONDARY = "#8B95A8"
TEXT_MUTED = "#5A6478"
BORDER_SUBTLE = "#1A2030"
BORDER_DEFAULT = "#252D3D"


def get_shared_css():
    """Return Industrial Data Observatory CSS — unified design system for the suite."""
    return """
    <style>
    /* ═══════════════════════════════════════════════════════════════
       YPF BI MONITOR — DESIGN SYSTEM v3.1
       "Industrial Data Observatory"
       Display: Space Grotesk | Body: DM Sans | Data: JetBrains Mono
       Anchor: Diagonal accent slash + noise texture
       ═══════════════════════════════════════════════════════════════ */

    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── DESIGN TOKENS ─────────────────────────────────────────── */
    :root {
        --brand-accent: #F2C811;
        --brand-accent-hover: #FFD84A;
        --brand-accent-muted: rgba(242, 200, 17, 0.12);
        --brand-accent-glow: rgba(242, 200, 17, 0.25);

        --surface-root: #0B0E14;
        --surface-1: #111520;
        --surface-2: #181D2A;
        --surface-3: #1E2536;
        --surface-4: #252D3D;
        --surface-raised: #2C3548;

        --glass-bg: rgba(255, 255, 255, 0.04);
        --glass-border: rgba(255, 255, 255, 0.08);
        --glass-hover: rgba(255, 255, 255, 0.07);

        --text-primary: #E8ECF4;
        --text-secondary: #8B95A8;
        --text-muted: #5A6478;
        --text-inverse: #0B0E14;

        --status-ok: #10B981;
        --status-ok-bg: rgba(16, 185, 129, 0.10);
        --status-warn: #F59E0B;
        --status-warn-bg: rgba(245, 158, 11, 0.10);
        --status-danger: #D13438;
        --status-danger-bg: rgba(209, 52, 56, 0.10);
        --status-info: #0078D4;
        --status-info-bg: rgba(0, 120, 212, 0.10);

        --cat-report: #3B82F6;
        --cat-report-dim: rgba(59, 130, 246, 0.12);
        --cat-model: #8B5CF6;
        --cat-model-dim: rgba(139, 92, 246, 0.12);
        --cat-bpa: #10B981;
        --cat-bpa-dim: rgba(16, 185, 129, 0.12);

        --border-subtle: #1A2030;
        --border-default: #252D3D;
        --border-strong: #354155;
        --border-accent: rgba(242, 200, 17, 0.35);

        --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.35);
        --shadow-lg: 0 8px 32px rgba(0,0,0,0.45);
        --shadow-glow: 0 0 24px var(--brand-accent-glow);

        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 20px;
        --radius-full: 9999px;

        --font-display: 'Space Grotesk', 'DM Sans', system-ui, sans-serif;
        --font-body: 'DM Sans', system-ui, -apple-system, sans-serif;
        --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;

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

    /* Noise grain overlay */
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

    /* ── MAIN CONTAINER ────────────────────────────────────────── */
    .main .block-container {
        max-width: 1400px;
        padding: 2rem 2.5rem !important;
    }

    /* ── APP HEADER (.ypf-header) ──────────────────────────────── */
    .ypf-header {
        background: var(--surface-2);
        padding: 2rem 2.5rem;
        border-radius: var(--radius-lg);
        margin-bottom: 1.75rem;
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--brand-accent);
        position: relative;
        overflow: hidden;
    }

    /* DIFFERENTIATION ANCHOR — diagonal accent slash */
    .ypf-header::after {
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

    .ypf-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 160px; height: 100%;
        background: linear-gradient(90deg, var(--brand-accent-muted), transparent);
        pointer-events: none;
    }

    .ypf-header h1 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.04em;
        position: relative;
        z-index: 1;
    }

    .ypf-header .subtitle {
        color: var(--text-secondary);
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }

    .ypf-header .version {
        display: inline-block;
        font-family: var(--font-mono) !important;
        color: var(--brand-accent);
        font-size: 0.7rem;
        margin: 0.6rem 0 0 0;
        padding: 0.15rem 0.5rem;
        background: var(--brand-accent-muted);
        border-radius: var(--radius-sm);
        border: 1px solid rgba(242,200,17,0.18);
        position: relative;
        z-index: 1;
    }

    /* ── SECTION HEADERS ───────────────────────────────────────── */
    .section-header {
        background: var(--surface-2);
        border-left: 3px solid var(--brand-accent);
        padding: 0.6rem 1rem;
        font-weight: 600;
        margin: 1.25rem 0 0.75rem 0;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        font-size: 0.9rem;
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        letter-spacing: -0.01em;
    }

    /* ── HELP / INFO BOXES ─────────────────────────────────────── */
    .help-box {
        background: var(--surface-2);
        border-left: 3px solid var(--brand-accent);
        padding: 1rem 1.25rem;
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        margin: 0.75rem 0;
        color: var(--text-secondary);
        border-top: 1px solid var(--border-subtle);
        border-right: 1px solid var(--border-subtle);
        border-bottom: 1px solid var(--border-subtle);
    }

    /* ── BUTTONS ────────────────────────────────────────────────── */
    .stButton > button {
        background: var(--brand-accent) !important;
        color: var(--text-inverse) !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.6rem 1.4rem !important;
        transition: all var(--duration-normal) var(--ease-out) !important;
        cursor: pointer !important;
        letter-spacing: -0.01em;
        min-height: 44px !important;
    }
    .stButton > button:hover {
        background: var(--brand-accent-hover) !important;
        box-shadow: var(--shadow-glow) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-default) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--brand-accent) !important;
        background: var(--brand-accent-muted) !important;
        color: var(--brand-accent) !important;
    }

    /* ── DOWNLOAD BUTTON ──────────────────────────────────────── */
    .stDownloadButton > button {
        background: var(--surface-3) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        font-weight: 500 !important;
        transition: all var(--duration-normal) var(--ease-out) !important;
        cursor: pointer !important;
        min-height: 44px !important;
    }
    .stDownloadButton > button:hover {
        border-color: var(--brand-accent) !important;
        background: var(--brand-accent-muted) !important;
        color: var(--brand-accent) !important;
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
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
        transition: color var(--duration-normal) var(--ease-out) !important;
    }
    .streamlit-expanderHeader:hover {
        color: var(--brand-accent) !important;
    }

    /* ── METRIC CARDS ──────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--surface-2);
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--brand-accent);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        transition: all var(--duration-normal) var(--ease-out);
    }
    [data-testid="stMetric"]:hover {
        border-color: var(--border-accent);
        border-left-color: var(--brand-accent);
        box-shadow: var(--shadow-md);
    }
    [data-testid="stMetricValue"] {
        font-family: var(--font-mono) !important;
        font-weight: 600 !important;
        color: var(--brand-accent) !important;
        font-size: 1.6rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted) !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }

    /* ── DATAFRAMES ────────────────────────────────────────────── */
    .stDataFrame, [data-testid="stDataFrame"] {
        border-radius: var(--radius-lg) !important;
        overflow: hidden;
        border: 1px solid var(--border-default) !important;
    }
    .stDataFrame table, .stTable table {
        font-size: 0.85rem;
        background: var(--surface-1) !important;
    }
    .stDataFrame thead th, .stTable thead th,
    [data-testid="stDataFrame"] th {
        background: var(--surface-3) !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.7rem !important;
        letter-spacing: 0.06em;
        border-bottom: 1px solid var(--border-default) !important;
    }
    .stDataFrame tbody td, .stTable tbody td {
        background: var(--surface-1) !important;
        color: var(--text-primary) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }
    .stDataFrame tbody tr:hover td, .stTable tbody tr:hover td,
    [data-testid="stDataFrame"] tr:hover td {
        background: var(--surface-2) !important;
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-family: var(--font-body) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
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
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.65rem 1.25rem;
        transition: all var(--duration-normal) var(--ease-out);
        border: none !important;
        cursor: pointer;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background: var(--glass-hover);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"],
    .stTabs [aria-selected="true"] {
        background: var(--brand-accent) !important;
        color: var(--text-inverse) !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-sm);
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* ── TEXT INPUTS ────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: var(--surface-2) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-size: 0.9rem !important;
        padding: 0.7rem 1rem !important;
        transition: all var(--duration-normal) var(--ease-out);
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--brand-accent) !important;
        box-shadow: 0 0 0 3px var(--brand-accent-muted) !important;
        background: var(--surface-3) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
    }

    /* ── SELECTBOX / MULTISELECT ──────────────────────────────── */
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

    /* ── RADIO / CHECKBOX ─────────────────────────────────────── */
    .stRadio [data-baseweb="radio"] {
        cursor: pointer !important;
    }
    .stCheckbox label {
        color: var(--text-secondary) !important;
    }
    .stCheckbox [data-baseweb="checkbox"] div {
        border-color: var(--border-default) !important;
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

    /* ── DIVIDERS ───────────────────────────────────────────────── */
    hr {
        border: none;
        height: 1px;
        background: var(--border-subtle);
        margin: 1.5rem 0;
    }

    /* ── FEATURE CARDS (.feature-card) ─────────────────────────── */
    .feature-card {
        background: var(--surface-2);
        padding: 1.5rem;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-default);
        border-left: 3px solid var(--brand-accent);
        transition: all 0.25s var(--ease-out);
        cursor: default;
        position: relative;
        overflow: hidden;
        margin: 0.5rem 0;
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
        transform: translateX(2px);
        box-shadow: var(--shadow-md);
    }
    .feature-card:hover::before { opacity: 1; }
    .feature-card h3 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        font-size: 1.05rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }
    .feature-card h4 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        font-size: 0.95rem;
        font-weight: 600;
        margin: 0 0 0.4rem 0;
    }
    .feature-card p {
        color: var(--text-secondary) !important;
        font-size: 0.85rem;
        line-height: 1.6;
        margin: 0;
    }
    .feature-card ul {
        color: var(--text-secondary);
        font-size: 0.82rem;
        margin: 0.5rem 0 0 0;
        padding-left: 1.2rem;
        line-height: 1.7;
    }
    .feature-card ul li {
        color: var(--text-secondary);
    }

    /* ── PBIP INPUT SECTION ────────────────────────────────────── */
    .pbip-input-section {
        background: var(--surface-2);
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--brand-accent);
        border-radius: 0 var(--radius-md) var(--radius-md) 0;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
    }

    /* ── FOOTER ─────────────────────────────────────────────────── */
    .ypf-footer {
        text-align: center;
        color: var(--text-muted) !important;
        font-size: 0.72rem;
        font-family: var(--font-body);
        border-top: 1px solid var(--border-subtle);
        padding-top: 1rem;
        margin-top: 2.5rem;
        letter-spacing: 0.03em;
    }

    /* ── LOADER ─────────────────────────────────────────────────── */
    .ypf-loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 2rem;
    }
    .ypf-loader {
        width: 50px;
        height: 50px;
        border: 3px solid var(--surface-3);
        border-top: 3px solid var(--brand-accent);
        border-radius: 50%;
        animation: ypf-spin 1s linear infinite;
    }
    @keyframes ypf-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .ypf-loader-text {
        color: var(--text-secondary);
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    .stSpinner > div {
        border-color: var(--brand-accent) transparent transparent transparent !important;
    }

    /* ── SKELETON ──────────────────────────────────────────────── */
    .skeleton {
        background: linear-gradient(90deg, var(--surface-2) 25%, var(--surface-3) 50%, var(--surface-2) 75%);
        background-size: 200% 100%;
        animation: skeleton-pulse 1.5s ease-in-out infinite;
        border-radius: var(--radius-sm);
        height: 1rem;
        margin: 0.5rem 0;
    }
    .skeleton-card {
        background: var(--surface-2);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1.5rem;
    }
    .skeleton-card .skeleton-title {
        height: 1.4rem;
        width: 60%;
        margin-bottom: 1rem;
    }
    .skeleton-card .skeleton-text {
        height: 0.9rem;
        width: 90%;
        margin-bottom: 0.5rem;
    }
    .skeleton-card .skeleton-text:last-child {
        width: 70%;
    }
    @keyframes skeleton-pulse {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ── STATUS DOTS ───────────────────────────────────────────── */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .status-dot.active, .status-dot.ok { background: var(--status-ok); box-shadow: 0 0 6px rgba(16,185,129,0.5); }
    .status-dot.warning, .status-dot.warn { background: var(--status-warn); box-shadow: 0 0 6px rgba(245,158,11,0.4); }
    .status-dot.error, .status-dot.danger { background: var(--status-danger); }

    /* ── TYPOGRAPHY (Headings + Text) ──────────────────────────── */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        letter-spacing: -0.03em;
    }

    .stMarkdown p,
    .stMarkdown li {
        color: var(--text-secondary) !important;
    }
    .stMarkdown h4, .stMarkdown h3, .stMarkdown h2, .stMarkdown h1 {
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
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

    code, pre, .stCodeBlock, [data-testid="stCode"] {
        font-family: var(--font-mono) !important;
    }

    /* Captions */
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
    .badge-accent {
        background: var(--brand-accent-muted);
        color: var(--brand-accent);
        border-color: rgba(242, 200, 17, 0.2);
    }

    /* ── CHARTS (Plotly) ──────────────────────────────────────── */
    .js-plotly-plot {
        border-radius: var(--radius-lg);
        overflow: hidden;
    }
    .js-plotly-plot .main-svg {
        background: transparent !important;
    }
    .modebar-btn path { fill: var(--text-muted) !important; }
    .modebar-btn:hover path { fill: var(--brand-accent) !important; }

    /* ── PROGRESS BARS ─────────────────────────────────────────── */
    [data-testid="stProgress"] > div > div {
        background: var(--brand-accent) !important;
    }

    /* ── TOAST ──────────────────────────────────────────────────── */
    [data-testid="stToast"] {
        background: var(--surface-3) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-lg) !important;
        color: var(--text-primary) !important;
    }

    /* ── FILE UPLOADER ─────────────────────────────────────────── */
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {
        background: var(--surface-2) !important;
        border: 1px dashed var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-secondary) !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--brand-accent) !important;
        background: var(--surface-3) !important;
    }

    /* ── ENTRANCE ANIMATION ───────────────────────────────────── */
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

    /* ── RESPONSIVE ────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem !important; }
        .ypf-header { padding: 1.5rem; }
        .ypf-header h1 { font-size: 1.35rem; }
    }

    /* ── REDUCED MOTION ────────────────────────────────────────── */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
    </style>
    """


def render_app_header(title: str, subtitle: str = "", version: str = ""):
    """Render the YPF Industrial Data Observatory app header with diagonal slash anchor.

    Args:
        title: App title (e.g. "Power BI Analyzer")
        subtitle: Short description
        version: Version string (e.g. "1.1")
    """
    version_html = f'<span class="version">v{version}</span>' if version else ''
    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ''

    st.markdown(f"""
    <div class="ypf-header">
        <h1>{title}</h1>
        {subtitle_html}
        {version_html}
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Render the YPF footer with Gerencia de Visualización credit."""
    st.markdown("""
    <div class="ypf-footer">
        YPF S.A. &middot; Gerencia de Visualización &middot; DA&amp;IA &middot; 2026
    </div>
    """, unsafe_allow_html=True)


def render_skeleton(rows: int = 3):
    """Render a skeleton loading placeholder.

    Args:
        rows: Number of skeleton text rows to show
    """
    skeleton_rows = ''.join(
        f'<div class="skeleton skeleton-text" style="width: {90 - i * 10}%;"></div>'
        for i in range(rows)
    )
    st.markdown(f"""
    <div class="skeleton-card">
        <div class="skeleton skeleton-title"></div>
        {skeleton_rows}
    </div>
    """, unsafe_allow_html=True)


def inject_shared_styles():
    """Inject shared CSS into the Streamlit page. Call once at the top of each app."""
    st.markdown(get_shared_css(), unsafe_allow_html=True)
