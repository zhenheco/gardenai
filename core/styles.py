from __future__ import annotations

import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Open+Sans:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Open Sans', sans-serif;
            color: #14532D;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Poppins', sans-serif;
            color: #14532D;
        }

        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }

        .gai-card {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #BBF7D0;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
            margin-bottom: 1rem;
        }

        .gai-kpi-card {
            background-color: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #BBF7D0;
            text-align: center;
        }

        .gai-kpi-label {
            font-size: 0.875rem;
            color: #64748B;
            margin-bottom: 0.5rem;
        }

        .gai-kpi-value {
            font-size: 1.875rem;
            font-weight: 700;
            color: #15803D;
        }

        .gai-kpi-delta {
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }

        .gai-badge {
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
        }

        .gai-badge-success { background-color: #DCFCE7; color: #16A34A; }
        .gai-badge-warning { background-color: #FEF3C7; color: #D97706; }
        .gai-badge-destructive { background-color: #FEE2E2; color: #DC2626; }
        .gai-badge-info { background-color: #DBEAFE; color: #3B82F6; }

        .gai-hero {
            background: linear-gradient(135deg, #15803D 0%, #14532D 100%);
            padding: 3rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
        }

        .gai-hero h1 { color: white !important; margin: 0; }
        .gai-hero p { color: #BBF7D0 !important; margin: 0.5rem 0 0 0; opacity: 0.9; }

        /* Customizing Streamlit components */
        div[data-testid="stMetricValue"] > div {
            color: #15803D;
            font-weight: 700;
        }
        
        div[data-testid="stExpander"] {
            border: 1px solid #BBF7D0 !important;
            border-radius: 8px !important;
            background-color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero_header(title: str, subtitle: str, emoji: str = "🌱"):
    st.markdown(
        f"""
        <div class="gai-hero">
            <h1>{emoji} {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, delta: str | None = None, icon: str = ""):
    delta_html = ""
    if delta:
        color = "#16A34A" if delta.startswith("+") else "#DC2626"
        delta_html = f'<div class="gai-kpi-delta" style="color: {color}">{delta}</div>'

    st.markdown(
        f"""
        <div class="gai-kpi-card">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
            <div class="gai-kpi-label">{label}</div>
            <div class="gai-kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_ring(score: int, label: str):
    # Simple SVG implementation of a health ring
    color = "#16A34A" if score >= 80 else "#F59E0B" if score >= 50 else "#DC2626"
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1rem;">
            <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#E8F0F1" stroke-width="8" />
                <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="8" 
                    stroke-dasharray="{2.827 * score} 282.7" stroke-dashoffset="0" transform="rotate(-90 50 50)" />
                <text x="50" y="55" font-family="Poppins" font-size="20" font-weight="bold" text-anchor="middle" fill="{color}">{score}</text>
            </svg>
            <div style="margin-top: 0.5rem; font-weight: 600; font-size: 0.875rem;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badge(text: str, kind: str = "info"):
    st.markdown(f'<span class="gai-badge gai-badge-{kind}">{text}</span>', unsafe_allow_html=True)


def render_diff(original: str | list[str], new: str | list[str], lang="de"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Original**")
        if isinstance(original, list):
            for item in original:
                st.markdown(f"- {item}")
        else:
            st.info(original)
    with col2:
        st.markdown("**Proposed**")
        if isinstance(new, list):
            for item in new:
                st.markdown(f"- {item}")
        else:
            st.success(new)
