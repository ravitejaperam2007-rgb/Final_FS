"""
AWARE-AI — Enterprise Supply Chain Control Tower Streamlit Application.

Central navigation, global configuration, database connection lifecycle,
and routing across all 9 enterprise modules via native st.navigation.
"""

from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Streamlit Page Config
st.set_page_config(
    page_title="AWARE-AI Control Tower",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database.connection import DatabaseManager
from app.components.ui_components import apply_custom_theme
from app.components.sidebar import render_sidebar_info

# Import Page Modules
from app.pages import (
    dashboard,
    shipments,
    risk,
    agents,
    root_cause,
    resilience,
    weather,
    inventory,
    monitoring,
)


@st.cache_resource
def get_shared_db() -> DatabaseManager:
    """Initialize and cache the database manager instance."""
    db = DatabaseManager()
    db.init()
    return db


def page_wrapper(render_fn):
    """Wrap each page with theme application and database injection."""
    def _wrapped():
        apply_custom_theme()
        db = get_shared_db()
        render_sidebar_info(db)
        render_fn(db)
    _wrapped.__name__ = render_fn.__name__
    return _wrapped


def main() -> None:
    db = get_shared_db()
    
    pages = [
        st.Page(page_wrapper(dashboard.render_page), title="1. Global Control Tower", icon="🌐", url_path="dashboard", default=True),
        st.Page(page_wrapper(shipments.render_page), title="2. Shipment Management", icon="📦", url_path="shipments"),
        st.Page(page_wrapper(risk.render_page), title="3. Shipment Risk Analysis", icon="🎯", url_path="risk"),
        st.Page(page_wrapper(agents.render_page), title="4. Multi-Agent Intelligence", icon="🤖", url_path="agents"),
        st.Page(page_wrapper(root_cause.render_page), title="5. Root Cause & Impact", icon="🔍", url_path="root_cause"),
        st.Page(page_wrapper(resilience.render_page), title="6. Resilience Planning", icon="🛡️", url_path="resilience"),
        st.Page(page_wrapper(weather.render_page), title="7. Weather & Maritime", icon="🌊", url_path="weather"),
        st.Page(page_wrapper(inventory.render_page), title="8. Supplier & Inventory", icon="🏭", url_path="inventory"),
        st.Page(page_wrapper(monitoring.render_page), title="9. System Monitoring", icon="⚡", url_path="monitoring"),
    ]

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
