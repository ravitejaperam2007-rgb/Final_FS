"""
Page 8: Supplier and Inventory Intelligence.
Tracks supplier reliability scoring, lead-time volatility,
inventory stockout vulnerability, safety stocks, and Wilson EOQ calculations.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.connection import DatabaseManager
from database.crud import SupplierCRUD, InventoryCRUD
from database.models import Supplier, Inventory
from modules.supplier.intelligence import SupplierIntelligence
from modules.inventory.intelligence import InventoryIntelligence
from modules.inventory.optimizer import InventoryOptimizer
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Supplier Reliability & Inventory Criticality Intelligence
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Empirical vendor reliability evaluation, stockout risk radar, safety stock buffers, and EOQ optimization.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_sup, tab_inv, tab_eoq = st.tabs([
        "🏭 Strategic Suppliers",
        "📦 Inventory Health & Stockout Radar",
        "⚙️ EOQ & Reorder Point Optimizer",
    ])

    # ── TAB 1: Supplier Intelligence ─────────────────────────────
    with tab_sup:
        st.subheader("Empirical Vendor Performance & Reliability Matrix")
        with db.session() as session:
            suppliers = SupplierCRUD.list_all(session)
            if not suppliers:
                st.info("No suppliers found in database.")
            else:
                sup_rows = []
                for s in suppliers:
                    sup_rows.append({
                        "ID": s.id,
                        "Supplier Name": s.name,
                        "Country": s.country,
                        "Category": s.category or "General",
                        "Risk Tier": s.risk_tier.upper() if s.risk_tier else "MEDIUM",
                        "Reliability Score": f"{s.reliability_score:.1%}",
                        "Avg Lead Time (Days)": s.lead_time_days,
                        "Active Shipments": len(s.shipments),
                    })
                st.dataframe(pd.DataFrame(sup_rows), use_container_width=True, hide_index=True)

        st.markdown("#### Supplier Deep Profiler")
        with db.session() as session:
            sup_map = {s.name: s.id for s in suppliers}
        if sup_map:
            sel_sup_name = st.selectbox("Select Supplier to Audit", options=list(sup_map.keys()))
            sup_intel = SupplierIntelligence(db_manager=db)
            profile = sup_intel.profile_supplier(sup_map[sel_sup_name])

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                render_kpi("Reliability Index", f"{profile.get('reliability_score', 0):.1%}")
            with sc2:
                render_kpi("Lead Time Days", f"{profile.get('lead_time_days', 0)} Days")
            with sc3:
                render_kpi("Risk Tier", profile.get('risk_tier', 'MEDIUM').upper())
            with sc4:
                render_kpi("Category", str(profile.get('category', 'General')))

    # ── TAB 2: Inventory Health ──────────────────────────────────
    with tab_inv:
        st.subheader("Multi-Echelon Inventory Health & Stockout Exposure")
        with db.session() as session:
            items = InventoryCRUD.list_all(session)
            if not items:
                st.info("No inventory items found.")
            else:
                inv_rows = []
                critical_count = 0
                for item in items:
                    stockout_risk = "HIGH" if item.quantity_on_hand < item.safety_stock else "NORMAL"
                    if stockout_risk == "HIGH":
                        critical_count += 1
                    inv_rows.append({
                        "SKU": item.sku,
                        "Product Name": item.product_name,
                        "Warehouse": item.warehouse_location or "-",
                        "Qty On Hand": f"{item.quantity_on_hand:,}",
                        "Safety Stock": f"{item.safety_stock:,}",
                        "Reorder Point": f"{item.reorder_point:,}",
                        "Unit Cost ($)": f"${item.unit_cost:,.2f}",
                        "Stockout Risk": stockout_risk,
                        "Supplier": item.supplier.name if item.supplier else "-",
                    })

                i1, i2, i3 = st.columns(3)
                with i1:
                    render_kpi("Total Monitored SKUs", len(items))
                with i2:
                    render_kpi(
                        "Stockout Critical Alerts",
                        critical_count,
                        delta="Action Required" if critical_count > 0 else "Optimal",
                        delta_color="danger" if critical_count > 0 else "normal",
                    )
                with i3:
                    render_kpi("Inventory Under Safety Buffer", f"{critical_count / len(items):.0%}")

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)

    # ── TAB 3: EOQ & Reorder Optimizer ───────────────────────────
    with tab_eoq:
        st.subheader("Wilson Economic Order Quantity (EOQ) & Safety Stock Calculus")
        with st.form("eoq_calc_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                demand = st.number_input("Annual Demand (Units/Year)", min_value=100.0, value=25000.0, step=1000.0)
                lead_time = st.number_input("Supplier Lead Time (Days)", min_value=1.0, value=18.0, step=1.0)
            with c2:
                order_cost = st.number_input("Order / Setup Cost ($/Order)", min_value=10.0, value=250.0, step=25.0)
                unit_cost = st.number_input("Unit Purchase Cost ($)", min_value=1.0, value=50.0, step=5.0)
            with c3:
                holding_rate = st.slider("Annual Holding Cost Rate (%)", min_value=5.0, max_value=40.0, value=20.0, step=1.0) / 100.0
                service_level = st.selectbox("Desired Service Level", options=["90%", "95%", "99%"], index=1)

            calc_btn = st.form_submit_button("Calculate Optimal EOQ & Reorder Policy", type="primary")

            if calc_btn:
                optimizer = InventoryOptimizer()
                safety_buf = InventoryOptimizer.calculate_safety_stock(
                    max_daily_demand=demand / 300.0,
                    avg_daily_demand=demand / 365.0,
                    max_lead_time_days=int(lead_time * 1.5),
                    avg_lead_time_days=int(lead_time),
                )
                eoq_res = optimizer.calculate_eoq(
                    annual_demand=demand,
                    ordering_cost=order_cost,
                    unit_cost=unit_cost,
                    holding_cost_rate=holding_rate,
                )
                rop_val = InventoryOptimizer.calculate_reorder_point(
                    average_daily_demand=demand / 365.0,
                    lead_time_days=int(lead_time),
                    safety_stock=safety_buf,
                )

                st.success("Optimization Calculations Succeeded!")
                e1, e2, e3 = st.columns(3)
                with e1:
                    render_kpi("Optimal Order Size (EOQ)", f"{eoq_res.get('eoq_units', 0):,.0f} Units", subtitle="Wilson Lot Size")
                with e2:
                    render_kpi("Recommended Reorder Point", f"{rop_val:,.0f} Units", subtitle=f"Service Level: {service_level}")
                with e3:
                    render_kpi("Safety Stock Buffer", f"{safety_buf:,.0f} Units", subtitle="Stochastic buffer")


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

