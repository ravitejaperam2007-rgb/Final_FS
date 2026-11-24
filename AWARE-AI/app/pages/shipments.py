"""
Page 2: Shipment Management.
Provides full CRUD interface to view, register, update, and manage shipments,
including audit trail history and status transitions.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD, PortCRUD, SupplierCRUD
from database.models import (
    Shipment,
    ShipmentStatus,
    PriorityLevel,
    ShipmentHistory,
)
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Shipment Management & Lifecycle Audit
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Register new maritime consignments, update status telemetry, and review immutable audit histories.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_overview, tab_create, tab_update, tab_audit = st.tabs([
        "📋 Active Shipments",
        "➕ Register New Shipment",
        "🔄 Update Status / Telemetry",
        "📜 Audit Trail History",
    ])

    # ── TAB 1: Overview ──────────────────────────────────────────
    with tab_overview:
        with db.session() as session:
            shipments = ShipmentCRUD.list_all(session)
            if not shipments:
                st.info("No shipments found in the database. Use 'Register New Shipment' to add one.")
            else:
                rows = []
                for s in shipments:
                    rows.append({
                        "ID": s.id,
                        "Tracking ID": s.tracking_id,
                        "Origin": f"{s.origin_port.name} ({s.origin_port.code})" if s.origin_port else "-",
                        "Destination": f"{s.destination_port.name} ({s.destination_port.code})" if s.destination_port else "-",
                        "Supplier": s.supplier.name if s.supplier else "-",
                        "Status": s.status.value,
                        "Priority": s.priority.value,
                        "Weight (kg)": f"{s.weight_kg:,.0f}" if s.weight_kg else "-",
                        "Cargo": s.cargo_description or "-",
                        "Departure": s.departure_date.strftime("%Y-%m-%d") if s.departure_date else "-",
                        "Est Arrival": s.estimated_arrival.strftime("%Y-%m-%d") if s.estimated_arrival else "-",
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ── TAB 2: Register New Shipment ────────────────────────────
    with tab_create:
        st.subheader("Register New Consignment")
        with db.session() as session:
            ports = PortCRUD.list_all(session)
            suppliers = SupplierCRUD.list_all(session)

            port_options = {f"{p.name} ({p.code})": p.id for p in ports}
            supplier_options = {"None": None}
            supplier_options.update({f"{s.name} ({s.country})": s.id for s in suppliers})

        if not port_options:
            st.error("No ports found. Please seed the database first.")
        else:
            with st.form("create_shipment_form"):
                c1, c2 = st.columns(2)
                with c1:
                    tracking_id = st.text_input("Tracking ID", value=f"SHP-TRK-{datetime.now().strftime('%Y%m%d%H%M')}")
                    origin_label = st.selectbox("Origin Port", options=list(port_options.keys()), index=0)
                    dest_label = st.selectbox("Destination Port", options=list(port_options.keys()), index=1 if len(port_options) > 1 else 0)
                    supplier_label = st.selectbox("Strategic Supplier", options=list(supplier_options.keys()))

                with c2:
                    priority = st.selectbox("Consignment Priority", options=[p.value for p in PriorityLevel], index=1)
                    weight_kg = st.number_input("Cargo Weight (kg)", min_value=1.0, value=15000.0, step=500.0)
                    cargo_desc = st.text_area("Cargo Description", value="Containerized High-Value Components")
                    departure_date = st.date_input("Departure Date", value=datetime.now())

                submit = st.form_submit_button("Submit & Register Shipment", use_container_width=True)

                if submit:
                    if origin_label == dest_label:
                        st.error("Origin and Destination ports cannot be the same.")
                    else:
                        try:
                            with db.session() as session:
                                dep_dt = datetime.combine(departure_date, datetime.min.time())
                                created = ShipmentCRUD.create(
                                    session,
                                    tracking_id=tracking_id,
                                    origin_port_id=port_options[origin_label],
                                    destination_port_id=port_options[dest_label],
                                    supplier_id=supplier_options[supplier_label],
                                    cargo_description=cargo_desc,
                                    weight_kg=weight_kg,
                                    priority=PriorityLevel(priority),
                                    status=ShipmentStatus.PENDING,
                                    departure_date=dep_dt,
                                    changed_by="Control_Tower_Operator",
                                    change_reason="Manual shipment registration via UI",
                                )
                                st.success(f"Successfully registered shipment: {created.tracking_id} (ID: {created.id})")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error registering shipment: {e}")

    # ── TAB 3: Update Status / Telemetry ─────────────────────────
    with tab_update:
        st.subheader("Update Live Telemetry & Consignment Status")
        with db.session() as session:
            shipments = ShipmentCRUD.list_all(session)
            shipment_map = {f"{s.tracking_id} [{s.status.value}]": s.id for s in shipments}

        if not shipment_map:
            st.info("No shipments available to update.")
        else:
            selected_shipment_label = st.selectbox("Select Shipment to Update", options=list(shipment_map.keys()))
            selected_id = shipment_map[selected_shipment_label]

            with db.session() as session:
                target_shp = ShipmentCRUD.get(session, selected_id)
                current_status = target_shp.status.value if target_shp else "PENDING"
                cur_lat = target_shp.current_latitude or 0.0
                cur_lon = target_shp.current_longitude or 0.0

            with st.form("update_shipment_form"):
                u1, u2 = st.columns(2)
                with u1:
                    new_status = st.selectbox(
                        "New Status",
                        options=[s.value for s in ShipmentStatus],
                        index=[s.value for s in ShipmentStatus].index(current_status),
                    )
                    reason = st.text_input("Reason for Status Change", value="Operational telemetry update")

                with u2:
                    lat_val = st.number_input("Current Latitude", value=float(cur_lat), format="%.4f")
                    lon_val = st.number_input("Current Longitude", value=float(cur_lon), format="%.4f")

                update_btn = st.form_submit_button("Apply Telemetry & Status Update", use_container_width=True)

                if update_btn:
                    try:
                        with db.session() as session:
                            updated = ShipmentCRUD.update(
                                session,
                                selected_id,
                                status=ShipmentStatus(new_status),
                                current_latitude=lat_val,
                                current_longitude=lon_val,
                                changed_by="Control_Tower_Dispatcher",
                                change_reason=reason,
                            )
                            st.success(f"Shipment {updated.tracking_id} updated to {updated.status.value}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update shipment: {e}")

    # ── TAB 4: Audit Trail History ──────────────────────────────
    with tab_audit:
        st.subheader("Immutable Shipment State Transition Ledger")
        with db.session() as session:
            shipments = ShipmentCRUD.list_all(session)
            shp_filter_opts = {"All Shipments": None}
            shp_filter_opts.update({s.tracking_id: s.id for s in shipments})

        selected_filter = st.selectbox("Filter Audit History by Shipment", options=list(shp_filter_opts.keys()))
        filter_id = shp_filter_opts[selected_filter]

        with db.session() as session:
            query = session.query(ShipmentHistory)
            if filter_id is not None:
                query = query.filter(ShipmentHistory.shipment_id == filter_id)
            history_records = query.order_by(ShipmentHistory.timestamp.desc()).all()

            if not history_records:
                st.info("No audit transition records found.")
            else:
                audit_rows = []
                for h in history_records:
                    audit_rows.append({
                        "Timestamp (UTC)": h.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "Shipment Tracking ID": h.shipment.tracking_id if h.shipment else f"ID {h.shipment_id}",
                        "Previous Status": h.previous_status.value if h.previous_status else "INITIAL",
                        "New Status": h.new_status.value,
                        "Operator / Agent": h.changed_by,
                        "Reason": h.change_reason or "-",
                    })
                df_audit = pd.DataFrame(audit_rows)
                st.dataframe(df_audit, use_container_width=True, hide_index=True)


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

