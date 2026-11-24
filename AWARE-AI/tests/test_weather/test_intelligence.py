"""
Unit tests for Weather Intelligence with Open-Meteo, caching, and database persistence.
"""

import time
import pytest

from database.crud import PortCRUD, WeatherCRUD
from modules.weather.api_client import WeatherAPIClient
from modules.weather.intelligence import WeatherIntelligence


class MockWeatherClient(WeatherAPIClient):
    """Predictable weather client for deterministic offline testing."""

    def __init__(self, response_override=None):
        super().__init__()
        self.call_count = 0
        self.response_override = response_override

    def get_current_weather(self, latitude, longitude, force_refresh=False):
        self.call_count += 1
        if self.response_override:
            return self.response_override
        return {
            "latitude": latitude,
            "longitude": longitude,
            "recorded_at": "2026-11-23T12:00:00Z",
            "data_source": "LIVE_API",
            "data_freshness_seconds": 0,
            "is_synthetic": False,
            "event_type": "Thunderstorm",
            "severity": "severe",
            "temperature_celsius": 28.5,
            "wind_speed_kmh": 72.0,
            "precipitation_mm": 35.0,
            "weather_code": 95,
            "raw_payload": {"code": 95},
        }


class TestWeatherClientAndCaching:
    def test_cache_hit_prevents_duplicate_api_calls(self):
        client = WeatherAPIClient(cache_ttl_seconds=60)
        # Prepopulate cache
        client._cache["1.3521_103.8198"] = {
            "data": {
                "latitude": 1.3521,
                "longitude": 103.8198,
                "data_source": "LIVE_API",
                "severity": "minor",
                "event_type": "Clear sky",
            },
            "cached_at_ts": time.time(),
        }

        res = client.get_current_weather(1.3521, 103.8198)
        assert res["data_source"] == "CACHE"
        assert res["event_type"] == "Clear sky"
        assert res["data_freshness_seconds"] >= 0

    def test_api_network_failure_returns_unavailable_provenance(self):
        # Point client to an invalid URL to simulate offline/sandbox network failure
        client = WeatherAPIClient(timeout=1)
        client.BASE_URL = "http://127.0.0.1:59999/unreachable"
        res = client.get_current_weather(35.0, 139.0)

        assert res["data_source"] == "UNAVAILABLE"
        assert res["is_synthetic"] is False
        assert "Error" in res["error"]


class TestWeatherIntelligence:
    def test_evaluate_port_weather_and_persists_evidence(self, db):
        with db.session() as s:
            port = PortCRUD.create(
                s, name="Singapore Port", code="SGSIN", country="Singapore",
                latitude=1.3521, longitude=103.8198,
            )
            pid = port.id

        mock_client = MockWeatherClient()
        engine = WeatherIntelligence(db_manager=db, api_client=mock_client)

        result = engine.evaluate_port_weather(pid, persist_evidence=True)

        assert result["port_id"] == pid
        assert result["condition"] == "Thunderstorm"
        assert result["severity"] == "severe"
        assert result["weather_risk_score"] > 0.50
        assert result["evidence_id"] is not None

        # Verify record in database
        with db.session() as s:
            evidence = WeatherCRUD.get(s, result["evidence_id"])
            assert evidence is not None
            assert evidence.port_id == pid
            assert evidence.severity.value == "severe"

    def test_assess_route_weather_risk(self, db):
        with db.session() as s:
            p1 = PortCRUD.create(s, name="P1", code="P01", country="A", latitude=10.0, longitude=20.0)
            p2 = PortCRUD.create(s, name="P2", code="P02", country="B", latitude=30.0, longitude=40.0)
            p1_id, p2_id = p1.id, p2.id

        mock_client = MockWeatherClient()
        engine = WeatherIntelligence(db_manager=db, api_client=mock_client)

        route_eval = engine.assess_route_weather_risk(
            origin_port_id=p1_id,
            destination_port_id=p2_id,
            current_coordinates=(20.0, 30.0),
        )

        assert route_eval["composite_weather_risk"] > 0.0
        assert "route_weather_severity" in route_eval
        assert route_eval["enroute_condition"] is not None
