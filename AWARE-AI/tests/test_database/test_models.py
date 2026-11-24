"""
Tests — ORM model definitions, constraints, and relationships.
"""

import pytest
from datetime import datetime, timezone

from database.models import (
    ALL_MODELS, Base, Port, Supplier, Shipment, ShipmentHistory,
    WeatherEvidence, Inventory, RiskAssessment, MLPrediction,
    AgentExecution, RootCause, MitigationRecommendation,
    ResiliencePlan, ApprovalHistory,
    ShipmentStatus, PriorityLevel, RiskLevel, WeatherSeverity,
    PlanStatus, ApprovalAction, AgentTaskStatus, RecommendationStatus,
)


class TestAllModelsRegistry:
    def test_count(self):
        assert len(ALL_MODELS) == 13

    def test_all_extend_base(self):
        for model in ALL_MODELS:
            assert issubclass(model, Base)

    def test_unique_table_names(self):
        names = [m.__tablename__ for m in ALL_MODELS]
        assert len(names) == len(set(names))


class TestEnums:
    def test_shipment_status_values(self):
        assert set(ShipmentStatus) == {
            ShipmentStatus.PENDING, ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.DELAYED, ShipmentStatus.DELIVERED,
            ShipmentStatus.CANCELLED,
        }

    def test_risk_level_values(self):
        assert set(RiskLevel) == {
            RiskLevel.LOW, RiskLevel.MEDIUM,
            RiskLevel.HIGH, RiskLevel.CRITICAL,
        }

    def test_weather_severity_values(self):
        assert set(WeatherSeverity) == {
            WeatherSeverity.MINOR, WeatherSeverity.MODERATE,
            WeatherSeverity.SEVERE, WeatherSeverity.EXTREME,
        }

    def test_plan_status_values(self):
        assert set(PlanStatus) == {
            PlanStatus.DRAFT, PlanStatus.ACTIVE, PlanStatus.ARCHIVED,
        }


class TestModelRepr:
    def test_port_repr(self, db):
        with db.session() as s:
            port = Port(name="Test", code="TST01", country="XX",
                        latitude=0.0, longitude=0.0)
            s.add(port)
            s.flush()
            assert "TST01" in repr(port)

    def test_shipment_repr(self, db):
        with db.session() as s:
            p1 = Port(name="A", code="AAA01", country="X", latitude=0, longitude=0)
            p2 = Port(name="B", code="BBB01", country="Y", latitude=1, longitude=1)
            s.add_all([p1, p2])
            s.flush()
            ship = Shipment(tracking_id="TR-001",
                            origin_port_id=p1.id, destination_port_id=p2.id)
            s.add(ship)
            s.flush()
            assert "TR-001" in repr(ship)


class TestRelationships:
    def test_port_to_weather(self, db):
        with db.session() as s:
            port = Port(name="P", code="P0001", country="X",
                        latitude=0, longitude=0)
            s.add(port)
            s.flush()
            w = WeatherEvidence(
                port_id=port.id, event_type="storm",
                severity=WeatherSeverity.SEVERE,
                start_time=datetime.now(timezone.utc),
            )
            s.add(w)
            s.flush()
            assert len(port.weather_events) == 1

    def test_shipment_to_history(self, db):
        with db.session() as s:
            p1 = Port(name="A", code="SH001", country="X", latitude=0, longitude=0)
            p2 = Port(name="B", code="SH002", country="Y", latitude=1, longitude=1)
            s.add_all([p1, p2])
            s.flush()
            ship = Shipment(tracking_id="REL-001",
                            origin_port_id=p1.id, destination_port_id=p2.id)
            s.add(ship)
            s.flush()
            h = ShipmentHistory(shipment_id=ship.id,
                                new_status=ShipmentStatus.IN_TRANSIT,
                                changed_by="test")
            s.add(h)
            s.flush()
            assert len(ship.history) == 1
            assert ship.history[0].new_status == ShipmentStatus.IN_TRANSIT

    def test_risk_to_root_causes(self, db):
        with db.session() as s:
            risk = RiskAssessment(
                entity_type="shipment", entity_id=1,
                risk_category="weather", likelihood=0.8, impact=0.9,
                risk_score=0.72, risk_level=RiskLevel.CRITICAL,
            )
            s.add(risk)
            s.flush()
            cause = RootCause(
                risk_assessment_id=risk.id,
                cause_category="weather",
                description="Typhoon approaching",
            )
            s.add(cause)
            s.flush()
            assert len(risk.root_causes) == 1

    def test_supplier_to_inventory(self, db):
        with db.session() as s:
            sup = Supplier(name="S", country="X")
            s.add(sup)
            s.flush()
            inv = Inventory(sku="SKU-1", product_name="Widget",
                            supplier_id=sup.id, quantity_on_hand=100)
            s.add(inv)
            s.flush()
            assert len(sup.inventory_items) == 1
