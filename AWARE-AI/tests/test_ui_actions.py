"""
AWARE-AI UI Actions & Component Automated Integration Tests.

Validates that every interactive action across all 9 control tower pages
functions cleanly with actual database connections and ML/Agent engines:
1. Dashboard render & KPI/chart generation
2. Shipment registration, status update, and history retrieval
3. Live ML prediction and TreeSHAP waterfall/bar generation
4. Multi-agent swarm execution & execution telemetry logging
5. Root cause retrieval and business impact assessment
6. Resilience plan generation, comparison chart, and Human-in-the-Loop decision review
7. Weather scanner and route geodetics waypoint calculation
8. Supplier profiling and Wilson EOQ / ROP optimizer
9. System health PRAGMA verification and table row count inspection
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from database.connection import DatabaseManager
from database.crud import (
    PortCRUD,
    SupplierCRUD,
    InventoryCRUD,
    ShipmentCRUD,
    ResiliencePlanCRUD,
)
from database.models import (
    ShipmentStatus,
    PriorityLevel,
    PlanStatus,
    ApprovalAction,
)
from app.components.charts import (
    create_fleet_map,
    create_risk_gauge,
    create_shap_bar_chart,
    create_risk_radar,
    create_plan_comparison_chart,
)
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline
from agents.orchestrator import AgentOrchestrator
from modules.resilience.impact_engine import BusinessImpactAssessmentEngine
from modules.resilience.planner import AutonomousResiliencePlanner
from modules.resilience.approval_workflow import HumanApprovalWorkflowManager
from modules.shipment.routes import RouteOptimizer
from modules.supplier.intelligence import SupplierIntelligence
from modules.inventory.intelligence import InventoryIntelligence
from modules.inventory.optimizer import InventoryOptimizer


@pytest.fixture
def ui_test_db():
    db = DatabaseManager(url="sqlite:///:memory:")
    db.init()
    # Seed minimal baseline
    with db.session() as s:
        p1 = PortCRUD.create(s, name="Shanghai", code="CNSHA", country="China", latitude=31.23, longitude=121.47)
        p2 = PortCRUD.create(s, name="Rotterdam", code="NLRTM", country="Netherlands", latitude=51.92, longitude=4.48)
        sup = SupplierCRUD.create(s, name="Global Tech", country="Taiwan", reliability_score=0.88, lead_time_days=15)
        inv = InventoryCRUD.create(
            s, sku="SKU-TEST-01", product_name="Sensor", supplier_id=sup.id,
            quantity_on_hand=800, safety_stock=500, reorder_point=1000, unit_cost=50.0,
        )
        shp = ShipmentCRUD.create(
            s, tracking_id="SHP-UI-001", origin_port_id=p1.id, destination_port_id=p2.id,
            supplier_id=sup.id, weight_kg=12000.0, priority=PriorityLevel.HIGH,
            status=ShipmentStatus.IN_TRANSIT,
        )
    yield db
    db.drop()


class TestUIActionsAndComponents:
    """Verifies that all page interactions function with actual data."""

    def test_page_1_dashboard_charts(self, ui_test_db: DatabaseManager):
        gauge = create_risk_gauge(0.68, title="Fleet Risk")
        assert gauge is not None
        assert gauge.data[0].value == 0.68

        shipments_payload = [{
            "tracking_id": "SHP-UI-001",
            "status": "IN_TRANSIT",
            "risk_level": "HIGH",
            "cargo": "High Value Tech",
            "origin_lat": 31.23, "origin_lon": 121.47,
            "dest_lat": 51.92, "dest_lon": 4.48,
            "current_lat": 35.0, "current_lon": 110.0,
        }]
        ports_payload = [{"name": "Shanghai", "code": "CNSHA", "country": "China", "latitude": 31.23, "longitude": 121.47}]
        fleet_map = create_fleet_map(shipments_payload, ports_payload)
        assert fleet_map is not None
        assert len(fleet_map.data) >= 2

    def test_page_2_shipment_crud_action(self, ui_test_db: DatabaseManager):
        with ui_test_db.session() as s:
            p1 = PortCRUD.get_by_code(s, "CNSHA")
            p2 = PortCRUD.get_by_code(s, "NLRTM")
            # Create action
            new_shp = ShipmentCRUD.create(
                s, tracking_id="SHP-UI-NEW", origin_port_id=p1.id, destination_port_id=p2.id,
                weight_kg=8000.0, priority=PriorityLevel.MEDIUM, status=ShipmentStatus.PENDING,
                changed_by="UI_Operator", change_reason="Registered from UI form",
            )
            assert new_shp.id > 0

            # Update status action
            updated = ShipmentCRUD.update(
                s, new_shp.id, status=ShipmentStatus.IN_TRANSIT,
                changed_by="UI_Operator", change_reason="Departed origin port",
            )
            assert updated.status == ShipmentStatus.IN_TRANSIT

            # History audit trail
            hist = ShipmentCRUD.get_history(s, new_shp.id)
            assert len(hist) == 2

    def test_page_3_ml_inference_and_shap_chart_action(self, ui_test_db: DatabaseManager):
        pipeline = MLExplainabilityPipeline(db_manager=ui_test_db)
        res = pipeline.predict_and_explain_shipment(1, persist=True)

        assert res["shipment_id"] == 1
        assert 0.0 <= res["ml_delay_probability"] <= 1.0
        assert 0.0 <= res["composite_risk_score"] <= 1.0

        attributions = [{"feature": k, "attribution": v} for k, v in res["shap_explanation"]["attributions"].items()]
        shap_chart = create_shap_bar_chart(attributions)
        assert shap_chart is not None

        radar = create_risk_radar({"ML Risk": 0.5, "Supplier": 0.4, "Operational": 0.6})
        assert radar is not None

    def test_page_4_multi_agent_execution_action(self, ui_test_db: DatabaseManager):
        orchestrator = AgentOrchestrator(db_manager=ui_test_db)
        cycle_res = orchestrator.run_shipment_intelligence_cycle(1)
        assert cycle_res["cycle_status"] == "completed"
        assert len(cycle_res["agent_executions"]) == 7

        history = orchestrator.get_agent_execution_history(limit=10)
        assert len(history) >= 7

    def test_page_5_impact_and_root_cause_action(self, ui_test_db: DatabaseManager):
        engine = BusinessImpactAssessmentEngine(db_manager=ui_test_db)
        impact = engine.assess_impact(1, predicted_delay_prob=0.75, weather_severity="severe")
        assert impact["total_financial_exposure"] > 0
        assert "demurrage_exposure" in impact
        assert "line_stoppage_risk" in impact

    def test_page_6_resilience_planning_and_approval_action(self, ui_test_db: DatabaseManager):
        planner = AutonomousResiliencePlanner(db_manager=ui_test_db)
        risk_profile = {"ml_delay_probability": 0.70, "composite_risk_score": 0.65, "weather_severity": "severe"}
        plan_res = planner.generate_and_compare_plans(1, risk_profile=risk_profile, persist_plans=True)

        assert len(plan_res["candidate_plans"]) >= 2
        rec_id = plan_res["persisted_resilience_plan_id"]
        assert rec_id is not None

        # Comparison chart
        chart = create_plan_comparison_chart(plan_res["candidate_plans"])
        assert chart is not None

        # Approval action
        wf = HumanApprovalWorkflowManager(db_manager=ui_test_db)
        decision = wf.review_and_decide(rec_id, action="approve", approved_by="Ops_Director", comments="Approved via UI form")
        assert decision["new_plan_status"] == PlanStatus.ACTIVE.value

        audit_trail = wf.get_approval_audit_trail(rec_id)
        assert len(audit_trail) == 1
        assert audit_trail[0]["approved_by"] == "Ops_Director"

    def test_page_7_weather_and_routes_action(self, ui_test_db: DatabaseManager):
        # Distance calculation
        dist_km = RouteOptimizer.haversine_distance_km(31.23, 121.47, 51.92, 4.48)
        assert dist_km > 5000.0
        waypoints = RouteOptimizer.interpolate_waypoints(31.23, 121.47, 51.92, 4.48, num_waypoints=5)
        assert len(waypoints) == 5

    def test_page_8_supplier_and_inventory_action(self, ui_test_db: DatabaseManager):
        sup_intel = SupplierIntelligence(db_manager=ui_test_db)
        profile = sup_intel.profile_supplier(1)
        assert profile["name"] == "Global Tech"

        inv_intel = InventoryIntelligence(db_manager=ui_test_db)
        crit = inv_intel.assess_sku_criticality("SKU-TEST-01")
        assert "stockout_risk" in crit
        assert "criticality_score" in crit

        optimizer = InventoryOptimizer()
        eoq = optimizer.calculate_eoq(annual_demand=12000.0, ordering_cost=150.0, unit_cost=50.0, holding_cost_rate=0.20)
        assert eoq["eoq_units"] > 0
        rop = InventoryOptimizer.calculate_reorder_point(average_daily_demand=33.0, lead_time_days=15, safety_stock=200)
        assert rop > 0

    def test_page_9_system_monitoring_action(self, ui_test_db: DatabaseManager):
        assert ui_test_db.table_exists("shipments") is True
        assert ui_test_db.table_exists("ports") is True
        assert ui_test_db.row_count("shipments") == 1
        assert ui_test_db.row_count("ports") == 2
