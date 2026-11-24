"""
Page 1: Global Control Tower Dashboard.
Displays high-level operational KPIs, interactive fleet map, high-risk alerts,
and active maritime disruption summaries from the database.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload

from database.connection import DatabaseManager
from database.models import (
    Port,
    Shipment,
    ShipmentStatus,
    RiskAssessment,
    WeatherEvidence,
    WeatherSeverity,
    ResiliencePlan,
    PlanStatus,
)
from app.components.ui_components import render_kpi, risk_badge_html
from app.components.charts import create_fleet_map, create_risk_gauge


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Global Supply Chain Control Tower
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Real-time multi-echelon maritime visibility, autonomous risk classification, and fleet telemetry.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Fetch Real Database Metrics
    with db.session() as session:
        ports = session.query(Port).all()
        ports_data = [{"name": p.name, "code": p.code, "country": p.country, "latitude": p.latitude, "longitude": p.longitude} for p in ports]

        shipments = (
            session.query(Shipment)
            .options(
                joinedload(Shipment.origin_port),
                joinedload(Shipment.destination_port),
                joinedload(Shipment.supplier),
            )
            .all()
        )
        total_shipments = len(shipments)
        in_transit = sum(1 for s in shipments if s.status == ShipmentStatus.IN_TRANSIT)
        delayed = sum(1 for s in shipments if s.status == ShipmentStatus.DELAYED)
        delivered = sum(1 for s in shipments if s.status == ShipmentStatus.DELIVERED)

        # High risk shipments
        assessments = session.query(RiskAssessment).filter(RiskAssessment.entity_type == "shipment").order_by(RiskAssessment.assessed_at.desc()).all()
        latest_risk_map = {}
        for a in assessments:
            if a.entity_id not in latest_risk_map:
                latest_risk_map[a.entity_id] = a

        # Severe weather events
        severe_weather_count = session.query(WeatherEvidence).filter(
            WeatherEvidence.severity.in_([WeatherSeverity.SEVERE, WeatherSeverity.EXTREME])
        ).count()

        # Active resilience plans
        active_plans = session.query(ResiliencePlan).filter(
            ResiliencePlan.status.in_([PlanStatus.ACTIVE])
        ).count()

        # Average composite risk across active fleet
        avg_risk = 0.0
        if latest_risk_map:
            avg_risk = sum(a.risk_score for a in latest_risk_map.values()) / len(latest_risk_map)

        # Build shipment map payload
        shipments_map_data = []
        for s in shipments:
            r = latest_risk_map.get(s.id)
            risk_lvl = r.risk_level.name if r else "LOW"
            shipments_map_data.append({
                "tracking_id": s.tracking_id,
                "status": s.status.value,
                "risk_level": risk_lvl,
                "cargo": s.cargo_description or "General Freight",
                "origin_lat": s.origin_port.latitude if s.origin_port else None,
                "origin_lon": s.origin_port.longitude if s.origin_port else None,
                "dest_lat": s.destination_port.latitude if s.destination_port else None,
                "dest_lon": s.destination_port.longitude if s.destination_port else None,
                "current_lat": s.current_latitude or (s.origin_port.latitude if s.origin_port else None),
                "current_lon": s.current_longitude or (s.origin_port.longitude if s.origin_port else None),
            })

        # Build high-risk attention alerts and fleet overview table rows inside active session
        high_risk_alerts = []
        table_rows = []
        for s in shipments:
            r = latest_risk_map.get(s.id)
            score = float(r.risk_score) if r and r.risk_score is not None else 0.25
            lvl = r.risk_level.name if r and hasattr(r, "risk_level") else "NORMAL"
            orig_name = f"{s.origin_port.name} ({s.origin_port.code})" if s.origin_port else "N/A"
            dest_name = f"{s.destination_port.name} ({s.destination_port.code})" if s.destination_port else "N/A"
            orig_code = s.origin_port.code if s.origin_port else "N/A"
            dest_code = s.destination_port.code if s.destination_port else "N/A"
            supp_name = s.supplier.name if s.supplier else "N/A"

            if score >= 0.50 or s.status == ShipmentStatus.DELAYED:
                high_risk_alerts.append({
                    "tracking_id": s.tracking_id,
                    "risk_level": lvl,
                    "score": score,
                    "origin_code": orig_code,
                    "dest_code": dest_code,
                    "status": s.status.value,
                })

            table_rows.append({
                "Tracking ID": s.tracking_id,
                "Origin": orig_name,
                "Destination": dest_name,
                "Supplier": supp_name,
                "Status": s.status.value,
                "Priority": s.priority.value,
                "Risk Score": f"{score:.2f}",
                "Risk Tier": lvl,
                "Departure": s.departure_date.strftime("%Y-%m-%d %H:%M") if s.departure_date else "Pending",
                "Est. Arrival": s.estimated_arrival.strftime("%Y-%m-%d %H:%M") if s.estimated_arrival else "TBD",
            })

    # 2. Key Performance Indicator Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi("Active Fleet", f"{in_transit} Vessels", subtitle=f"Total: {total_shipments} managed")
    with c2:
        render_kpi(
            "Disruptions",
            f"{delayed}",
            subtitle="Immediate mitigation needed" if delayed > 0 else "All corridors operational",
            delta=f"+{delayed}" if delayed > 0 else None,
            delta_color="danger" if delayed > 0 else "normal",
        )
    with c3:
        render_kpi(
            "Fleet Risk Index",
            f"{avg_risk:.2f}",
            subtitle="Composite Multi-Factor (0-1)",
            delta="Elevated" if avg_risk > 0.5 else "Optimal",
            delta_color="danger" if avg_risk > 0.5 else "normal",
        )
    with c4:
        render_kpi("Severe Weather Alerts", f"{severe_weather_count}", subtitle="Open-Meteo port hazards")
    with c5:
        render_kpi("Active Resilience Plans", f"{active_plans}", subtitle="Approved autonomous playbooks")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Main Operational View: Interactive World Fleet Map & High Risk Panel
    col_map, col_alerts = st.columns([7, 3])

    with col_map:
        st.subheader("🌐 Global Maritime Transit Corridors & Vessel Positions")
        if shipments_map_data:
            fig_map = create_fleet_map(shipments_map_data, ports_data)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("No active shipments available to display on map.")

    with col_alerts:
        st.subheader("⚡ Fleet Risk Health")
        st.plotly_chart(create_risk_gauge(avg_risk, title="Fleet-Wide Risk"), use_container_width=True)

        st.markdown("#### 🚨 High-Priority Attention List")
        if high_risk_alerts:
            for a in high_risk_alerts:
                st.markdown(
                    f"""
                    <div style="background: #1e293b; border-left: 4px solid #ef4444; padding: 10px; margin-bottom: 8px; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #f9fafb;">{a['tracking_id']}</strong>
                            {risk_badge_html(a['risk_level'])}
                        </div>
                        <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 4px;">
                            {a['origin_code']} → {a['dest_code']} | Status: {a['status']}
                        </div>
                        <div style="font-size: 0.8rem; color: #38bdf8; margin-top: 2px;">
                            Risk Score: <b>{a['score']:.2f}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ No shipments currently exceeding critical risk thresholds.")

    # 4. Active Fleet Status Table
    st.markdown("### 📋 Active Fleet Status Overview")
    if table_rows:
        df = pd.DataFrame(table_rows)
        st.dataframe(
            df,
            column_config={
                "Tracking ID": st.column_config.TextColumn("Tracking ID", width="medium"),
                "Risk Tier": st.column_config.TextColumn("Risk Tier", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No shipments found.")


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

