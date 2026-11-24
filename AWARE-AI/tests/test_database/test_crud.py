"""
Tests — CRUD operations for all 13 database tables.
"""

import pytest
from datetime import datetime, timezone

from database.crud import (
    PortCRUD, SupplierCRUD, ShipmentCRUD, WeatherCRUD,
    InventoryCRUD, RiskCRUD, MLPredictionCRUD,
    AgentExecutionCRUD, RootCauseCRUD, MitigationCRUD,
    ResiliencePlanCRUD, ApprovalHistoryCRUD,
)
from database.models import (
    ShipmentStatus, WeatherSeverity, RiskLevel,
    AgentTaskStatus, PlanStatus, ApprovalAction,
    PriorityLevel, RecommendationStatus,
)


# ============================================================
#  Port CRUD
# ============================================================
class TestPortCRUD:
    def test_create_and_get(self, db, sample_port_data):
        with db.session() as s:
            port = PortCRUD.create(s, **sample_port_data)
            assert port.id is not None
            assert port.code == "CNSHA"
            fetched = PortCRUD.get(s, port.id)
            assert fetched.name == "Shanghai"

    def test_get_by_code(self, db, sample_port_data):
        with db.session() as s:
            PortCRUD.create(s, **sample_port_data)
        with db.session() as s:
            port = PortCRUD.get_by_code(s, "CNSHA")
            assert port is not None
            assert port.country == "China"

    def test_list_all(self, db, sample_port_data, sample_port_data_b):
        with db.session() as s:
            PortCRUD.create(s, **sample_port_data)
            PortCRUD.create(s, **sample_port_data_b)
        with db.session() as s:
            ports = PortCRUD.list_all(s)
            assert len(ports) == 2

    def test_list_filter_country(self, db, sample_port_data, sample_port_data_b):
        with db.session() as s:
            PortCRUD.create(s, **sample_port_data)
            PortCRUD.create(s, **sample_port_data_b)
        with db.session() as s:
            china = PortCRUD.list_all(s, country="China")
            assert len(china) == 1

    def test_update(self, db, sample_port_data):
        with db.session() as s:
            port = PortCRUD.create(s, **sample_port_data)
            pid = port.id
        with db.session() as s:
            updated = PortCRUD.update(s, pid, name="Shanghai Port")
            assert updated.name == "Shanghai Port"

    def test_update_nonexistent(self, db):
        with db.session() as s:
            assert PortCRUD.update(s, 9999, name="X") is None

    def test_delete(self, db, sample_port_data):
        with db.session() as s:
            port = PortCRUD.create(s, **sample_port_data)
            pid = port.id
        with db.session() as s:
            assert PortCRUD.delete(s, pid) is True
        with db.session() as s:
            assert PortCRUD.get(s, pid) is None

    def test_delete_nonexistent(self, db):
        with db.session() as s:
            assert PortCRUD.delete(s, 9999) is False

    def test_create_invalid_latitude(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="latitude"):
                PortCRUD.create(s, name="X", code="X", country="X",
                                latitude=100.0, longitude=0.0)


# ============================================================
#  Supplier CRUD
# ============================================================
class TestSupplierCRUD:
    def test_create_and_get(self, db, sample_supplier_data):
        with db.session() as s:
            sup = SupplierCRUD.create(s, **sample_supplier_data)
            assert sup.id is not None
            assert sup.reliability_score == 0.92
        with db.session() as s:
            fetched = SupplierCRUD.get(s, sup.id)
            assert fetched.name == "Acme Components"

    def test_list_by_risk_tier(self, db, sample_supplier_data):
        with db.session() as s:
            SupplierCRUD.create(s, **sample_supplier_data)
            SupplierCRUD.create(s, name="Risky Corp", country="XX",
                                risk_tier="high", reliability_score=0.3)
        with db.session() as s:
            low = SupplierCRUD.list_all(s, risk_tier="low")
            assert len(low) == 1
            high = SupplierCRUD.list_all(s, risk_tier="high")
            assert len(high) == 1

    def test_update(self, db, sample_supplier_data):
        with db.session() as s:
            sup = SupplierCRUD.create(s, **sample_supplier_data)
            sid = sup.id
        with db.session() as s:
            updated = SupplierCRUD.update(s, sid, reliability_score=0.85)
            assert updated.reliability_score == 0.85

    def test_delete(self, db, sample_supplier_data):
        with db.session() as s:
            sup = SupplierCRUD.create(s, **sample_supplier_data)
            sid = sup.id
        with db.session() as s:
            assert SupplierCRUD.delete(s, sid) is True
        with db.session() as s:
            assert SupplierCRUD.get(s, sid) is None

    def test_invalid_email(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="email"):
                SupplierCRUD.create(s, name="X", country="X",
                                    contact_email="not-an-email")

    def test_invalid_reliability_score(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="reliability_score"):
                SupplierCRUD.create(s, name="X", country="X",
                                    reliability_score=1.5)


# ============================================================
#  Shipment CRUD
# ============================================================
class TestShipmentCRUD:
    def _make_ports(self, session):
        p1 = PortCRUD.create(session, name="A", code="A0001", country="X",
                              latitude=0.0, longitude=0.0)
        p2 = PortCRUD.create(session, name="B", code="B0001", country="Y",
                              latitude=1.0, longitude=1.0)
        return p1, p2

    def test_create_with_history(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ship = ShipmentCRUD.create(
                s, tracking_id="SH-100",
                origin_port_id=p1.id, destination_port_id=p2.id,
                cargo_description="Steel", weight_kg=10000.0,
            )
            assert ship.id is not None
            assert ship.status == ShipmentStatus.PENDING
            # first history entry auto-created
            history = ShipmentCRUD.get_history(s, ship.id)
            assert len(history) == 1
            assert history[0].new_status == ShipmentStatus.PENDING

    def test_get_by_tracking_id(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ShipmentCRUD.create(s, tracking_id="TRACK-1",
                                origin_port_id=p1.id, destination_port_id=p2.id)
        with db.session() as s:
            found = ShipmentCRUD.get_by_tracking_id(s, "TRACK-1")
            assert found is not None

    def test_update_status_adds_history(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ship = ShipmentCRUD.create(
                s, tracking_id="SH-200",
                origin_port_id=p1.id, destination_port_id=p2.id,
            )
            sid = ship.id
        with db.session() as s:
            ShipmentCRUD.update_status(s, sid, "in_transit",
                                       changed_by="dispatcher",
                                       reason="Departed port")
        with db.session() as s:
            history = ShipmentCRUD.get_history(s, sid)
            assert len(history) == 2
            assert history[1].new_status == ShipmentStatus.IN_TRANSIT
            assert history[1].changed_by == "dispatcher"

    def test_delivered_sets_actual_arrival(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ship = ShipmentCRUD.create(
                s, tracking_id="SH-300",
                origin_port_id=p1.id, destination_port_id=p2.id,
            )
            sid = ship.id
        with db.session() as s:
            updated = ShipmentCRUD.update_status(s, sid, "delivered")
            assert updated.actual_arrival is not None

    def test_list_by_status(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ShipmentCRUD.create(s, tracking_id="SH-A",
                                origin_port_id=p1.id, destination_port_id=p2.id)
            ship2 = ShipmentCRUD.create(s, tracking_id="SH-B",
                                        origin_port_id=p1.id, destination_port_id=p2.id)
            ShipmentCRUD.update_status(s, ship2.id, "in_transit")
        with db.session() as s:
            pending = ShipmentCRUD.list_all(s, status="pending")
            assert len(pending) == 1

    def test_same_origin_destination_rejected(self, db):
        with db.session() as s:
            p1, _ = self._make_ports(s)
            with pytest.raises(ValueError, match="Origin and destination"):
                ShipmentCRUD.create(s, tracking_id="BAD",
                                    origin_port_id=p1.id,
                                    destination_port_id=p1.id)

    def test_delete(self, db):
        with db.session() as s:
            p1, p2 = self._make_ports(s)
            ship = ShipmentCRUD.create(
                s, tracking_id="DEL-1",
                origin_port_id=p1.id, destination_port_id=p2.id,
            )
            sid = ship.id
        with db.session() as s:
            assert ShipmentCRUD.delete(s, sid) is True


# ============================================================
#  Weather Evidence CRUD
# ============================================================
class TestWeatherCRUD:
    def _make_port(self, session):
        return PortCRUD.create(session, name="P", code="WP001", country="X",
                                latitude=0.0, longitude=0.0)

    def test_create_and_list_by_port(self, db):
        with db.session() as s:
            port = self._make_port(s)
            WeatherCRUD.create(
                s, port_id=port.id, event_type="storm",
                severity="severe",
                start_time=datetime.now(timezone.utc),
                wind_speed_kmh=120.0,
            )
            WeatherCRUD.create(
                s, port_id=port.id, event_type="fog",
                severity="minor",
                start_time=datetime.now(timezone.utc),
            )
        with db.session() as s:
            events = WeatherCRUD.list_by_port(s, port.id)
            assert len(events) == 2

    def test_list_by_severity(self, db):
        with db.session() as s:
            port = self._make_port(s)
            WeatherCRUD.create(
                s, port_id=port.id, event_type="hurricane",
                severity="extreme",
                start_time=datetime.now(timezone.utc),
            )
        with db.session() as s:
            extreme = WeatherCRUD.list_by_severity(s, "extreme")
            assert len(extreme) == 1

    def test_invalid_severity(self, db):
        with db.session() as s:
            port = self._make_port(s)
            with pytest.raises(ValueError, match="severity"):
                WeatherCRUD.create(
                    s, port_id=port.id, event_type="rain",
                    severity="apocalyptic",
                    start_time=datetime.now(timezone.utc),
                )


# ============================================================
#  Inventory CRUD
# ============================================================
class TestInventoryCRUD:
    def test_create_and_get_by_sku(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            assert item.id is not None
        with db.session() as s:
            found = InventoryCRUD.get_by_sku(s, "ELEC-001")
            assert found is not None
            assert found.product_name == "Capacitor 100µF"

    def test_adjust_quantity_positive(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            iid = item.id
        with db.session() as s:
            updated = InventoryCRUD.adjust_quantity(s, iid, 200)
            assert updated.quantity_on_hand == 5200

    def test_adjust_quantity_negative(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            iid = item.id
        with db.session() as s:
            updated = InventoryCRUD.adjust_quantity(s, iid, -1000)
            assert updated.quantity_on_hand == 4000

    def test_adjust_quantity_below_zero_raises(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            iid = item.id
        with db.session() as s:
            with pytest.raises(ValueError, match="negative stock"):
                InventoryCRUD.adjust_quantity(s, iid, -99999)

    def test_list_low_stock(self, db):
        with db.session() as s:
            InventoryCRUD.create(s, sku="LOW-1", product_name="Low Item",
                                 quantity_on_hand=5, reorder_point=100)
            InventoryCRUD.create(s, sku="OK-1", product_name="OK Item",
                                 quantity_on_hand=500, reorder_point=100)
        with db.session() as s:
            low = InventoryCRUD.list_low_stock(s)
            assert len(low) == 1
            assert low[0].sku == "LOW-1"

    def test_update(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            iid = item.id
        with db.session() as s:
            updated = InventoryCRUD.update(s, iid, unit_cost=0.20)
            assert updated.unit_cost == 0.20

    def test_delete(self, db, sample_inventory_data):
        with db.session() as s:
            item = InventoryCRUD.create(s, **sample_inventory_data)
            iid = item.id
        with db.session() as s:
            assert InventoryCRUD.delete(s, iid) is True
        with db.session() as s:
            assert InventoryCRUD.get(s, iid) is None


# ============================================================
#  Risk Assessment CRUD
# ============================================================
class TestRiskCRUD:
    def test_create_auto_score(self, db):
        with db.session() as s:
            risk = RiskCRUD.create(
                s, entity_type="shipment", entity_id=1,
                risk_category="weather",
                likelihood=0.8, impact=0.9,
            )
            assert risk.risk_score == pytest.approx(0.72, abs=0.01)
            assert risk.risk_level == RiskLevel.HIGH

    def test_create_critical_level(self, db):
        with db.session() as s:
            risk = RiskCRUD.create(
                s, entity_type="supplier", entity_id=2,
                risk_category="geopolitical",
                likelihood=0.9, impact=0.95,
            )
            assert risk.risk_level == RiskLevel.CRITICAL

    def test_create_low_level(self, db):
        with db.session() as s:
            risk = RiskCRUD.create(
                s, entity_type="port", entity_id=3,
                risk_category="quality",
                likelihood=0.1, impact=0.2,
            )
            assert risk.risk_level == RiskLevel.LOW

    def test_list_by_entity(self, db):
        with db.session() as s:
            RiskCRUD.create(s, entity_type="shipment", entity_id=1,
                            risk_category="weather", likelihood=0.5, impact=0.5)
            RiskCRUD.create(s, entity_type="shipment", entity_id=1,
                            risk_category="logistics", likelihood=0.3, impact=0.4)
            RiskCRUD.create(s, entity_type="supplier", entity_id=2,
                            risk_category="financial", likelihood=0.6, impact=0.7)
        with db.session() as s:
            ship_risks = RiskCRUD.list_by_entity(s, "shipment", 1)
            assert len(ship_risks) == 2

    def test_count(self, db):
        with db.session() as s:
            RiskCRUD.create(s, entity_type="shipment", entity_id=1,
                            risk_category="weather", likelihood=0.9, impact=0.9)
            RiskCRUD.create(s, entity_type="supplier", entity_id=2,
                            risk_category="quality", likelihood=0.1, impact=0.1)
        with db.session() as s:
            assert RiskCRUD.count(s) == 2
            assert RiskCRUD.count(s, level="critical") == 1

    def test_invalid_entity_type(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="entity_type"):
                RiskCRUD.create(s, entity_type="unknown", entity_id=1,
                                risk_category="x", likelihood=0.5, impact=0.5)

    def test_likelihood_out_of_range(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="likelihood"):
                RiskCRUD.create(s, entity_type="shipment", entity_id=1,
                                risk_category="x", likelihood=1.5, impact=0.5)


# ============================================================
#  ML Prediction CRUD
# ============================================================
class TestMLPredictionCRUD:
    def test_create_and_get(self, db):
        with db.session() as s:
            pred = MLPredictionCRUD.create(
                s, model_name="demand_xgb", model_version="1.0",
                prediction_type="demand_forecast",
                entity_type="inventory", entity_id=1,
                predicted_value=1500.0, confidence=0.87,
                features_json='{"season": "Q4"}',
                shap_values_json='{"season": 0.3}',
            )
            assert pred.id is not None
        with db.session() as s:
            fetched = MLPredictionCRUD.get(s, pred.id)
            assert fetched.model_name == "demand_xgb"
            assert fetched.confidence == 0.87

    def test_list_by_model(self, db):
        with db.session() as s:
            MLPredictionCRUD.create(
                s, model_name="risk_rf", model_version="2.1",
                prediction_type="risk", predicted_value=0.65,
            )
            MLPredictionCRUD.create(
                s, model_name="risk_rf", model_version="2.1",
                prediction_type="risk", predicted_value=0.42,
            )
        with db.session() as s:
            results = MLPredictionCRUD.list_by_model(s, "risk_rf")
            assert len(results) == 2

    def test_invalid_confidence(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="confidence"):
                MLPredictionCRUD.create(
                    s, model_name="x", model_version="1",
                    prediction_type="y", predicted_value=1.0,
                    confidence=2.0,
                )


# ============================================================
#  Agent Execution CRUD
# ============================================================
class TestAgentExecutionCRUD:
    def test_create_and_complete(self, db):
        with db.session() as s:
            ex = AgentExecutionCRUD.create(
                s, agent_name="weather_agent",
                task_type="forecast_check",
                input_summary="Check Shanghai weather",
            )
            eid = ex.id
            assert ex.status == AgentTaskStatus.RUNNING
        with db.session() as s:
            completed = AgentExecutionCRUD.complete(
                s, eid, output_summary="No severe weather detected",
            )
            assert completed.status == AgentTaskStatus.COMPLETED
            assert completed.duration_ms is not None

    def test_complete_with_error(self, db):
        with db.session() as s:
            ex = AgentExecutionCRUD.create(
                s, agent_name="risk_agent", task_type="assess",
                input_summary="Check risk",
            )
            eid = ex.id
        with db.session() as s:
            failed = AgentExecutionCRUD.complete(
                s, eid, error_message="API timeout",
            )
            assert failed.status == AgentTaskStatus.FAILED
            assert failed.error_message == "API timeout"

    def test_list_by_agent(self, db):
        with db.session() as s:
            AgentExecutionCRUD.create(s, agent_name="inv_agent",
                                      task_type="reorder_check")
            AgentExecutionCRUD.create(s, agent_name="inv_agent",
                                      task_type="stock_alert")
            AgentExecutionCRUD.create(s, agent_name="ship_agent",
                                      task_type="track")
        with db.session() as s:
            inv = AgentExecutionCRUD.list_by_agent(s, "inv_agent")
            assert len(inv) == 2


# ============================================================
#  Root Cause CRUD
# ============================================================
class TestRootCauseCRUD:
    def _make_risk(self, session):
        return RiskCRUD.create(
            session, entity_type="shipment", entity_id=1,
            risk_category="weather", likelihood=0.7, impact=0.8,
        )

    def test_create_and_list(self, db):
        with db.session() as s:
            risk = self._make_risk(s)
            RootCauseCRUD.create(
                s, risk_assessment_id=risk.id,
                cause_category="weather",
                description="Typhoon Haiyan approaching sea lane",
                contributing_factors_json='["wind", "waves"]',
            )
            RootCauseCRUD.create(
                s, risk_assessment_id=risk.id,
                cause_category="logistics",
                description="Port congestion due to storm",
            )
        with db.session() as s:
            causes = RootCauseCRUD.list_by_risk(s, risk.id)
            assert len(causes) == 2

    def test_delete(self, db):
        with db.session() as s:
            risk = self._make_risk(s)
            cause = RootCauseCRUD.create(
                s, risk_assessment_id=risk.id,
                cause_category="supplier",
                description="Factory shutdown",
            )
            cid = cause.id
        with db.session() as s:
            assert RootCauseCRUD.delete(s, cid) is True


# ============================================================
#  Mitigation CRUD
# ============================================================
class TestMitigationCRUD:
    def _make_risk(self, session):
        return RiskCRUD.create(
            session, entity_type="supplier", entity_id=5,
            risk_category="financial", likelihood=0.6, impact=0.7,
        )

    def test_create_and_update_status(self, db):
        with db.session() as s:
            risk = self._make_risk(s)
            rec = MitigationCRUD.create(
                s, risk_assessment_id=risk.id,
                recommendation="Dual-source critical parts",
                priority=PriorityLevel.HIGH,
                estimated_cost=50000.0,
                estimated_time_days=30,
            )
            rid = rec.id
            assert rec.status == RecommendationStatus.PROPOSED
        with db.session() as s:
            updated = MitigationCRUD.update_status(s, rid, "accepted")
            assert updated.status == RecommendationStatus.ACCEPTED

    def test_list_by_risk(self, db):
        with db.session() as s:
            risk = self._make_risk(s)
            MitigationCRUD.create(
                s, risk_assessment_id=risk.id,
                recommendation="A",
            )
            MitigationCRUD.create(
                s, risk_assessment_id=risk.id,
                recommendation="B",
            )
        with db.session() as s:
            recs = MitigationCRUD.list_by_risk(s, risk.id)
            assert len(recs) == 2


# ============================================================
#  Resilience Plan CRUD
# ============================================================
class TestResiliencePlanCRUD:
    def test_create_and_get(self, db):
        with db.session() as s:
            plan = ResiliencePlanCRUD.create(
                s, name="Typhoon Response",
                description="Protocol for Pacific typhoon disruptions",
                risk_category="weather",
                strategies_json='["reroute", "buffer_stock"]',
                owner="ops_team",
            )
            assert plan.status == PlanStatus.DRAFT
            pid = plan.id
        with db.session() as s:
            fetched = ResiliencePlanCRUD.get(s, pid)
            assert fetched.name == "Typhoon Response"

    def test_update_to_active(self, db):
        with db.session() as s:
            plan = ResiliencePlanCRUD.create(
                s, name="Plan B", risk_category="logistics",
            )
            pid = plan.id
        with db.session() as s:
            updated = ResiliencePlanCRUD.update(s, pid, status=PlanStatus.ACTIVE)
            assert updated.status == PlanStatus.ACTIVE

    def test_list_by_status(self, db):
        with db.session() as s:
            ResiliencePlanCRUD.create(s, name="A", risk_category="x")
            p2 = ResiliencePlanCRUD.create(s, name="B", risk_category="y")
            ResiliencePlanCRUD.update(s, p2.id, status=PlanStatus.ACTIVE)
        with db.session() as s:
            drafts = ResiliencePlanCRUD.list_all(s, status="draft")
            assert len(drafts) == 1

    def test_invalid_status(self, db):
        with db.session() as s:
            with pytest.raises(ValueError, match="status"):
                ResiliencePlanCRUD.create(
                    s, name="X", risk_category="y", status="invalid",
                )


# ============================================================
#  Approval History CRUD
# ============================================================
class TestApprovalHistoryCRUD:
    def test_create_and_list(self, db):
        with db.session() as s:
            ApprovalHistoryCRUD.create(
                s, entity_type="resilience_plan", entity_id=1,
                action=ApprovalAction.APPROVE,
                approved_by="coo@company.com",
                comments="Looks good",
            )
            ApprovalHistoryCRUD.create(
                s, entity_type="resilience_plan", entity_id=1,
                action=ApprovalAction.REVISE,
                approved_by="cto@company.com",
                comments="Add budget",
            )
        with db.session() as s:
            entries = ApprovalHistoryCRUD.list_by_entity(s, "resilience_plan", 1)
            assert len(entries) == 2

    def test_delete(self, db):
        with db.session() as s:
            a = ApprovalHistoryCRUD.create(
                s, entity_type="mitigation", entity_id=5,
                action=ApprovalAction.REJECT,
                approved_by="admin",
            )
            aid = a.id
        with db.session() as s:
            assert ApprovalHistoryCRUD.delete(s, aid) is True
        with db.session() as s:
            assert ApprovalHistoryCRUD.get(s, aid) is None
