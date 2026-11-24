"""
Page 4: Multi-Agent Intelligence Center.
Coordinates, triggers, and displays execution telemetry for the 7 specialized AWARE-AI agents:
1. Weather Intelligence Agent
2. Supplier Intelligence Agent
3. Risk Assessment Agent
4. Root Cause Analysis Agent
5. Impact Assessment Agent
6. Mitigation Recommendation Agent
7. Resilience Planning Agent
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD
from database.models import AgentExecution, AgentTaskStatus
from agents.orchestrator import AgentOrchestrator
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Multi-Agent Intelligence Command Center
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Autonomous orchestration of the 7 specialized supply chain intelligence and resilience agents.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with db.session() as session:
        shipments = ShipmentCRUD.list_all(session)
        shipment_map = {
            f"{s.tracking_id} ({s.origin_port.code if s.origin_port else 'N/A'} → {s.destination_port.code if s.destination_port else 'N/A'}) - [{s.status.value}]": s.id
            for s in shipments
        }

    if not shipment_map:
        st.warning("No shipments available to analyze.")
        return

    c_sel, c_btn = st.columns([7, 3])
    with c_sel:
        selected_label = st.selectbox("Select Target Consignment for Agent Execution", options=list(shipment_map.keys()))
        selected_id = shipment_map[selected_label]
    with c_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_cycle_btn = st.button("🤖 Trigger Full 7-Agent Cycle", use_container_width=True, type="primary")

    if run_cycle_btn:
        with st.spinner("Orchestrating multi-agent execution pipeline across all 7 specialized agents..."):
            orchestrator = AgentOrchestrator(db_manager=db)
            results = orchestrator.run_shipment_intelligence_cycle(selected_id)
            status = results.get("cycle_status")
            if status == "completed":
                st.success(f"Multi-agent cycle completed in {results.get('total_duration_ms', 0):.1f} ms. All 7 agents executed successfully!")
            else:
                st.warning(f"Cycle finished with status: {status}. Errors: {results.get('errors')}")

    # Display Agent Architecture Status Badges
    st.markdown("### 🧬 Specialized Agent Architecture")
    agents_info = [
        ("1. Weather Intelligence", "Atmospheric hazard & marine conditions tracker", "#38bdf8"),
        ("2. Supplier Intelligence", "Empirical reliability & lead-time volatility scorer", "#818cf8"),
        ("3. Risk Assessment", "Composite multi-factor risk evaluator", "#f59e0b"),
        ("4. Root Cause Analysis", "TreeSHAP attribution diagnosis engine", "#ef4444"),
        ("5. Impact Assessment", "Financial demurrage & line-stoppage analyzer", "#ec4899"),
        ("6. Mitigation Recommendation", "Operational playbook generator", "#10b981"),
        ("7. Resilience Planning", "Maritime route diversion & utility optimizer", "#06b6d4"),
    ]

    cols = st.columns(4)
    for i, (name, desc, color) in enumerate(agents_info[:4]):
        with cols[i]:
            st.markdown(
                f"""
                <div style="background: #111827; border: 1px solid #1f2937; border-top: 3px solid {color}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                    <strong style="color: #f9fafb; font-size: 0.85rem;">{name}</strong>
                    <div style="color: #9ca3af; font-size: 0.75rem; margin-top: 4px;">{desc}</div>
                    <div style="color: #10b981; font-size: 0.7rem; font-weight: 700; margin-top: 6px;">● ONLINE</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    cols2 = st.columns(3)
    for i, (name, desc, color) in enumerate(agents_info[4:]):
        with cols2[i]:
            st.markdown(
                f"""
                <div style="background: #111827; border: 1px solid #1f2937; border-top: 3px solid {color}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                    <strong style="color: #f9fafb; font-size: 0.85rem;">{name}</strong>
                    <div style="color: #9ca3af; font-size: 0.75rem; margin-top: 4px;">{desc}</div>
                    <div style="color: #10b981; font-size: 0.7rem; font-weight: 700; margin-top: 6px;">● ONLINE</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Telemetry and Execution Logs
    st.markdown("---")
    st.subheader(f"📊 Agent Execution History for Consignment (ID: {selected_id})")

    with db.session() as session:
        executions = (
            session.query(AgentExecution)
            .order_by(AgentExecution.started_at.desc())
            .limit(25)
            .all()
        )

        if not executions:
            st.info("No agent execution history found for this shipment yet. Click 'Trigger Full 7-Agent Cycle' above.")
        else:
            exec_rows = []
            for e in executions:
                exec_rows.append({
                    "Execution ID": e.id,
                    "Agent Name": e.agent_name,
                    "Task Type": e.task_type,
                    "Status": e.status.value,
                    "Duration (ms)": f"{e.duration_ms:.1f}" if e.duration_ms is not None else "-",
                    "Timestamp": e.started_at.strftime("%Y-%m-%d %H:%M:%S") if e.started_at else "-",
                    "Error": e.error_message or "None",
                })
            st.dataframe(pd.DataFrame(exec_rows), use_container_width=True, hide_index=True)

            # Latest execution inspection
            latest_exec = executions[0]
            with st.expander(f"🔍 Deep Telemetry Payload: {latest_exec.agent_name} (ID: {latest_exec.id})"):
                st.json({
                    "agent_name": latest_exec.agent_name,
                    "task_type": latest_exec.task_type,
                    "status": latest_exec.status.value,
                    "duration_ms": latest_exec.duration_ms,
                    "input_summary": latest_exec.input_summary,
                    "output_summary": latest_exec.output_summary,
                    "error_message": latest_exec.error_message,
                })


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

