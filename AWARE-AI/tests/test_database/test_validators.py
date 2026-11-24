"""
Tests — Validators (input validation before database writes).
"""

import pytest
from datetime import datetime, timezone

from database.validators import (
    validate_port_data,
    validate_supplier_data,
    validate_shipment_data,
    validate_weather_data,
    validate_inventory_data,
    validate_risk_data,
    validate_ml_prediction_data,
    validate_resilience_plan_data,
)


class TestPortValidation:
    def test_valid(self):
        validate_port_data(dict(name="A", code="AA", country="X",
                                latitude=0.0, longitude=0.0))

    def test_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            validate_port_data(dict(code="AA", country="X",
                                    latitude=0.0, longitude=0.0))

    def test_lat_too_high(self):
        with pytest.raises(ValueError, match="latitude"):
            validate_port_data(dict(name="A", code="AA", country="X",
                                    latitude=91.0, longitude=0.0))

    def test_lon_too_low(self):
        with pytest.raises(ValueError, match="longitude"):
            validate_port_data(dict(name="A", code="AA", country="X",
                                    latitude=0.0, longitude=-181.0))

    def test_code_too_long(self):
        with pytest.raises(ValueError, match="code"):
            validate_port_data(dict(name="A", code="X" * 21, country="X",
                                    latitude=0.0, longitude=0.0))


class TestSupplierValidation:
    def test_valid_minimal(self):
        validate_supplier_data(dict(name="S", country="C"))

    def test_bad_email(self):
        with pytest.raises(ValueError, match="email"):
            validate_supplier_data(dict(name="S", country="C",
                                        contact_email="bad"))

    def test_reliability_out_of_range(self):
        with pytest.raises(ValueError, match="reliability_score"):
            validate_supplier_data(dict(name="S", country="C",
                                        reliability_score=-0.1))

    def test_negative_lead_time(self):
        with pytest.raises(ValueError, match="lead_time_days"):
            validate_supplier_data(dict(name="S", country="C",
                                        lead_time_days=-5))

    def test_invalid_risk_tier(self):
        with pytest.raises(ValueError, match="risk_tier"):
            validate_supplier_data(dict(name="S", country="C",
                                        risk_tier="extreme"))


class TestShipmentValidation:
    def test_valid(self):
        validate_shipment_data(dict(tracking_id="T1",
                                    origin_port_id=1, destination_port_id=2))

    def test_same_ports(self):
        with pytest.raises(ValueError, match="Origin and destination"):
            validate_shipment_data(dict(tracking_id="T1",
                                        origin_port_id=1, destination_port_id=1))

    def test_zero_weight(self):
        with pytest.raises(ValueError, match="weight_kg"):
            validate_shipment_data(dict(tracking_id="T1",
                                        origin_port_id=1, destination_port_id=2,
                                        weight_kg=0))

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            validate_shipment_data(dict(tracking_id="T1",
                                        origin_port_id=1, destination_port_id=2,
                                        status="flying"))


class TestWeatherValidation:
    def test_valid(self):
        validate_weather_data(dict(port_id=1, event_type="storm",
                                   severity="severe",
                                   start_time=datetime.now(timezone.utc)))

    def test_bad_severity(self):
        with pytest.raises(ValueError, match="severity"):
            validate_weather_data(dict(port_id=1, event_type="storm",
                                       severity="apocalyptic",
                                       start_time=datetime.now(timezone.utc)))

    def test_negative_wind(self):
        with pytest.raises(ValueError, match="wind_speed"):
            validate_weather_data(dict(port_id=1, event_type="storm",
                                       severity="minor",
                                       start_time=datetime.now(timezone.utc),
                                       wind_speed_kmh=-10))


class TestInventoryValidation:
    def test_valid(self):
        validate_inventory_data(dict(sku="X", product_name="Y"))

    def test_negative_qty(self):
        with pytest.raises(ValueError, match="quantity_on_hand"):
            validate_inventory_data(dict(sku="X", product_name="Y",
                                         quantity_on_hand=-1))

    def test_negative_cost(self):
        with pytest.raises(ValueError, match="unit_cost"):
            validate_inventory_data(dict(sku="X", product_name="Y",
                                         unit_cost=-5.0))


class TestRiskValidation:
    def test_valid(self):
        validate_risk_data(dict(entity_type="shipment", entity_id=1,
                                risk_category="weather",
                                likelihood=0.5, impact=0.5))

    def test_bad_entity_type(self):
        with pytest.raises(ValueError, match="entity_type"):
            validate_risk_data(dict(entity_type="spaceship", entity_id=1,
                                    risk_category="x",
                                    likelihood=0.5, impact=0.5))

    def test_likelihood_above_one(self):
        with pytest.raises(ValueError, match="likelihood"):
            validate_risk_data(dict(entity_type="shipment", entity_id=1,
                                    risk_category="x",
                                    likelihood=1.1, impact=0.5))


class TestMLPredictionValidation:
    def test_valid(self):
        validate_ml_prediction_data(dict(model_name="m", model_version="1",
                                          prediction_type="demand",
                                          predicted_value=100.0))

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence"):
            validate_ml_prediction_data(dict(model_name="m", model_version="1",
                                              prediction_type="demand",
                                              predicted_value=100.0,
                                              confidence=1.5))


class TestResiliencePlanValidation:
    def test_valid(self):
        validate_resilience_plan_data(dict(name="P", risk_category="weather"))

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            validate_resilience_plan_data(dict(name="P", risk_category="x",
                                               status="invalid"))
