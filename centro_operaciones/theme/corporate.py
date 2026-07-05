"""Paleta y estilos corporativos — Óptica Los Andes."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

COLORS = {
    "primary": "#2563eb",
    "primary_dark": "#1E3A5F",
    "primary_light": "#3b82f6",
    "accent": "#1d4ed8",
    "bg_page": "#eef4ff",
    "bg_card": "#ffffff",
    "bg_sidebar": "#f1f5f9",
    "border": "#e2e8f0",
    "text": "#0f172a",
    "text_muted": "#64748b",
    "success": "#16a34a",
    "warning": "#f59e0b",
    "danger": "#dc2626",
}

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def inject_corporate_css() -> None:
    """Inyecta CSS corporativo en la app Streamlit."""
    css_file = ASSETS_DIR / "styles.css"
    extra = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
    st.markdown(
        f"""
        <style>
        :root {{
            --ola-primary: {COLORS["primary"]};
            --ola-primary-dark: {COLORS["primary_dark"]};
            --ola-bg: {COLORS["bg_page"]};
        }}
        .stApp {{
            background: linear-gradient(160deg, #eef4ff 0%, #f5f8ff 45%, #eaf6ff 100%);
        }}
        div[data-testid="stSidebar"] {{
            background: {COLORS["bg_sidebar"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        div[data-testid="stSidebar"] .stRadio label {{
            font-weight: 500;
        }}
        .ola-header {{
            background: linear-gradient(135deg, {COLORS["primary_dark"]} 0%, {COLORS["primary"]} 100%);
            color: white;
            padding: 1.25rem 1.5rem;
            border-radius: 14px;
            margin-bottom: 1rem;
            box-shadow: 0 4px 14px rgba(30, 58, 95, 0.18);
        }}
        .ola-header h1 {{
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
        }}
        .ola-header p {{
            margin: 0.35rem 0 0;
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        .ola-kpi {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            padding: 14px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }}
        .ola-kpi .label {{
            color: {COLORS["text_muted"]};
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .ola-kpi .value {{
            color: {COLORS["primary_dark"]};
            font-size: 1.75rem;
            font-weight: 800;
            margin-top: 4px;
        }}
        .ola-toolbar {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 0.5rem 0;
        }}
        .pendiente-badge {{
            background: #fef3c7;
            color: #92400e;
            padding: 8px 14px;
            border-radius: 10px;
            font-weight: 700;
        }}
        .kpi-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px;
            text-align: center;
        }}
        {extra}
        </style>
        """,
        unsafe_allow_html=True,
    )