"""
Page 9: System Monitoring.
Inspects database table health, SQLite PRAGMA journal modes,
WAL execution metrics, migration ledger status, and system telemetry.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from sqlalchemy import text

from database.connection import DatabaseManager
from database.migrations_mgr import MigrationManager
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                System Health & Database Telemetry
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                SQLite WAL mode concurrency verification, table row counts, PRAGMA diagnostics, and migration ledger.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. PRAGMA & WAL Engine Checks
    with db.engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout;")).scalar()
        integrity_check = conn.execute(text("PRAGMA integrity_check;")).scalar()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Journal Mode", str(journal_mode).upper(), subtitle="Target: WAL")
    with c2:
        render_kpi("Foreign Keys", "ENFORCED" if foreign_keys == 1 else "DISABLED", subtitle="Relational constraints")
    with c3:
        render_kpi("Busy Timeout", f"{busy_timeout} ms", subtitle="Concurrency wait")
    with c4:
        render_kpi("Database Integrity", str(integrity_check).upper(), subtitle="SQLite B-tree check")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Table Row Count Matrix
    st.subheader("📊 Relational Entity Record Counts")
    tables = [
        "ports",
        "suppliers",
        "inventory",
        "shipments",
        "shipment_history",
        "weather_evidence",
        "risk_assessments",
        "ml_predictions",
        "agent_executions",
        "root_causes",
        "mitigation_recommendations",
        "resilience_plans",
        "approval_history",
        "schema_migrations",
    ]

    rows = []
    for t in tables:
        count = db.row_count(t) if db.table_exists(t) else 0
        rows.append({
            "Table Name": t,
            "Exists": "YES" if db.table_exists(t) else "NO",
            "Total Records": f"{count:,}",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 3. Migration Ledger Inspection
    st.markdown("---")
    st.subheader("📜 Schema Migration Version Status")
    mgr = MigrationManager(db_manager=db)
    current_ver = mgr.current_version()
    latest_ver = mgr.latest_version()

    m1, m2 = st.columns(2)
    with m1:
        render_kpi("Applied Migration Version", f"v{current_ver}")
    with m2:
        render_kpi("Available Migration Version", f"v{latest_ver}", delta="Synchronized" if current_ver == latest_ver else "Update Needed")

    with db.session() as session:
        applied_logs = mgr.history()
        if applied_logs:
            mig_rows = []
            for m in applied_logs:
                ver = m.get("version") if isinstance(m, dict) else getattr(m, "version", "")
                desc = m.get("description") if isinstance(m, dict) else getattr(m, "description", "")
                app_at = m.get("applied_at") if isinstance(m, dict) else getattr(m, "applied_at", "")
                succ = m.get("success") if isinstance(m, dict) else getattr(m, "success", True)
                app_str = app_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(app_at, "strftime") else str(app_at)
                mig_rows.append({
                    "Version": ver,
                    "Description": desc,
                    "Applied At (UTC)": app_str,
                    "Success": "TRUE" if succ else "FAILED",
                })
            st.dataframe(pd.DataFrame(mig_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No migrations ledger entries found.")


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

