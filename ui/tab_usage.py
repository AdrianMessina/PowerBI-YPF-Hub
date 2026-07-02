"""Usage Dashboard — whitelist-only analytics on app usage.

Access controlled by config/admin_users.txt (one username per line).
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from core.environment import get_current_user
from core.usage_logger import UsageLogger

# Plotly dark theme
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, DM Sans, sans-serif", color="#8B95A8"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
)


def _load_admin_users() -> set:
    """Load whitelist from config/admin_users.txt"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "admin_users.txt"
    )
    users = set()
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    users.add(line)
    return users


def _get_current_user() -> str:
    return get_current_user()


def render_usage_tab():
    """Render usage dashboard (whitelist only)."""

    current = _get_current_user()
    admins = _load_admin_users()

    if current not in admins:
        st.markdown(
            '<div style="text-align:center; padding: 3rem 2rem;">'
            '<div style="font-size: 2.5rem; margin-bottom: 1rem; opacity: 0.3;">&#128274;</div>'
            '<p style="color: var(--text-secondary); font-size: 1rem;">'
            'Esta seccion es exclusiva para administradores.</p>'
            '<p style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.5rem;">'
            f'Usuario actual: <strong>{current}</strong> — '
            'Contacte al equipo de Data Analytics para solicitar acceso.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Authorized: show dashboard ──────────────────────────────
    logger = _get_or_create_logger()
    events = logger.get_all_events()

    if not events:
        st.info("No hay datos de uso. Los eventos se registran automaticamente al analizar reportes.")
        return

    df = pd.DataFrame(events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date

    for col in ("username", "hostname"):
        if col not in df.columns:
            df[col] = "unknown"
        else:
            df[col] = df[col].fillna("unknown").astype(str)

    # ── Metrics ─────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Eventos", f"{len(df):,}")
    c2.metric("Sesiones", f"{df['session_id'].nunique():,}")
    c3.metric("Usuarios", f"{df['username'].nunique():,}")
    days = max((df["timestamp"].max() - df["timestamp"].min()).days, 1)
    c4.metric("Eventos/dia", f"{len(df)/days:.1f}")

    st.divider()

    sub = st.tabs(["Actividad", "Usuarios", "Reportes", "Datos"])

    with sub[0]:
        _tab_activity(df)
    with sub[1]:
        _tab_users(df)
    with sub[2]:
        _tab_reports(df)
    with sub[3]:
        _tab_raw(df)


def _tab_activity(df):
    daily = df.groupby("date").size().reset_index(name="eventos")
    daily["date"] = pd.to_datetime(daily["date"])

    fig = px.area(daily, x="date", y="eventos")
    fig.update_traces(line_color="#F2C811", fillcolor="rgba(242,200,17,0.08)")
    fig.update_layout(height=280, **_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

    top = df["event"].value_counts().head(10).reset_index()
    top.columns = ["Evento", "Cantidad"]
    fig2 = px.bar(top, x="Cantidad", y="Evento", orientation="h")
    fig2.update_traces(marker_color="#F2C811")
    fig2.update_layout(height=max(200, len(top) * 28), **_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)


def _tab_users(df):
    stats = df.groupby("username").agg(
        sesiones=("session_id", "nunique"),
        eventos=("event", "count"),
        primera=("timestamp", "min"),
        ultima=("timestamp", "max"),
    ).reset_index()
    stats["primera"] = stats["primera"].dt.strftime("%Y-%m-%d %H:%M")
    stats["ultima"] = stats["ultima"].dt.strftime("%Y-%m-%d %H:%M")
    stats.columns = ["Usuario", "Sesiones", "Eventos", "Primera vez", "Ultima vez"]
    stats = stats.sort_values("Eventos", ascending=False)
    st.dataframe(stats, use_container_width=True, hide_index=True)


def _tab_reports(df):
    import json as _json
    analysis = df[df["event"].str.contains("analysis", case=False, na=False)]
    if analysis.empty:
        st.info("No hay analisis registrados.")
        return

    rows = []
    for _, r in analysis.iterrows():
        data = r.get("data", {})
        if isinstance(data, str):
            try:
                data = _json.loads(data)
            except Exception:
                data = {}
        name = data.get("report_name", "")
        if name:
            rows.append({
                "Reporte": name,
                "Score": data.get("score", ""),
                "Paginas": data.get("pages", ""),
                "Visuals": data.get("visuals", ""),
                "Usuario": r.get("username", ""),
                "Fecha": r["timestamp"].strftime("%Y-%m-%d %H:%M"),
            })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("Sin datos detallados de reportes.")


def _tab_raw(df):
    recent = df.sort_values("timestamp", ascending=False).head(100)
    display = recent[["timestamp", "username", "hostname", "event"]].copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display.columns = ["Fecha", "Usuario", "Equipo", "Evento"]
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.download_button(
        "Exportar CSV",
        data=df.to_csv(index=False),
        file_name=f"pbi_fixer_usage_{datetime.now():%Y%m%d}.csv",
        mime="text/csv",
    )


def _get_or_create_logger():
    if "logger" not in st.session_state:
        st.session_state.logger = UsageLogger("PBI_Fixer", "2.0")
    return st.session_state.logger
