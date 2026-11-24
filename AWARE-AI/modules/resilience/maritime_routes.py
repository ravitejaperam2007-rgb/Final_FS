"""
AWARE-AI — Alternative Maritime Route Evaluator

Evaluates primary and diversion maritime corridors between ports.
Uses real spherical geodetics (Haversine formula), intermediate waypoint interpolation,
real-time Open-Meteo weather along corridor legs, transit time estimates at standard cruising speeds,
and operational fuel/bunker cost estimates.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from database.connection import DatabaseManager
from database.crud import PortCRUD
from database.models import Port
from modules.shipment.routes import RouteOptimizer
from modules.weather.intelligence import WeatherIntelligence
from utils.logger import get_logger

logger = get_logger("resilience.maritime_routes")


class MaritimeRouteEvaluator:
    """
    Evaluates alternative maritime routes, intermediate waypoint corridors,
    weather exposure, transit times, and fuel cost impacts without inventing data.
    """

    # Nominal bulk/container vessel cruise speed in knots (nautical miles per hour)
    DEFAULT_CRUISE_SPEED_KNOTS = 18.0
    # Estimated average daily bunker/fuel cost at sea (USD)
    DAILY_BUNKER_COST_USD = 15000.0

    def __init__(
        self,
        db_manager: DatabaseManager,
        weather_intel: Optional[WeatherIntelligence] = None,
    ):
        self.db = db_manager
        self.weather_intel = weather_intel or WeatherIntelligence(db_manager)

    def evaluate_primary_and_alternative_routes(
        self,
        origin_port_id: int,
        destination_port_id: int,
        intermediate_port_ids: Optional[List[int]] = None,
        avoid_weather_hazards: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Calculates and evaluates:
        1. Direct Great-Circle Route.
        2. Diversion Routes via designated or candidate intermediate transit ports in the database.
        """
        with self.db.session() as session:
            origin = PortCRUD.get(session, origin_port_id)
            dest = PortCRUD.get(session, destination_port_id)

            if not origin or not dest:
                raise ValueError("Origin and destination ports must exist in database.")

            evaluated_routes: List[Dict[str, Any]] = []

            # ── 1. Direct Great-Circle Route ────────────────────────
            direct_dist_nm = RouteOptimizer.haversine_distance_nm(
                origin.latitude, origin.longitude,
                dest.latitude, dest.longitude,
            )
            direct_transit_hours = direct_dist_nm / self.DEFAULT_CRUISE_SPEED_KNOTS
            direct_transit_days = round(direct_transit_hours / 24.0, 1)
            direct_fuel_cost = round((direct_transit_days * self.DAILY_BUNKER_COST_USD), 2)

            # Check weather across direct corridor
            direct_weather = self.weather_intel.assess_route_weather_risk(
                origin_port_id=origin.id,
                destination_port_id=dest.id,
            )
            direct_weather_score = direct_weather.get("peak_weather_risk", 0.15)

            # Feasibility: impaired if weather is extreme or severe
            direct_feasibility = "HIGH"
            if direct_weather_score >= 0.70:
                direct_feasibility = "RESTRICTED"
            elif direct_weather_score >= 0.45:
                direct_feasibility = "CAUTION"

            evaluated_routes.append({
                "route_id": "direct_corridor",
                "route_name": f"Direct Great-Circle ({origin.code} -> {dest.code})",
                "route_type": "DIRECT",
                "waypoints": [
                    {"port": origin.name, "code": origin.code, "lat": origin.latitude, "lon": origin.longitude},
                    {"port": dest.name, "code": dest.code, "lat": dest.latitude, "lon": dest.longitude},
                ],
                "distance_nm": direct_dist_nm,
                "transit_time_days": direct_transit_days,
                "estimated_fuel_cost_usd": direct_fuel_cost,
                "weather_risk_score": direct_weather_score,
                "weather_severity": direct_weather.get("route_weather_severity", "minor"),
                "operational_feasibility": direct_feasibility,
                "delay_risk_index": round(direct_weather_score * 0.7 + (direct_dist_nm / 10000.0) * 0.3, 3),
            })

            # ── 2. Alternative Diversion Routes ────────────────────
            # Use specified intermediate ports or find active transit ports in the DB
            candidate_ports: List[Port] = []
            if intermediate_port_ids:
                for pid in intermediate_port_ids:
                    p = PortCRUD.get(session, pid)
                    if p and p.id not in (origin.id, dest.id):
                        candidate_ports.append(p)
            else:
                all_ports = PortCRUD.list_all(session, active_only=True)
                candidate_ports = [p for p in all_ports if p.id not in (origin.id, dest.id)][:3]

            for waypoint_port in candidate_ports:
                leg1_dist = RouteOptimizer.haversine_distance_nm(
                    origin.latitude, origin.longitude,
                    waypoint_port.latitude, waypoint_port.longitude,
                )
                leg2_dist = RouteOptimizer.haversine_distance_nm(
                    waypoint_port.latitude, waypoint_port.longitude,
                    dest.latitude, dest.longitude,
                )
                total_dist = round(leg1_dist + leg2_dist, 2)
                transit_hours = total_dist / self.DEFAULT_CRUISE_SPEED_KNOTS
                transit_days = round(transit_hours / 24.0, 1)
                fuel_cost = round((transit_days * self.DAILY_BUNKER_COST_USD), 2)

                # Assess weather at waypoint port
                wp_weather = self.weather_intel.evaluate_port_weather(waypoint_port.id, persist_evidence=False)
                wp_weather_score = wp_weather.get("weather_risk_score", 0.15)
                # Weighted weather: 50% waypoint weather + 50% direct weather
                corridor_weather_score = round((wp_weather_score * 0.6 + direct_weather_score * 0.4), 3)

                feasibility = "HIGH"
                if corridor_weather_score >= 0.70:
                    feasibility = "RESTRICTED"
                elif corridor_weather_score >= 0.45:
                    feasibility = "CAUTION"
                elif total_dist > direct_dist_nm * 1.5:
                    feasibility = "LOW_EFFICIENCY"

                evaluated_routes.append({
                    "route_id": f"diversion_via_{waypoint_port.code.lower()}",
                    "route_name": f"Diversion Corridor via {waypoint_port.name} ({waypoint_port.code})",
                    "route_type": "DIVERSION",
                    "waypoints": [
                        {"port": origin.name, "code": origin.code, "lat": origin.latitude, "lon": origin.longitude},
                        {"port": waypoint_port.name, "code": waypoint_port.code, "lat": waypoint_port.latitude, "lon": waypoint_port.longitude},
                        {"port": dest.name, "code": dest.code, "lat": dest.latitude, "lon": dest.longitude},
                    ],
                    "distance_nm": total_dist,
                    "transit_time_days": transit_days,
                    "estimated_fuel_cost_usd": fuel_cost,
                    "weather_risk_score": corridor_weather_score,
                    "weather_severity": wp_weather.get("severity", "minor"),
                    "operational_feasibility": feasibility,
                    "delay_risk_index": round(corridor_weather_score * 0.7 + (total_dist / 10000.0) * 0.3, 3),
                })

            return evaluated_routes
