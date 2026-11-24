"""
Unit tests for Operational Shipment Risk Indicators and Route tracking.
"""

import pytest

from database.crud import PortCRUD, RiskCRUD, ShipmentCRUD, SupplierCRUD
from modules.shipment.routes import RouteOptimizer
from modules.shipment.tracker import ShipmentRiskEvaluator
from modules.weather.api_client import WeatherAPIClient
from modules.weather.intelligence import WeatherIntelligence


class MockWeatherForShipment(WeatherAPIClient):
    def get_current_weather(self, latitude, longitude, force_refresh=False):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "recorded_at": "2026-11-23T12:00:00Z",
            "data_source": "LIVE_API",
            "data_freshness_seconds": 0,
            "is_synthetic": False,
            "event_type": "Severe Gale",
            "severity": "severe",
            "wind_speed_kmh": 85.0,
            "precipitation_mm": 20.0,
        }


class TestRouteOptimizer:
    def test_haversine_distance(self):
        # Distance between Tokyo (35.6762, 139.6503) and San Francisco (37.7749, -122.4194)
        dist_km = RouteOptimizer.haversine_distance_km(35.6762, 139.6503, 37.7749, -122.4194)
        assert 8000 < dist_km < 9000

        dist_nm = RouteOptimizer.haversine_distance_nm(35.6762, 139.6503, 37.7749, -122.4194)
        assert 4000 < dist_nm < 5000

    def test_interpolate_waypoints(self):
        waypoints = RouteOptimizer.interpolate_waypoints(0.0, 0.0, 10.0, 10.0, num_waypoints=3)
        assert len(waypoints) == 3
        assert waypoints[0] == (2.5, 2.5)
        assert waypoints[1] == (5.0, 5.0)
        assert waypoints[2] == (7.5, 7.5)


class TestShipmentRiskEvaluator:
    def test_evaluate_shipment_risk_and_persists_assessment(self, db):
        with db.session() as s:
            origin = PortCRUD.create(s, name="Shanghai Port", code="CNSHA", country="China", latitude=31.23, longitude=121.47)
            dest = PortCRUD.create(s, name="Hamburg Port", code="DEHAM", country="Germany", latitude=53.55, longitude=9.99)
            supplier = SupplierCRUD.create(s, name="Steel Supplier", country="China", reliability_score=0.60)
            shipment = ShipmentCRUD.create(
                s, tracking_id="TR-OP-RISK-01", origin_port_id=origin.id, destination_port_id=dest.id,
                supplier_id=supplier.id, priority="high",
            )
            ShipmentCRUD.update_status(s, shipment.id, "delayed")
            ship_id = shipment.id

        mock_client = MockWeatherForShipment()
        weather_intel = WeatherIntelligence(db_manager=db, api_client=mock_client)
        evaluator = ShipmentRiskEvaluator(db_manager=db, weather_intel=weather_intel)

        eval_res = evaluator.evaluate_shipment_risk(ship_id, persist_risk_assessment=True)

        assert eval_res["shipment_id"] == ship_id
        assert eval_res["composite_risk_score"] > 0.50
        assert eval_res["risk_level"] in ("high", "critical")
        assert len(eval_res["contributing_factors"]) >= 2
        assert eval_res["persisted_risk_assessment_id"] is not None

        # Verify RiskAssessment in database
        with db.session() as s:
            risk = RiskCRUD.get(s, eval_res["persisted_risk_assessment_id"])
            assert risk is not None
            assert risk.entity_type == "shipment"
            assert risk.entity_id == ship_id
            assert risk.risk_score == eval_res["composite_risk_score"]
