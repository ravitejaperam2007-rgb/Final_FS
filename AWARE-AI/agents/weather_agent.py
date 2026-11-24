"""
AWARE-AI — Weather Intelligence Agent

Responsible for:
- Ingesting real atmospheric conditions along active corridors and ports via WeatherIntelligence.
- Evaluating disruption severity, wind thresholds, precipitation hazards.
- Formatting structured weather evidence dossiers for downstream risk agents.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from modules.weather.intelligence import WeatherIntelligence


class WeatherIntelligenceAgent(BaseAgent):
    """
    Autonomous agent continuously monitoring meteorological hazards.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="WeatherIntelligenceAgent", db_manager=db_manager)
        self.weather_intel = WeatherIntelligence(db_manager=db_manager)

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gathers live weather data for origin port, destination port, or en-route coordinates.
        """
        origin_port_id = context.get("origin_port_id")
        destination_port_id = context.get("destination_port_id")
        current_coordinates = context.get("current_coordinates")

        if origin_port_id and destination_port_id:
            route_weather = self.weather_intel.assess_route_weather_risk(
                origin_port_id=origin_port_id,
                destination_port_id=destination_port_id,
                current_coordinates=current_coordinates,
            )
            return {"type": "route_weather", "data": route_weather}

        if origin_port_id:
            port_weather = self.weather_intel.evaluate_port_weather(origin_port_id, persist_evidence=False)
            return {"type": "port_weather", "data": port_weather}

        raise ValueError("WeatherIntelligenceAgent requires origin_port_id or destination_port_id.")

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines weather severity level, operational impact, and route hazard alert.
        """
        data = perception.get("data", {})
        if perception.get("type") == "route_weather":
            peak_risk = data.get("peak_weather_risk", 0.0)
            severity = data.get("route_weather_severity", "minor")
            is_hazardous = peak_risk >= 0.50 or severity in ("severe", "extreme")

            actions = []
            if is_hazardous:
                actions.append("FLAG_METEOROLOGICAL_HAZARD")
                actions.append("RECOMMEND_SPEED_OR_CORRIDOR_DEVIATION")

            return {
                "peak_weather_risk": peak_risk,
                "composite_weather_risk": data.get("composite_weather_risk", 0.0),
                "severity": severity,
                "is_hazardous": is_hazardous,
                "advisory_actions": actions,
            }

        # Single port evaluation
        risk = data.get("weather_risk_score", 0.0)
        severity = data.get("severity", "minor")
        return {
            "peak_weather_risk": risk,
            "composite_weather_risk": risk,
            "severity": severity,
            "is_hazardous": risk >= 0.50,
            "advisory_actions": ["PORT_BERTH_ALERT"] if risk >= 0.50 else [],
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produces structured weather evidence payload for downstream orchestration.
        """
        return {
            "weather_severity": decision["severity"],
            "weather_risk_score": decision["peak_weather_risk"],
            "is_hazardous": decision["is_hazardous"],
            "recommended_alerts": decision["advisory_actions"],
        }
