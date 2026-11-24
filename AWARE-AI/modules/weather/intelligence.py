"""
AWARE-AI — Real-Time Weather Intelligence Engine

Ingests weather data for maritime ports and active shipment transit coordinates,
evaluates supply chain disruption severity, and persists weather evidence into SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from database.crud import PortCRUD, WeatherCRUD
from database.models import Port, WeatherEvidence, WeatherSeverity
from modules.weather.api_client import WeatherAPIClient
from utils.logger import get_logger

logger = get_logger("weather.intelligence")


class WeatherIntelligence:
    """
    Evaluates weather risk across logistics corridors and ports.
    Integrates directly with the database to store real weather evidence.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        api_client: Optional[WeatherAPIClient] = None,
    ):
        self.db = db_manager
        self.client = api_client or WeatherAPIClient()

    def evaluate_port_weather(
        self,
        port_id: int,
        persist_evidence: bool = True,
    ) -> Dict[str, Any]:
        """
        Assess current weather conditions for a registered port.
        Fetches live Open-Meteo data using port coordinates and optionally records evidence.
        """
        if not self.db:
            raise RuntimeError("DatabaseManager required to query port data.")

        with self.db.session() as session:
            port = PortCRUD.get(session, port_id)
            if not port:
                raise ValueError(f"Port with ID {port_id} not found.")

            weather_data = self.client.get_current_weather(
                latitude=port.latitude,
                longitude=port.longitude,
            )

            severity = weather_data.get("severity", "minor")
            event_type = weather_data.get("event_type", "Clear sky")

            evidence_id = None
            if persist_evidence and weather_data.get("data_source") in ("LIVE_API", "CACHE"):
                # Save into database
                evidence = WeatherCRUD.create(
                    session,
                    port_id=port.id,
                    event_type=event_type,
                    severity=severity,
                    description=(
                        f"{event_type} observed via Open-Meteo. "
                        f"Temp: {weather_data.get('temperature_celsius')}°C, "
                        f"Wind: {weather_data.get('wind_speed_kmh')} km/h, "
                        f"Precip: {weather_data.get('precipitation_mm')} mm. "
                        f"Source tag: {weather_data.get('data_source')}."
                    ),
                    temperature_celsius=weather_data.get("temperature_celsius"),
                    wind_speed_kmh=weather_data.get("wind_speed_kmh"),
                    precipitation_mm=weather_data.get("precipitation_mm"),
                    start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                    source=f"Open-Meteo ({weather_data.get('data_source')})",
                    raw_data_json=json.dumps(weather_data.get("raw_payload", {})),
                )
                evidence_id = evidence.id

            risk_score = self._compute_weather_risk_score(weather_data)

            return {
                "port_id": port.id,
                "port_code": port.code,
                "port_name": port.name,
                "country": port.country,
                "weather_risk_score": risk_score,
                "severity": severity,
                "condition": event_type,
                "temperature_celsius": weather_data.get("temperature_celsius"),
                "wind_speed_kmh": weather_data.get("wind_speed_kmh"),
                "precipitation_mm": weather_data.get("precipitation_mm"),
                "data_provenance": {
                    "source": weather_data.get("data_source"),
                    "freshness_seconds": weather_data.get("data_freshness_seconds"),
                    "is_synthetic": weather_data.get("is_synthetic", False),
                    "recorded_at": weather_data.get("recorded_at"),
                },
                "evidence_id": evidence_id,
                "warning": weather_data.get("warning") or weather_data.get("error"),
            }

    def assess_route_weather_risk(
        self,
        origin_port_id: int,
        destination_port_id: int,
        current_coordinates: Optional[tuple[float, float]] = None,
    ) -> Dict[str, Any]:
        """
        Assess overall weather risk across origin, destination, and current en-route location.
        """
        origin_eval = self.evaluate_port_weather(origin_port_id, persist_evidence=False)
        dest_eval = self.evaluate_port_weather(destination_port_id, persist_evidence=False)

        enroute_eval = None
        if current_coordinates:
            lat, lon = current_coordinates
            enroute_weather = self.client.get_current_weather(lat, lon)
            enroute_eval = {
                "coordinates": (lat, lon),
                "weather_risk_score": self._compute_weather_risk_score(enroute_weather),
                "severity": enroute_weather.get("severity", "minor"),
                "condition": enroute_weather.get("event_type", "Clear sky"),
                "wind_speed_kmh": enroute_weather.get("wind_speed_kmh"),
                "data_source": enroute_weather.get("data_source"),
            }

        scores = [origin_eval["weather_risk_score"], dest_eval["weather_risk_score"]]
        if enroute_eval:
            scores.append(enroute_eval["weather_risk_score"])

        max_risk = max(scores)
        overall_severity = "minor"
        if max_risk >= 0.75:
            overall_severity = "extreme"
        elif max_risk >= 0.50:
            overall_severity = "severe"
        elif max_risk >= 0.25:
            overall_severity = "moderate"

        return {
            "origin_port": origin_eval,
            "destination_port": dest_eval,
            "enroute_condition": enroute_eval,
            "composite_weather_risk": round(sum(scores) / len(scores), 3),
            "peak_weather_risk": round(max_risk, 3),
            "route_weather_severity": overall_severity,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _compute_weather_risk_score(self, weather_data: Dict[str, Any]) -> float:
        """
        Derive numeric risk index in range [0.0, 1.0].
        Combines wind velocity, gusts, precipitation intensity, and code severity.
        """
        if weather_data.get("data_source") == "UNAVAILABLE":
            return 0.15  # baseline uncertainty penalty for lack of live observation

        wind = weather_data.get("wind_speed_kmh") or 0.0
        precip = weather_data.get("precipitation_mm") or 0.0
        severity = weather_data.get("severity", "minor")

        # Wind factor: 0 at <=20kmh, 1.0 at >=100kmh
        wind_factor = min(max((wind - 20) / 80.0, 0.0), 1.0)
        # Precip factor: 0 at <=2mm, 1.0 at >=40mm
        precip_factor = min(max((precip - 2) / 38.0, 0.0), 1.0)

        severity_bonus = {
            "minor": 0.0,
            "moderate": 0.25,
            "severe": 0.60,
            "extreme": 0.90,
        }.get(severity, 0.1)

        raw_score = 0.4 * wind_factor + 0.3 * precip_factor + 0.3 * severity_bonus
        return round(min(max(raw_score, 0.0), 1.0), 3)
