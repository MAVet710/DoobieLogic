from __future__ import annotations

import streamlit as st

COLOR_TOKENS = {
    "bg": "#eef3f7",
    "surface": "#f8fbff",
    "surface_alt": "#e8f0fb",
    "ink": "#0f2740",
    "ink_muted": "#4f6278",
    "accent": "#2f80ed",
    "accent_soft": "rgba(47, 128, 237, 0.14)",
    "success": "#219653",
    "warning": "#f2994a",
    "danger": "#eb5757",
    "border": "#d3deec",
    "shadow": "0 16px 32px rgba(17, 38, 66, 0.08)",
    "radius": "16px",
}


def apply_buyer_dashboard_theme() -> None:
    """Inject a shared visual system so DoobieLogic aligns with Buyer Dashboard styling."""

    st.markdown(
        f"""
        <style>
            :root {{
                --dl-bg: {COLOR_TOKENS['bg']};
                --dl-surface: {COLOR_TOKENS['surface']};
                --dl-surface-alt: {COLOR_TOKENS['surface_alt']};
                --dl-ink: {COLOR_TOKENS['ink']};
                --dl-muted: {COLOR_TOKENS['ink_muted']};
                --dl-accent: {COLOR_TOKENS['accent']};
                --dl-accent-soft: {COLOR_TOKENS['accent_soft']};
                --dl-success: {COLOR_TOKENS['success']};
                --dl-warning: {COLOR_TOKENS['warning']};
                --dl-danger: {COLOR_TOKENS['danger']};
                --dl-border: {COLOR_TOKENS['border']};
                --dl-radius: {COLOR_TOKENS['radius']};
                --dl-shadow: {COLOR_TOKENS['shadow']};
            }}

            .stApp {{
                background: radial-gradient(circle at top right, #ffffff 0%, var(--dl-bg) 45%, #e2ecf9 100%);
                color: var(--dl-ink);
            }}

            .block-container {{
                max-width: 1200px;
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }}

            section[data-testid="stSidebar"] {{
                background: linear-gradient(165deg, #102840 0%, #17385c 90%);
                border-right: 1px solid rgba(255,255,255,0.08);
            }}
            section[data-testid="stSidebar"] * {{
                color: #eef6ff !important;
            }}
            section[data-testid="stSidebar"] [data-baseweb="select"] > div,
            section[data-testid="stSidebar"] .stTextInput input {{
                background: rgba(237, 246, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.25);
            }}

            .dl-hero {{
                background: linear-gradient(135deg, #17395f 0%, #1f4c80 75%, #2f80ed 100%);
                border-radius: 20px;
                box-shadow: var(--dl-shadow);
                padding: 1.5rem 1.75rem;
                color: #f5faff;
                margin-bottom: 1.2rem;
            }}
            .dl-hero h1, .dl-hero h2, .dl-hero p {{ color: #f5faff !important; margin: 0; }}
            .dl-hero p {{ margin-top: 0.55rem; opacity: 0.93; }}

            .dl-section {{
                background: var(--dl-surface);
                border: 1px solid var(--dl-border);
                border-radius: var(--dl-radius);
                box-shadow: var(--dl-shadow);
                padding: 1rem 1.1rem;
                margin-bottom: 1rem;
            }}

            .dl-kpi-grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(170px,1fr)); gap:0.85rem; margin: 0.8rem 0 1rem; }}
            .dl-kpi {{
                background: linear-gradient(180deg, #ffffff 0%, #f4f8fe 100%);
                border: 1px solid var(--dl-border);
                border-radius: 12px;
                padding: 0.8rem;
            }}
            .dl-kpi-label {{ color: var(--dl-muted); font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
            .dl-kpi-value {{ color: var(--dl-ink); font-size: 1.2rem; font-weight: 700; margin-top: 0.2rem; }}

            .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
                border-radius: 10px;
                border: 1px solid #2d75d8;
                background: linear-gradient(180deg, #3990ff 0%, #2f80ed 100%);
                color: white;
                font-weight: 600;
                box-shadow: 0 6px 14px rgba(47, 128, 237, 0.30);
            }}
            .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
                background: linear-gradient(180deg, #2f80ed 0%, #2369c6 100%);
                border-color: #1f5cae;
            }}

            .stTextInput input, .stTextArea textarea, .stNumberInput input,
            [data-baseweb="select"] > div,
            [data-baseweb="select"] input,
            .stDateInput input {{
                border-radius: 10px !important;
                border: 1px solid var(--dl-border) !important;
                background: #fff !important;
                color: var(--dl-ink) !important;
            }}

            [data-testid="stFileUploader"] {{
                background: var(--dl-surface-alt);
                border: 1px dashed #7fa4d8;
                border-radius: 12px;
                padding: 0.4rem 0.6rem;
            }}

            [data-testid="stDataFrame"], div[data-testid="stTable"] {{
                border: 1px solid var(--dl-border);
                border-radius: 14px;
                overflow: hidden;
                box-shadow: var(--dl-shadow);
            }}

            [data-testid="stExpander"] {{
                border: 1px solid var(--dl-border);
                border-radius: 12px;
                background: var(--dl-surface);
            }}

            [data-testid="stAlert"] {{ border-radius: 12px; border: 1px solid var(--dl-border); }}
            [data-testid="stAlert"] p {{ font-weight: 500; }}

            .dl-pill {{
                display:inline-block;
                padding: 0.18rem 0.6rem;
                border-radius: 999px;
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.02em;
                margin-right: 0.35rem;
            }}
            .dl-pill-accent {{ background: var(--dl-accent-soft); color: var(--dl-accent); }}
            .dl-pill-success {{ background: rgba(33,150,83,.14); color: var(--dl-success); }}
            .dl-pill-warning {{ background: rgba(242,153,74,.16); color: #8a520f; }}
            .dl-pill-danger {{ background: rgba(235,87,87,.16); color: #9e1e1e; }}

            .dl-muted {{ color: var(--dl-muted); }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="dl-hero">
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_open() -> None:
    st.markdown('<div class="dl-section">', unsafe_allow_html=True)


def section_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
