"""
AWARE-AI: Supplier Intelligence Page.
Routes to Supplier & Inventory Intelligence module.
"""

from __future__ import annotations

import streamlit as st
from database.connection import DatabaseManager
from app.pages import inventory


def render_page(db: DatabaseManager) -> None:
    inventory.render_page(db)


def render() -> None:
    db = DatabaseManager()
    db.init()
    render_page(db)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from app.components.ui_components import apply_custom_theme
    apply_custom_theme()
    _db = DatabaseManager()
    _db.init()
    render_page(_db)
