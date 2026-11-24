"""
AWARE-AI Enterprise Design System & Reusable UI Components.

Provides:
- Custom CSS injection for sleek dark-themed aerospace/maritime supply chain command center
- Consistent KPI metric cards with delta & status badges
- Risk indicator badges and alert banners
"""

from __future__ import annotations

import streamlit as st


def apply_custom_theme() -> None:
    """Inject enterprise control tower dark theme and typography."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

            :root {
                --primary: #0284c7;
                --primary-light: #38bdf8;
                --accent: #6366f1;
                --bg-dark: #090d16;
                --card-bg: #111827;
                --card-border: #1f2937;
                --text-main: #f9fafb;
                --text-muted: #9ca3af;
                --danger: #ef4444;
                --warning: #f59e0b;
                --success: #10b981;
                --info: #06b6d4;
            }

            .main .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 98%;
            }

            /* Metric Cards */
            .kpi-card {
                background: linear-gradient(135deg, #111827 0%, #1a2234 100%);
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 18px 20px;
                margin-bottom: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            .kpi-card:hover {
                border-color: #38bdf8;
                transform: translateY(-2px);
            }
            .kpi-title {
                font-size: 0.85rem;
                color: #9ca3af;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 600;
                margin-bottom: 6px;
            }
            .kpi-value {
                font-size: 1.85rem;
                font-weight: 700;
                color: #f9fafb;
                font-family: 'Inter', sans-serif;
            }
            .kpi-subtitle {
                font-size: 0.8rem;
                color: #6b7280;
                margin-top: 4px;
            }

            /* Badges */
            .badge-low {
                background-color: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .badge-medium {
                background-color: rgba(245, 158, 11, 0.15);
                color: #f59e0b;
                border: 1px solid rgba(245, 158, 11, 0.3);
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .badge-high {
                background-color: rgba(239, 68, 68, 0.15);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .badge-critical {
                background-color: rgba(220, 38, 38, 0.25);
                color: #f87171;
                border: 1px solid #ef4444;
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                animation: pulse 2s infinite;
            }

            /* Status Pill */
            .status-pill {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                display: inline-block;
            }

            /* Section Headers */
            .control-tower-header {
                border-left: 4px solid #0284c7;
                padding-left: 14px;
                margin-top: 10px;
                margin-bottom: 20px;
            }

            /* Code / Monospace */
            .mono-text {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                background-color: #1e293b;
                padding: 2px 6px;
                border-radius: 4px;
                color: #38bdf8;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(title: str, value: str | int | float, subtitle: str = "", delta: str | None = None, delta_color: str = "normal") -> None:
    """Render a styled KPI metric card."""
    delta_html = ""
    if delta:
        color = "#10b981" if delta_color == "normal" else "#ef4444"
        delta_html = f"<span style='color: {color}; font-size: 0.8rem; font-weight: 600; margin-left: 6px;'>{delta}</span>"

    html = f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}{delta_html}</div>
        {f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def risk_badge_html(level: str) -> str:
    """Return an HTML snippet for a risk badge."""
    lvl = (level or "low").lower()
    if "crit" in lvl:
        cls = "badge-critical"
    elif "high" in lvl:
        cls = "badge-high"
    elif "med" in lvl:
        cls = "badge-medium"
    else:
        cls = "badge-low"
    return f"<span class='{cls}'>{level.upper()}</span>"
