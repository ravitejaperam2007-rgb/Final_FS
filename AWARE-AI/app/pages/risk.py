"""
Page 3: Shipment Risk Analysis.
Integrates LightGBM delay prediction, composite risk scoring (0-1),
and TreeSHAP feature importance attributions.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD
from database.models import MLPrediction, RiskAssessment
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline
from app.components.ui_components import render_kpi, risk_badge_html
from app.components.charts import create_risk_gauge, create_shap_bar_chart, create_risk_radar


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Shipment Risk Analysis & Machine Learning Explainability
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Dual-tier risk inference: LightGBM delay classification paired with transparent TreeSHAP local attributions.
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
        st.warning("No shipments available in database for risk assessment.")
        return

    col_sel, col_btn = st.columns([8, 2])
    with col_sel:
        selected_label = st.selectbox("Select Consignment to Evaluate", options=list(shipment_map.keys()))
        selected_id = shipment_map[selected_label]
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_ml_btn = st.button("🚀 Run Live ML Inference", use_container_width=True, type="primary")

    # If run clicked, execute ML explainability pipeline
    if run_ml_btn:
        with st.spinner("Executing LightGBM model inference and computing TreeSHAP values..."):
            pipeline = MLExplainabilityPipeline(db_manager=db)
            try:
                result = pipeline.predict_and_explain_shipment(selected_id, persist=True)
                st.success(
                    f"Inference complete: Delay Probability = {result['ml_delay_probability']:.1%}, "
                    f"Composite Risk = {result['composite_risk_score']:.2f}"
                )
            except Exception as e:
                st.error(f"Inference error: {e}")

    # Load latest ML prediction and Risk Assessment from DB
    with db.session() as session:
        latest_pred = (
            session.query(MLPrediction)
            .filter(MLPrediction.entity_type == "shipment", MLPrediction.entity_id == selected_id)
            .order_by(MLPrediction.created_at.desc())
            .first()
        )
        latest_risk = (
            session.query(RiskAssessment)
            .filter(RiskAssessment.entity_type == "shipment", RiskAssessment.entity_id == selected_id)
            .order_by(RiskAssessment.assessed_at.desc())
            .first()
        )
        target_shipment = ShipmentCRUD.get_by_id(session, selected_id)
        target_weight = target_shipment.weight_kg if target_shipment else 15000.0
        target_priority = target_shipment.priority.value if target_shipment else "medium"
        target_supp_rel = target_shipment.supplier.reliability_score if (target_shipment and target_shipment.supplier) else 0.85

    if not latest_pred or not latest_risk:
        st.info("No prior inference record found for this shipment. Click **'Run Live ML Inference'** above to compute.")
        return

    # Extract metrics
    delay_prob = latest_pred.predicted_value
    risk_score = latest_risk.risk_score
    risk_tier = latest_risk.risk_level.name
    top_features = []
    if latest_pred.shap_values_json:
        import json
        raw_attributions = json.loads(latest_pred.shap_values_json)
        top_features = [{"feature": k, "attribution": v} for k, v in raw_attributions.items()]

    # KPI Row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi(
            "ML Delay Probability",
            f"{delay_prob:.1%}",
            subtitle="LightGBM Classifier",
            delta="High Risk" if delay_prob > 0.5 else "Low Risk",
            delta_color="danger" if delay_prob > 0.5 else "normal",
        )
    with k2:
        render_kpi(
            "Composite Risk Score",
            f"{risk_score:.2f}",
            subtitle="Multi-Factor Weighted Index",
            delta=risk_tier,
            delta_color="danger" if "HIGH" in risk_tier or "CRIT" in risk_tier else "normal",
        )
    with k3:
        render_kpi("Risk Classification", risk_tier, subtitle=f"Threshold Tier")
    with k4:
        render_kpi(
            "Cargo Value / Weight",
            f"{target_weight:,.0f} kg" if target_weight else "N/A",
            subtitle=target_priority.upper() + " PRIORITY",
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Visualization Row
    g_col, r_col = st.columns([5, 5])

    with g_col:
        st.subheader("🎯 Dual Risk Gauge Calibration")
        st.plotly_chart(create_risk_gauge(risk_score, title=f"Composite Risk ({risk_tier})"), use_container_width=True)

    with r_col:
        st.subheader("🕸️ Multi-Echelon Risk Factors")
        breakdown = {
            "ML Probability": delay_prob,
            "Supplier Risk": 1.0 - target_supp_rel,
            "Priority Weight": 0.9 if target_priority == "critical" else 0.5,
            "Operational Baseline": 0.4,
            "Composite Score": risk_score,
        }
        st.plotly_chart(create_risk_radar(breakdown), use_container_width=True)

    # SHAP Explanations Section
    st.markdown("---")
    st.subheader("🔍 TreeSHAP Feature Attribution (Local Instance Explainability)")
    st.markdown(
        """
        TreeSHAP decomposes the difference between the model's expected baseline delay probability
        and this shipment's specific prediction into exact additive feature contributions.
        Bars pointing right (red) indicate features increasing delay risk; bars pointing left (blue) decrease delay risk.
        """
    )

    col_shap_chart, col_shap_table = st.columns([6, 4])

    with col_shap_chart:
        fig_shap = create_shap_bar_chart(top_features)
        st.plotly_chart(fig_shap, use_container_width=True)

    with col_shap_table:
        st.markdown("#### Feature Influence Breakdown")
        if top_features:
            df_shap = pd.DataFrame(top_features)
            st.dataframe(df_shap, use_container_width=True, hide_index=True)
        else:
            st.info("No feature attributions stored for this prediction.")

    # Historical Predictions Table
    st.markdown("---")
    st.subheader("📜 Historical Inference Logs for Shipment")
    with db.session() as session:
        hist_preds = (
            session.query(MLPrediction)
            .filter(MLPrediction.entity_type == "shipment", MLPrediction.entity_id == selected_id)
            .order_by(MLPrediction.created_at.desc())
            .limit(10)
            .all()
        )
        hist_rows = []
        for p in hist_preds:
            hist_rows.append({
                "Timestamp": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "-",
                "Model Version": p.model_version,
                "Prediction": "DELAYED" if p.predicted_value > 0.5 else "ON_TIME",
                "Delay Probability": f"{p.predicted_value:.1%}",
                "Confidence": f"{p.confidence:.1%}" if p.confidence else "-",
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)


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

