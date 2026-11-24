"""
Page 5: Root Cause and Impact Analysis.
Deep-dives into diagnosed causal drivers, SHAP feature attribution roots,
and business impact assessments (demurrage, holding costs, SLA penalties, factory line stoppage).
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD
from database.models import RootCause, MitigationRecommendation, RiskAssessment
from modules.resilience.impact_engine import BusinessImpactAssessmentEngine
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Root Cause Diagnosis & Business Impact Assessment
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Trace delay causality down to environmental and operational drivers, and quantify financial enterprise exposure.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with db.session() as session:
        shipments = ShipmentCRUD.list_all(session)
        shipment_map = {f"{s.tracking_id} [{s.status.value}]": s.id for s in shipments}

    if not shipment_map:
        st.warning("No shipments available to analyze.")
        return

    c_sel, c_btn = st.columns([7, 3])
    with c_sel:
        selected_label = st.selectbox("Select Target Consignment", options=list(shipment_map.keys()))
        selected_id = shipment_map[selected_label]
    with c_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        eval_impact_btn = st.button("📊 Evaluate Business Impact", use_container_width=True, type="primary")

    # Run Impact Evaluation
    engine = BusinessImpactAssessmentEngine(db_manager=db)
    impact_data = engine.assess_impact(selected_id)

    # 1. Financial Impact Breakdown KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("Total Financial Exposure", f"${impact_data.get('total_financial_exposure', 0):,.2f}", subtitle="Aggregated risk impact")
    with k2:
        render_kpi("Demurrage Exposure", f"${impact_data.get('demurrage_exposure', 0):,.2f}", subtitle="Port storage & detention")
    with k3:
        render_kpi("Contract SLA Penalties", f"${impact_data.get('sla_penalties', 0):,.2f}", subtitle="Delay violation liabilities")
    with k4:
        stoppage = impact_data.get("line_stoppage_risk", "LOW")
        render_kpi(
            "Line Stoppage Risk",
            stoppage,
            subtitle="Assembly plant impact",
            delta="CRITICAL ALERT" if stoppage in ["HIGH", "CRITICAL"] else "Normal",
            delta_color="danger" if stoppage in ["HIGH", "CRITICAL"] else "normal",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Detailed Breakdown Sections
    col_causes, col_mitigations = st.columns([5, 5])

    with col_causes:
        st.subheader("🔍 Diagnosed Root Causes (TreeSHAP & Operational)")
        with db.session() as session:
            causes = (
                session.query(RootCause)
                .join(RiskAssessment)
                .filter(RiskAssessment.entity_type == "shipment", RiskAssessment.entity_id == selected_id)
                .order_by(RootCause.identified_at.desc())
                .all()
            )
            if not causes:
                # If not in DB, show causes from impact engine or prompt agent execution
                st.info("No persisted root cause records for this shipment. Run the **Multi-Agent Intelligence Cycle** on Page 4 to diagnose.")
            else:
                for c in causes:
                    st.markdown(
                        f"""
                        <div style="background: #111827; border-left: 4px solid #ef4444; border-radius: 4px; padding: 12px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between;">
                                <strong style="color: #f9fafb;">{c.cause_category.upper()}</strong>
                                <span style="color: #38bdf8; font-weight: 600; font-size: 0.85rem;">Source: {c.identified_by}</span>
                            </div>
                            <div style="color: #d1d5db; font-size: 0.85rem; margin-top: 4px;">{c.description}</div>
                            {f'<div style="color: #9ca3af; font-size: 0.75rem; margin-top: 4px;"><b>Contributing:</b> {c.contributing_factors_json}</div>' if c.contributing_factors_json else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    with col_mitigations:
        st.subheader("💡 Recommended Mitigations")
        with db.session() as session:
            mitigations = (
                session.query(MitigationRecommendation)
                .join(RiskAssessment)
                .filter(RiskAssessment.entity_type == "shipment", RiskAssessment.entity_id == selected_id)
                .order_by(MitigationRecommendation.priority.desc())
                .all()
            )
            if not mitigations:
                st.info("No specific mitigation recommendations found. Trigger the Multi-Agent Cycle to generate autonomous mitigations.")
            else:
                for m in mitigations:
                    st.markdown(
                        f"""
                        <div style="background: #111827; border-left: 4px solid #10b981; border-radius: 4px; padding: 12px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between;">
                                <strong style="color: #f9fafb;">{m.recommendation[:50]}...</strong>
                                <span style="color: #10b981; font-weight: 600; font-size: 0.8rem;">{m.priority.value.upper()}</span>
                            </div>
                            <div style="color: #d1d5db; font-size: 0.85rem; margin-top: 4px;">{m.recommendation}</div>
                            <div style="color: #38bdf8; font-size: 0.75rem; margin-top: 4px;">
                                Est. Cost: <b>${m.estimated_cost or 0:,.2f}</b> | Status: <b>{m.status.value.upper()}</b>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # 3. Downstream Assembly & Inventory Exposure
    st.markdown("---")
    st.subheader("🏭 Downstream Factory & Inventory Vulnerability")
    inv_impact = impact_data.get("affected_inventory_items", [])
    if inv_impact:
        df_inv = pd.DataFrame(inv_impact)
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("No direct critical SKU stockouts triggered by current consignment delay timeline.")


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

