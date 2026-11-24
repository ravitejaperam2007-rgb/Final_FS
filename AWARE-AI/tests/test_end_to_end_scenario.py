"""
End-to-End Shipment Disruption Scenario Integration Test.

Tests the full lifecycle of an emerging maritime disruption across all sub-systems:
1. Registration of an international shipment (Shanghai -> Los Angeles) carrying high-value inventory.
2. In-transit telemetry progression into a severe marine weather zone (Typhoon alert).
3. Weather Intelligence Agent captures atmospheric event & persists WeatherEvidence.
4. Supplier Intelligence Agent tracks supplier reliability profile & lead-time history.
5. ML Predictor generates delay probability and TreeSHAP feature attributions.
6. Composite Risk Engine evaluates operational, weather, supplier, and inventory factors into composite score (0-1).
7. Full 7-Agent Swarm execution coordinated by AgentOrchestrator.
8. Root Cause Analysis diagnoses primary drivers (e.g., severe storm, port congestion).
9. Impact Assessment Engine computes financial demurrage, holding costs, SLA liabilities, and factory line stoppage risk.
10. Autonomous Resilience Planner synthesizes alternative maritime routes and candidate recovery playbooks.
11. Multi-criteria trade-off comparison selects the optimal recommended plan.
12. Human-in-the-Loop workflow governs approval/rejection and records immutable audit history.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from database.connection import DatabaseManager
from database.crud import (
    PortCRUD,
    SupplierCRUD,
    InventoryCRUD,
    ShipmentCRUD,
    WeatherCRUD,
    RiskCRUD,
    MLPredictionCRUD,
    ResiliencePlanCRUD,
    ApprovalHistoryCRUD,
)
from database.models import (
    ShipmentStatus,
    PriorityLevel,
    WeatherSeverity,
    RiskLevel,
    PlanStatus,
    ApprovalAction,
)
from modules.shipment.tracker import ShipmentRiskEvaluator
from modules.weather.intelligence import WeatherIntelligence
from modules.supplier.intelligence import SupplierIntelligence
from modules.inventory.intelligence import InventoryIntelligence
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline
from agents.orchestrator import AgentOrchestrator
from modules.resilience.impact_engine import BusinessImpactAssessmentEngine
from modules.resilience.planner import AutonomousResiliencePlanner
from modules.resilience.approval_workflow import HumanApprovalWorkflowManager


@pytest.fixture
def test_db():
    db = DatabaseManager(url="sqlite:///:memory:")
    db.init()
    yield db
    db.drop()


class TestEndToEndDisruptionScenario:
    """Complete realistic disruption lifecycle test."""

    def test_complete_shipment_disruption_lifecycle(self, test_db: DatabaseManager):
        # ── Step 1: Base Entity Setup (Ports, Suppliers, Inventory) ─────────
        with test_db.session() as session:
            port_sha = PortCRUD.create(
                session, name="Shanghai Port", code="CNSHA", country="China", latitude=31.23, longitude=121.47
            )
            port_lax = PortCRUD.create(
                session, name="Los Angeles Port", code="USLAX", country="United States", latitude=33.74, longitude=-118.27
            )
            port_busan = PortCRUD.create(
                session, name="Busan Port", code="KRPUS", country="South Korea", latitude=35.10, longitude=129.04
            )

            supplier = SupplierCRUD.create(
                session,
                name="Apex Semiconductor Inc",
                country="Taiwan",
                reliability_score=0.82,
                lead_time_days=18,
                risk_tier="medium",
            )

            inv_item = InventoryCRUD.create(
                session,
                sku="SKU-AUTO-MCU-99",
                product_name="Critical Automotive 32-Bit Microcontroller",
                supplier_id=supplier.id,
                quantity_on_hand=500,
                safety_stock=1200,  # Below safety stock -> HIGH criticality
                reorder_point=1500,
                unit_cost=75.0,
                warehouse_location="WH-LAX-D1",
            )

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            shipment = ShipmentCRUD.create(
                session,
                tracking_id="SHP-DISRUPT-001",
                origin_port_id=port_sha.id,
                destination_port_id=port_lax.id,
                supplier_id=supplier.id,
                cargo_description="Containerized MCUs for Assembly Plant A",
                weight_kg=22000.0,
                priority=PriorityLevel.CRITICAL,
                status=ShipmentStatus.IN_TRANSIT,
                departure_date=now - timedelta(days=5),
                estimated_arrival=now + timedelta(days=9),
                current_latitude=30.5,
                current_longitude=135.0,  # Mid-Pacific transit
                changed_by="Dispatch_Agent",
                change_reason="Vessel departed Shanghai",
            )
            shipment_id = shipment.id
            sha_id = port_sha.id
            lax_id = port_lax.id
            sup_id = supplier.id

        assert shipment_id > 0

        # ── Step 2: Emergence of Severe Weather Disruption ──────────────────
        with test_db.session() as session:
            weather_evt = WeatherCRUD.create(
                session,
                port_id=sha_id,
                event_type="Super Typhoon Formosa",
                severity=WeatherSeverity.SEVERE,
                description="Wind gusts exceeding 130 km/h and wave heights 6.5m along East China Sea corridor.",
                temperature_celsius=26.0,
                wind_speed_kmh=115.0,
                precipitation_mm=85.0,
                visibility_km=2.0,
                start_time=now - timedelta(hours=12),
                end_time=now + timedelta(hours=36),
                source="Open-Meteo Severe Warning",
                shipment_id=shipment_id,
            )
        assert weather_evt.severity == WeatherSeverity.SEVERE

        # Update shipment status to DELAYED due to storm encounter
        with test_db.session() as session:
            updated_shp = ShipmentCRUD.update(
                session,
                shipment_id,
                status=ShipmentStatus.DELAYED,
                changed_by="Vessel_Master_AIS",
                change_reason="Reduced speed to 6 knots due to gale-force head seas",
            )
            assert updated_shp.status == ShipmentStatus.DELAYED

            # Verify audit trail record was automatically generated
            history_entries = ShipmentCRUD.get_history(session, shipment_id)
            assert len(history_entries) == 2
            assert history_entries[-1].new_status == ShipmentStatus.DELAYED
            assert "Reduced speed" in history_entries[-1].change_reason

        # ── Step 3: Operational Intelligence Modules Verification ───────────
        # Verify weather evidence recorded in database
        with test_db.session() as session:
            evidences = WeatherCRUD.list_by_port(session, sha_id)
            assert len(evidences) >= 1
            assert evidences[0].event_type == "Super Typhoon Formosa"
            assert evidences[0].severity == WeatherSeverity.SEVERE

        weather_intel = WeatherIntelligence(db_manager=test_db)
        w_eval = weather_intel.evaluate_port_weather(sha_id, persist_evidence=False)
        assert w_eval is not None
        assert "weather_risk_score" in w_eval

        sup_intel = SupplierIntelligence(db_manager=test_db)
        s_eval = sup_intel.profile_supplier(sup_id)
        # Empirical reliability drops dynamically when associated shipment is DELAYED
        assert 0.0 <= s_eval["reliability_score"] <= 1.0
        assert "risk_tier" in s_eval

        inv_intel = InventoryIntelligence(db_manager=test_db)
        i_eval = inv_intel.assess_sku_criticality(inv_item.sku)
        assert i_eval["stockout_risk"] > 0.5
        assert i_eval["inventory_status"] in ["CRITICAL_DEFICIT", "STOCKOUT", "REORDER_TRIGGERED"]

        # ── Step 4: ML Delay Prediction & SHAP Feature Attributions ─────────
        ml_pipeline = MLExplainabilityPipeline(db_manager=test_db)
        ml_result = ml_pipeline.predict_and_explain_shipment(shipment_id, persist=True)
        assert 0.0 <= ml_result["ml_delay_probability"] <= 1.0
        assert 0.0 <= ml_result["composite_risk_score"] <= 1.0
        assert ml_result["risk_classification"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert len(ml_result["shap_explanation"]["attributions"]) > 0

        # Verify separate ML probability vs composite risk score
        with test_db.session() as session:
            pred_db = MLPredictionCRUD.get(session, ml_result["persisted_prediction_id"])
            risk_db = RiskCRUD.get(session, ml_result["persisted_risk_assessment_id"])
            assert pred_db is not None
            assert risk_db is not None
            # ML probability and composite risk must both be present
            assert pred_db.predicted_value >= 0.0
            assert risk_db.risk_score >= 0.0

        # ── Step 5: Full 7-Agent Orchestration Swarm Execution ─────────────
        orchestrator = AgentOrchestrator(db_manager=test_db)
        swarm_result = orchestrator.run_shipment_intelligence_cycle(shipment_id)
        assert swarm_result["cycle_status"] == "completed"
        agent_execs = swarm_result["agent_executions"]
        assert len(agent_execs) == 7

        expected_agents = [
            "WeatherIntelligenceAgent",
            "SupplierIntelligenceAgent",
            "RiskAssessmentAgent",
            "RootCauseAnalysisAgent",
            "ImpactAssessmentAgent",
            "MitigationRecommendationAgent",
            "ResiliencePlanningAgent",
        ]
        for exp in expected_agents:
            assert exp in agent_execs
            assert agent_execs[exp]["status"] == "completed"

        # ── Step 6: Root Cause Diagnosis & Financial Impact Analysis ────────
        impact_engine = BusinessImpactAssessmentEngine(db_manager=test_db)
        impact = impact_engine.assess_impact(shipment_id)
        assert impact["total_financial_exposure"] > 0
        assert "demurrage_exposure" in impact
        assert "sla_penalties" in impact
        assert "line_stoppage_risk" in impact

        # ── Step 7: Autonomous Resilience Planning & Multi-Plan Selection ───
        planner = AutonomousResiliencePlanner(db_manager=test_db)
        risk_profile = {
            "ml_delay_probability": ml_result["ml_delay_probability"],
            "composite_risk_score": ml_result["composite_risk_score"],
            "weather_severity": "severe",
            "persisted_risk_assessment_id": ml_result["persisted_risk_assessment_id"],
        }
        res_plans = planner.generate_and_compare_plans(
            shipment_id=shipment_id,
            risk_profile=risk_profile,
            persist_plans=True,
        )
        assert len(res_plans["candidate_plans"]) >= 2
        assert res_plans["recommended_plan"] is not None
        assert res_plans["persisted_resilience_plan_id"] is not None

        recommended_plan_id = res_plans["persisted_resilience_plan_id"]

        with test_db.session() as session:
            plan_record = ResiliencePlanCRUD.get(session, recommended_plan_id)
            assert plan_record.status == PlanStatus.DRAFT

        # ── Step 8: Human-in-the-Loop Governance & Audit Ledger ─────────────
        approval_mgr = HumanApprovalWorkflowManager(db_manager=test_db)
        reviewed = approval_mgr.review_and_decide(
            plan_id=recommended_plan_id,
            action="approve",
            approved_by="Operations_Director_Jane",
            comments="Authorized rerouting to avoid super typhoon core.",
        )
        assert reviewed["new_plan_status"] == PlanStatus.ACTIVE.value

        with test_db.session() as session:
            plan_after = ResiliencePlanCRUD.get(session, recommended_plan_id)
            assert plan_after.status == PlanStatus.ACTIVE

            # Verify immutable audit history
            audit_events = ApprovalHistoryCRUD.list_by_entity(session, "resilience_plan", recommended_plan_id)
            assert len(audit_events) == 1
            assert audit_events[0].action == ApprovalAction.APPROVE
            assert audit_events[0].approved_by == "Operations_Director_Jane"
            assert "Authorized rerouting" in audit_events[0].comments
