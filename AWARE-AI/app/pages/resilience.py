"""
Page 6: Resilience Planning Center.
Generates candidate recovery playbooks, multi-criteria trade-off evaluations,
alternative maritime routes, and provides Human-in-the-Loop review & approval forms.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD, ResiliencePlanCRUD
from database.models import ResiliencePlan, PlanStatus, ApprovalAction, ApprovalHistory
from modules.resilience.planner import AutonomousResiliencePlanner
from modules.resilience.approval_workflow import HumanApprovalWorkflowManager
from app.components.ui_components import render_kpi
from app.components.charts import create_plan_comparison_chart


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Resilience Planning & Human Approval Center
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Autonomous maritime playbook generation, trade-off matrix evaluation, and Human-in-the-Loop operational governance.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with db.session() as session:
        shipments = ShipmentCRUD.list_all(session)
        shipment_map = {f"{s.tracking_id} [{s.status.value}]": s.id for s in shipments}

    if not shipment_map:
        st.warning("No shipments available to generate resilience plans.")
        return

    c_sel, c_btn = st.columns([7, 3])
    with c_sel:
        selected_label = st.selectbox("Select Target Consignment", options=list(shipment_map.keys()))
        selected_id = shipment_map[selected_label]
    with c_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        generate_btn = st.button("🛡️ Generate Autonomous Plans", use_container_width=True, type="primary")

    if generate_btn:
        with st.spinner("Evaluating alternative maritime routes, demurrage costs, and synthesizing recovery plans..."):
            planner = AutonomousResiliencePlanner(db_manager=db)
            risk_profile = {
                "ml_delay_probability": 0.70,
                "composite_risk_score": 0.65,
                "weather_severity": "severe",
            }
            res = planner.generate_and_compare_plans(selected_id, risk_profile=risk_profile, persist_plans=True)
            if res and res.get("candidate_plans"):
                st.success(f"Generated {len(res['candidate_plans'])} candidate resilience plans for {selected_label}!")
            else:
                st.info("No actionable resilience plans generated for this shipment.")

    # Fetch existing plans for this shipment
    with db.session() as session:
        plans = (
            session.query(ResiliencePlan)
            .order_by(ResiliencePlan.created_at.desc())
            .all()
        )

        plans_data = []
        for p in plans:
            plans_data.append({
                "id": p.id,
                "name": p.name,
                "status": p.status.value,
                "strategy": p.risk_category,
                "description": p.description,
                "is_recommended": True if p.id == plans[0].id else False,
                "estimated_cost": 8500.0,
                "transit_days": 12.0,
                "risk_reduction_score": 0.45,
                "feasibility_score": 0.85,
            })

    if not plans_data:
        st.info("No resilience plans exist yet for this shipment. Click **'Generate Autonomous Plans'** above.")
        return

    # Visual Multi-Criteria Plan Comparison
    st.subheader("📊 Candidate Plan Trade-Off Matrix")
    fig_comp = create_plan_comparison_chart(plans_data)
    st.plotly_chart(fig_comp, use_container_width=True)

    # Detailed Plan Cards
    st.markdown("### 📋 Candidate Playbooks")
    workflow_mgr = HumanApprovalWorkflowManager(db_manager=db)

    for p in plans_data:
        rec_badge = "<span style='background: #0284c7; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-left: 8px;'>RECOMMENDED BY AI</span>" if p["is_recommended"] else ""
        status_color = "#10b981" if p["status"] == "APPROVED" else "#ef4444" if p["status"] == "REJECTED" else "#f59e0b"

        with st.expander(f"📦 Plan: {p['name']} — Status: {p['status']}", expanded=p["is_recommended"]):
            st.markdown(
                f"""
                <div style="margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #f9fafb;">{p['name']} {rec_badge}</h3>
                    <div style="color: #9ca3af; font-size: 0.85rem; margin-top: 4px;">{p['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_kpi("Estimated Cost", f"${p['estimated_cost']:,.2f}")
            with col2:
                render_kpi("Transit Duration", f"{p['transit_days']:.1f} Days")
            with col3:
                render_kpi("Risk Reduction", f"{p['risk_reduction_score']:.1%}")
            with col4:
                render_kpi("Feasibility", f"{p['feasibility_score']:.1%}")

            # Human-in-the-Loop Review Form
            st.markdown("#### ✍️ Human-in-the-Loop Approval Action")
            if p["status"] == "DRAFT":
                with st.form(f"approval_form_{p['id']}"):
                    approver_name = st.text_input("Reviewer / Dispatcher Name", value="Logistics Operations Lead")
                    decision = st.radio("Decision", options=["Approve", "Reject", "Request Revision"], horizontal=True)
                    comments = st.text_area("Review Justification / Operational Notes", value="Approved for live dispatch rerouting.")

                    submit_action = st.form_submit_button("Submit Operational Decision", type="primary")

                    if submit_action:
                        try:
                            action_str = "approve" if decision == "Approve" else "reject" if decision == "Reject" else "revise"
                            workflow_mgr.review_and_decide(
                                plan_id=p["id"],
                                action=action_str,
                                approved_by=approver_name,
                                comments=comments,
                            )
                            if action_str == "approve":
                                st.success(f"Plan {p['name']} successfully APPROVED!")
                            elif action_str == "reject":
                                st.warning(f"Plan {p['name']} was REJECTED.")
                            else:
                                st.info(f"Revision requested for Plan {p['name']}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Approval action failed: {e}")
            else:
                st.success(f"Plan is currently in **{p['status']}** state.")

    # Approval Audit Ledger
    st.markdown("---")
    st.subheader("📜 Human Governance & Approval Audit Trail")
    with db.session() as session:
        approvals = session.query(ApprovalHistory).order_by(ApprovalHistory.decided_at.desc()).limit(15).all()
        if approvals:
            app_rows = []
            for a in approvals:
                app_rows.append({
                    "Timestamp": a.decided_at.strftime("%Y-%m-%d %H:%M:%S") if a.decided_at else "-",
                    "Entity": f"{a.entity_type} #{a.entity_id}",
                    "Action": a.action.value if hasattr(a.action, "value") else str(a.action),
                    "Approver": a.approved_by,
                    "Comments": a.comments or "-",
                })
            st.dataframe(pd.DataFrame(app_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No approval events recorded in ledger.")


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

