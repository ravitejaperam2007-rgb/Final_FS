"""
AWARE-AI Enterprise Sidebar Navigation Component.

Provides:
- Active page selection across the 9 enterprise control tower modules
- Real-time system status indicators (Database, ML Engine, Multi-Agent Orchestrator)
- Global active disruption counter badge
"""

from __future__ import annotations

import streamlit as st
from database.connection import DatabaseManager
from database.models import AgentExecution, Shipment, ShipmentStatus


PAGES = [
    ("🌐 1. Global Control Tower", "dashboard"),
    ("📦 2. Shipment Management", "shipments"),
    ("🎯 3. Shipment Risk Analysis", "risk"),
    ("🤖 4. Multi-Agent Intelligence", "agents"),
    ("🔍 5. Root Cause & Impact", "root_cause"),
    ("🛡️ 6. Resilience Planning", "resilience"),
    ("🌊 7. Weather & Maritime", "weather"),
    ("🏭 8. Supplier & Inventory", "inventory"),
    ("⚡ 9. System Monitoring", "monitoring"),
]


def render_sidebar_info(db: DatabaseManager) -> None:
    """Render the sidebar branding, fleet metrics, and system status indicators."""
    st.sidebar.markdown(
        """
        <div style="padding: 5px 0 15px 0; border-bottom: 1px solid #1f2937; margin-bottom: 10px;">
            <h2 style="color: #38bdf8; margin: 0; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px;">
                ⚓ AWARE-AI
            </h2>
            <div style="color: #9ca3af; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;">
                Autonomous Supply Chain Control Tower
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with db.session() as session:
            total_shipments = session.query(Shipment).count()
            in_transit = session.query(Shipment).filter(Shipment.status == ShipmentStatus.IN_TRANSIT).count()
            delayed = session.query(Shipment).filter(Shipment.status == ShipmentStatus.DELAYED).count()
            agent_runs = session.query(AgentExecution).count()
    except Exception:
        total_shipments, in_transit, delayed, agent_runs = 0, 0, 0, 0

    st.sidebar.markdown(
        f"""
        <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #9ca3af;">
                <span>Active Fleet:</span> <strong style="color: #f9fafb;">{in_transit} / {total_shipments}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #9ca3af; margin-top: 4px;">
                <span>Disruptions:</span> <strong style="color: {'#ef4444' if delayed > 0 else '#10b981'};">{delayed} Delayed</strong>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #9ca3af; margin-top: 4px;">
                <span>Agent Cycles:</span> <strong style="color: #38bdf8;">{agent_runs}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(db: DatabaseManager) -> str:
    """Legacy helper for backward compatibility and fallback."""
    render_sidebar_info(db)
    page_labels = [label for label, _ in PAGES]
    page_keys = {label: key for label, key in PAGES}

    selected_label = st.sidebar.radio(
        label="Select Module",
        options=page_labels,
        label_visibility="collapsed",
        index=0,
    )
    return page_keys[selected_label]
