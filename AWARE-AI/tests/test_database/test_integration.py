"""
Integration tests for AWARE-AI backend services and database storage.

Validates end-to-end integration across:
- Shipments & status history
- Weather evidence attached to shipments & ports
- Suppliers & inventory tracking
- Risk assessment, root causes, mitigations & resilience playbooks
- ML predictions & SHAP explainability records
- Multi-agent execution lifecycle
"""

from datetime import datetime, timezone
import pytest

from database.models import (
    AgentTaskStatus,
    PlanStatus,
    PriorityLevel,
    RiskLevel,
    ShipmentStatus,
    WeatherSeverity,
)
from database.services import BackendIntegrationService
from database.crud import (
    ApprovalHistoryCRUD,
    InventoryCRUD,
    MitigationCRUD,
    PortCRUD,
    ResiliencePlanCRUD,
    RiskCRUD,
    ShipmentCRUD,
    SupplierCRUD,
    WeatherCRUD,
)


@pytest.fixture
def service(db):
    return BackendIntegrationService(db)


@pytest.fixture
def base_ports_and_supplier(db):
    with db.session() as s:
        p1 = PortCRUD.create(
            s, name="Port of Singapore", code="SGSIN", country="Singapore",
            latitude=1.3521, longitude=103.8198,
        )
        p2 = PortCRUD.create(
            s, name="Port of Rotterdam", code="NLRTM", country="Netherlands",
            latitude=51.9244, longitude=4.4777,
        )
        supplier = SupplierCRUD.create(
            s, name="Apex Semiconductor", country="Taiwan",
            contact_email="supply@apexsemi.com", reliability_score=0.96,
            lead_time_days=21, risk_tier="low",
        )
        return p1.id, p2.id, supplier.id


class TestBackendIntegration:
    """Integration test suite verifying end-to-end relational workflows."""

    def test_shipment_lifecycle_and_history_audit(self, service, base_ports_and_supplier):
        p1_id, p2_id, sup_id = base_ports_and_supplier

        # 1. Create shipment
        shipment = service.register_shipment(
            tracking_id="AWARE-TRACK-99",
            origin_port_id=p1_id,
            destination_port_id=p2_id,
            supplier_id=sup_id,
            cargo_description="Precision Microcontrollers",
            weight_kg=12500.5,
            priority="high",
            created_by="ops_agent",
        )
        assert shipment.id is not None
        assert shipment.status == ShipmentStatus.PENDING

        # Verify initial history
        with service.db.session() as s:
            history = ShipmentCRUD.get_history(s, shipment.id)
            assert len(history) == 1
            assert history[0].new_status == ShipmentStatus.PENDING
            assert history[0].changed_by == "ops_agent"

        # 2. Transition to in_transit
        service.transition_shipment_status(
            shipment_id=shipment.id,
            new_status="in_transit",
            changed_by="dispatcher",
            reason="Vessel departed berth 4",
        )

        with service.db.session() as s:
            history = ShipmentCRUD.get_history(s, shipment.id)
            assert len(history) == 2
            assert history[1].previous_status == ShipmentStatus.PENDING
            assert history[1].new_status == ShipmentStatus.IN_TRANSIT
            assert history[1].change_reason == "Vessel departed berth 4"

        # 3. Transition to delayed
        service.transition_shipment_status(
            shipment_id=shipment.id,
            new_status="delayed",
            changed_by="weather_agent",
            reason="Typhoon disruption on shipping corridor",
        )

        with service.db.session() as s:
            updated = ShipmentCRUD.get(s, shipment.id)
            assert updated.status == ShipmentStatus.DELAYED
            history = ShipmentCRUD.get_history(s, shipment.id)
            assert len(history) == 3

    def test_weather_evidence_integration_with_shipment(self, service, base_ports_and_supplier):
        p1_id, p2_id, sup_id = base_ports_and_supplier
        shipment = service.register_shipment(
            tracking_id="SHIP-WEATHER-01",
            origin_port_id=p1_id,
            destination_port_id=p2_id,
        )

        weather = service.attach_weather_to_shipment(
            shipment_id=shipment.id,
            port_id=p1_id,
            event_type="Tropical Cyclone",
            severity="extreme",
            start_time=datetime.now(timezone.utc),
            description="Category 4 cyclone affecting strait of Malacca",
            wind_speed_kmh=180.0,
            precipitation_mm=95.0,
            raw_data={"wind_gusts": 220, "alert_id": "WX-908"},
        )

        assert weather.id is not None
        assert weather.shipment_id == shipment.id
        assert weather.severity == WeatherSeverity.EXTREME

        # Test listing by shipment
        with service.db.session() as s:
            events = WeatherCRUD.list_by_shipment(s, shipment.id)
            assert len(events) == 1
            assert events[0].event_type == "Tropical Cyclone"

    def test_supplier_and_inventory_integration(self, service, base_ports_and_supplier):
        p1_id, p2_id, sup_id = base_ports_and_supplier

        with service.db.session() as s:
            item = InventoryCRUD.create(
                s,
                sku="MCU-ARM-01",
                product_name="ARM Cortex M4 SoC",
                supplier_id=sup_id,
                quantity_on_hand=3000,
                reorder_point=1000,
                safety_stock=500,
                unit_cost=4.25,
            )
            assert item.id is not None

        # Adjust quantity safely
        with service.db.session() as s:
            InventoryCRUD.adjust_quantity(s, item.id, -2200)
            low_stock = InventoryCRUD.list_low_stock(s)
            assert any(i.sku == "MCU-ARM-01" for i in low_stock)

    def test_comprehensive_risk_rootcause_mitigation_and_resilience_pipeline(
        self, service, base_ports_and_supplier
    ):
        p1_id, p2_id, sup_id = base_ports_and_supplier
        shipment = service.register_shipment(
            tracking_id="SHIP-RISK-PIPELINE",
            origin_port_id=p1_id,
            destination_port_id=p2_id,
            supplier_id=sup_id,
        )

        # Record full risk incident
        result = service.record_risk_incident(
            entity_type="shipment",
            entity_id=shipment.id,
            risk_category="weather",
            likelihood=0.85,
            impact=0.90,
            description="High risk of delay due to approaching storm",
            assessed_by="multi_agent_risk_evaluator",
            root_causes=[
                {
                    "cause_category": "weather",
                    "description": "Cyclone Gale trajectory overlaps primary shipping lane",
                    "contributing_factors": ["High sea state", "Port berth closures"],
                }
            ],
            mitigations=[
                {
                    "recommendation": "Reroute vessel via Sunda Strait and increase engine speed",
                    "priority": PriorityLevel.HIGH,
                    "estimated_cost": 15000.0,
                    "estimated_time_days": 2,
                }
            ],
        )

        risk = result["risk"]
        root_causes = result["root_causes"]
        mitigations = result["mitigations"]

        assert risk.id is not None
        assert risk.risk_level == RiskLevel.CRITICAL
        assert len(root_causes) == 1
        assert len(mitigations) == 1
        assert mitigations[0].root_cause_id == root_causes[0].id

        # Build Resilience Playbook
        plan = service.create_resilience_playbook(
            name="Cyclone Corridor Mitigation Playbook",
            risk_category="weather",
            strategies=["rerouting", "contingency_fuel_allocation", "priority_docking"],
            risk_assessment_id=risk.id,
            mitigation_id=mitigations[0].id,
            root_cause_id=root_causes[0].id,
            trigger_conditions={"wind_speed_kmh_threshold": 120},
            owner="Maritime Response Team",
        )

        assert plan.id is not None
        assert plan.risk_assessment_id == risk.id
        assert plan.mitigation_id == mitigations[0].id

        # Governance approval
        with service.db.session() as s:
            app = ApprovalHistoryCRUD.create(
                s,
                entity_type="resilience_plan",
                entity_id=plan.id,
                action="approve",
                approved_by="VP of Logistics",
                comments="Rerouting protocol approved for immediate dispatch.",
            )
            assert app.id is not None

            ResiliencePlanCRUD.update(s, plan.id, status=PlanStatus.ACTIVE)

        with service.db.session() as s:
            active_plans = ResiliencePlanCRUD.list_all(s, status="active", risk_assessment_id=risk.id)
            assert len(active_plans) == 1
            assert active_plans[0].name == "Cyclone Corridor Mitigation Playbook"

    def test_ml_prediction_and_agent_execution_storage(self, service):
        # 1. Log ML prediction with SHAP explanations
        pred = service.log_ml_prediction(
            model_name="xgboost_delay_predictor",
            model_version="v2.4.1",
            prediction_type="shipment_delay_prob",
            predicted_value=0.78,
            confidence=0.92,
            entity_type="shipment",
            entity_id=101,
            features={"wind_speed": 85, "port_congestion_index": 0.8},
            shap_values={"wind_speed": +0.42, "port_congestion_index": +0.36},
        )
        assert pred.id is not None
        assert pred.confidence == 0.92
        assert "wind_speed" in pred.shap_values_json

        # 2. Log Agent lifecycle
        exec_log = service.log_agent_lifecycle(
            agent_name="WeatherAgent",
            task_type="evaluate_route_safety",
            input_data={"corridor": "South China Sea", "waypoints": 5},
            output_data={"safe": False, "recommended_deviation_degrees": 18.5},
        )
        assert exec_log.id is not None
        assert exec_log.status == AgentTaskStatus.COMPLETED
        assert exec_log.duration_ms is not None
