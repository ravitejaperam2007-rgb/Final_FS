"""
Page 7: Weather and Maritime Intelligence.
Live Open-Meteo port atmospheric conditions, oceanic hazard alerts,
corridor waypoint weather interpolation, and Great-Circle geodetic navigation metrics.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from database.connection import DatabaseManager
from database.crud import PortCRUD
from database.models import WeatherEvidence, WeatherSeverity
from modules.weather.api_client import WeatherAPIClient
from modules.weather.intelligence import WeatherIntelligence
from modules.shipment.routes import RouteOptimizer
from app.components.ui_components import render_kpi


def render_page(db: DatabaseManager) -> None:
    st.markdown(
        """
        <div class="control-tower-header">
            <h1 style="color: #f9fafb; margin: 0; font-size: 1.8rem; font-weight: 700;">
                Weather & Maritime Route Intelligence
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.95rem;">
                Real-time atmospheric hazard monitoring via Open-Meteo REST API, oceanic squall detection, and route waypoints.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_ports, tab_route, tab_evidence = st.tabs([
        "🌊 Port Atmospheric Telemetry",
        "🧭 Great-Circle Route Geodetics",
        "📜 Weather Evidence Ledger",
    ])

    # ── TAB 1: Live Port Weather ─────────────────────────────────
    with tab_ports:
        st.subheader("Live Maritime Port Weather Scanner")
        with db.session() as session:
            ports = PortCRUD.list_all(session)
            port_map = {f"{p.name} ({p.code}) - {p.country}": p for p in ports}

        if not port_map:
            st.info("No ports configured.")
        else:
            col_p, col_b = st.columns([7, 3])
            with col_p:
                sel_port_label = st.selectbox("Select Maritime Port", options=list(port_map.keys()))
                port = port_map[sel_port_label]
            with col_b:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                fetch_live = st.button("📡 Fetch Live Open-Meteo Data", use_container_width=True, type="primary")

            # Default or live weather
            client = WeatherAPIClient()
            intel = WeatherIntelligence(db_manager=db, api_client=client)

            if fetch_live:
                with st.spinner(f"Querying Open-Meteo API for {port.name} [{port.latitude:.2f}, {port.longitude:.2f}]..."):
                    weather_res = intel.evaluate_port_weather(port.id)
                    st.success(f"Weather data retrieved! Risk level: {weather_res.get('risk_level', 'NORMAL')}")

            # Fetch latest weather evidence for this port
            with db.session() as session:
                latest_w = (
                    session.query(WeatherEvidence)
                    .filter(WeatherEvidence.port_id == port.id)
                    .order_by(WeatherEvidence.recorded_at.desc())
                    .first()
                )

            if latest_w:
                w1, w2, w3, w4 = st.columns(4)
                with w1:
                    render_kpi("Temperature", f"{latest_w.temperature_celsius:.1f} °C" if latest_w.temperature_celsius else "N/A")
                with w2:
                    render_kpi("Wind Speed", f"{latest_w.wind_speed_kmh:.1f} km/h" if latest_w.wind_speed_kmh else "N/A")
                with w3:
                    render_kpi("Precipitation", f"{latest_w.precipitation_mm:.1f} mm" if latest_w.precipitation_mm is not None else "0 mm")
                with w4:
                    render_kpi(
                        "Hazard Severity",
                        latest_w.severity.value.upper(),
                        delta="ALERT" if latest_w.severity in [WeatherSeverity.SEVERE, WeatherSeverity.EXTREME] else "Normal",
                        delta_color="danger" if latest_w.severity in [WeatherSeverity.SEVERE, WeatherSeverity.EXTREME] else "normal",
                    )

                st.markdown(
                    f"""
                    <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 16px; margin-top: 15px;">
                        <h4 style="margin: 0; color: #38bdf8;">{latest_w.event_type}</h4>
                        <p style="color: #d1d5db; margin: 8px 0 0 0;">{latest_w.description or 'No atmospheric warning active.'}</p>
                        <div style="color: #6b7280; font-size: 0.8rem; margin-top: 8px;">
                            Provider Source: <b>{latest_w.source}</b> | Recorded: <b>{latest_w.recorded_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("No weather evidence on record for this port yet. Click 'Fetch Live Open-Meteo Data' to query.")

    # ── TAB 2: Route Geodetics ───────────────────────────────────
    with tab_route:
        st.subheader("Maritime Route Distance & Waypoint Generator")
        with db.session() as session:
            ports = PortCRUD.list_all(session)
            p_names = {f"{p.name} ({p.code})": p for p in ports}

        if len(p_names) >= 2:
            rc1, rc2 = st.columns(2)
            with rc1:
                orig_label = st.selectbox("Origin Port", options=list(p_names.keys()), index=0, key="orig_route")
            with rc2:
                dest_label = st.selectbox("Destination Port", options=list(p_names.keys()), index=1, key="dest_route")

            p_orig = p_names[orig_label]
            p_dest = p_names[dest_label]

            dist_km = RouteOptimizer.haversine_distance_km(p_orig.latitude, p_orig.longitude, p_dest.latitude, p_dest.longitude)
            dist_nm = RouteOptimizer.haversine_distance_nm(p_orig.latitude, p_orig.longitude, p_dest.latitude, p_dest.longitude)
            steaming_days_18kn = dist_nm / (18 * 24)

            d1, d2, d3 = st.columns(3)
            with d1:
                render_kpi("Great-Circle Distance", f"{dist_nm:,.0f} NM", subtitle=f"{dist_km:,.0f} km")
            with d2:
                render_kpi("Steaming Time @ 18 knots", f"{steaming_days_18kn:.1f} Days", subtitle="Standard cargo speed")
            with d3:
                render_kpi("Fuel Consumption Est.", f"{steaming_days_18kn * 32:.0f} Tons", subtitle="VLSFO marine fuel")

            waypoints = RouteOptimizer.interpolate_waypoints(p_orig.latitude, p_orig.longitude, p_dest.latitude, p_dest.longitude, num_waypoints=7)
            st.markdown("#### Waypoint Geodetic Coordinates")
            wp_rows = [{"Waypoint #": i + 1, "Latitude": f"{wp[0]:.4f}", "Longitude": f"{wp[1]:.4f}"} for i, wp in enumerate(waypoints)]
            st.dataframe(pd.DataFrame(wp_rows), use_container_width=True, hide_index=True)

    # ── TAB 3: Evidence Ledger ───────────────────────────────────
    with tab_evidence:
        st.subheader("Historical Weather Evidence Database")
        with db.session() as session:
            evidences = session.query(WeatherEvidence).order_by(WeatherEvidence.recorded_at.desc()).limit(20).all()
            if not evidences:
                st.info("No weather records found.")
            else:
                ev_rows = []
                for e in evidences:
                    ev_rows.append({
                        "Recorded (UTC)": e.recorded_at.strftime("%Y-%m-%d %H:%M"),
                        "Port": e.port.name if e.port else f"Port #{e.port_id}",
                        "Event": e.event_type,
                        "Severity": e.severity.value,
                        "Wind (km/h)": e.wind_speed_kmh,
                        "Precip (mm)": e.precipitation_mm,
                        "Source": e.source,
                    })
                st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)


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

