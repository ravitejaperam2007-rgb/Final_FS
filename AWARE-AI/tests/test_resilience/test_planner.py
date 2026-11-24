"""
Comprehensive Tests for AWARE-AI Impact Assessment & Autonomous Resilience Planning.

Tests:
1. Maritime alternative route evaluation (distances, transit times, fuel cost, feasibility).
2. Business impact assessment (delay days, demurrage, holding costs, line stoppage risk).
3. Candidate plan generation, tradeoff evaluation, and multi-criteria comparison.
4. Recommendation scoring and plain-language explanation reasoning.
5. Human-in-the-loop governance approval workflow (approve, reject, revise) and audit trail.
"""

import pytest

from database.crud import (
    ApprovalHistoryCRUD,
    InventoryCRUD,
    PortCRUD,
    ResiliencePlanCRUD,
    RiskCRUD,
    ShipmentCRUD,
    SupplierCRUD,
)
from database.models import PlanStatus
from modules.resilience.approval_workflow import HumanApprovalWorkflowManager
from modules.resilience.impact_engine import BusinessImpactAssessmentEngine
from modules.resilience.maritime_routes import MaritimeRouteEvaluator
from modules.resilience.planner import AutonomousResiliencePlanner


@pytest.fixture
def resilience_fixture(db):
    """Setup active ports, supplier, inventory, and shipment with high delay risk."""
    with db.session() as s:
        p1 = PortCRUD.create(
            s, name="Shanghai Port", code="CNSHA", country="China",
            latitude=31.2304, longitude=121.4737,
        )
        p2 = PortCRUD.create(
            s, name="Rotterdam Port", code="NLRTM", country="Netherlands",
            latitude=51.9244, longitude=4.4777,
        )
        p3 = PortCRUD.create(
            s, name="Singapore Port", code="SGSIN", country="Singapore",
            latitude=1.3521, longitude=103.8198,
        )
        sup = SupplierCRUD.create(
            s, name="EuroAsia Tech Components", country="China",
            reliability_score=0.68, lead_time_days=30,
        )
        # Create critical inventory linked to this supplier
        inv = InventoryCRUD.create(
            s, sku="CRIT-IC-01", product_name="Microprocessor Unit",
            supplier_id=sup.id, quantity_on_hand=80, reorder_point=200, safety_stock=100,
            unit_cost=85.0,
        )
        ship = ShipmentCRUD.create(
            s, tracking_id="RESILIENCE-SHIP-01",
            origin_port_id=p1.id, destination_port_id=p2.id,
            supplier_id=sup.id, priority="critical", weight_kg=22000.0,
        )
        risk = RiskCRUD.create(
            s, entity_type="shipment", entity_id=ship.id,
            risk_category="operational_delay",
            likelihood=0.80, impact=0.85, risk_score=0.68,
        )
        return {
            "origin_id": p1.id,
            "dest_id": p2.id,
            "waypoint_id": p3.id,
            "supplier_id": sup.id,
            "inventory_id": inv.id,
            "shipment_id": ship.id,
            "risk_id": risk.id,
        }


class TestMaritimeRouteEvaluator:
    def test_evaluate_direct_and_diversion_routes(self, db, resilience_fixture):
        evaluator = MaritimeRouteEvaluator(db)
        routes = evaluator.evaluate_primary_and_alternative_routes(
            origin_port_id=resilience_fixture["origin_id"],
            destination_port_id=resilience_fixture["dest_id"],
            intermediate_port_ids=[resilience_fixture["waypoint_id"]],
        )

        assert len(routes) >= 2
        direct = routes[0]
        assert direct["route_type"] == "DIRECT"
        assert direct["distance_nm"] > 4000.0
        assert direct["transit_time_days"] > 5.0
        assert direct["estimated_fuel_cost_usd"] > 10000.0
        assert direct["operational_feasibility"] in ("HIGH", "CAUTION", "RESTRICTED")

        diversion = routes[1]
        assert diversion["route_type"] == "DIVERSION"
        assert diversion["distance_nm"] >= direct["distance_nm"]


class TestBusinessImpactAssessmentEngine:
    def test_evaluate_shipment_business_impact(self, db, resilience_fixture):
        engine = BusinessImpactAssessmentEngine(db)
        impact = engine.evaluate_shipment_business_impact(
            shipment_id=resilience_fixture["shipment_id"],
            predicted_delay_prob=0.80,
            weather_severity="severe",
        )

        assert impact["shipment_id"] == resilience_fixture["shipment_id"]
        assert impact["expected_delay_days"] > 2.0
        fin = impact["financial_exposure"]
        assert fin["total_exposure_usd"] > 15000.0
        assert fin["demurrage_cost_usd"] > 0
        assert fin["holding_cost_usd"] > 0

        # High priority + delay probability > 0.55 triggers line stoppage risk check
        assert impact["operational_impact"]["line_stoppage_risk"] is True
        assert impact["operational_impact"]["impact_level"] == "CRITICAL"
        assert impact["inventory_impact"]["stockout_vulnerability"] in ("CRITICAL", "HIGH")


class TestAutonomousResiliencePlanner:
    def test_generate_and_compare_candidate_plans(self, db, resilience_fixture):
        planner = AutonomousResiliencePlanner(db)
        risk_profile = {
            "ml_delay_probability": 0.78,
            "composite_risk_score": 0.72,
            "weather_severity": "severe",
            "persisted_risk_assessment_id": resilience_fixture["risk_id"],
        }

        result = planner.generate_and_compare_plans(
            shipment_id=resilience_fixture["shipment_id"],
            risk_profile=risk_profile,
            persist_plans=True,
        )

        assert result["shipment_id"] == resilience_fixture["shipment_id"]
        assert len(result["candidate_plans"]) == 3
        assert result["recommended_plan"] is not None
        assert result["requires_human_approval"] is True
        assert result["persisted_resilience_plan_id"] is not None

        # Check recommended plan properties
        rec = result["recommended_plan"]
        assert "estimated_risk_reduction" in rec
        assert "projected_residual_risk" in rec
        assert rec["projected_residual_risk"] < result["initial_composite_risk"]
        assert "implementation_cost_usd" in rec

        # Check reasoning explanation
        reasoning = result["recommendation_reasoning"]
        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        assert rec["name"] in reasoning

        # Ensure persisted in SQLite with status DRAFT
        with db.session() as s:
            plan_db = ResiliencePlanCRUD.get(s, result["persisted_resilience_plan_id"])
            assert plan_db is not None
            assert plan_db.status == PlanStatus.DRAFT


class TestHumanApprovalWorkflow:
    def test_review_decision_approve_activates_plan_and_logs_audit(self, db, resilience_fixture):
        planner = AutonomousResiliencePlanner(db)
        plan_out = planner.generate_and_compare_plans(
            shipment_id=resilience_fixture["shipment_id"],
            risk_profile={"composite_risk_score": 0.70, "persisted_risk_assessment_id": resilience_fixture["risk_id"]},
        )
        plan_id = plan_out["persisted_resilience_plan_id"]

        workflow = HumanApprovalWorkflowManager(db)

        # 1. Authorize approval
        approval_res = workflow.review_and_decide(
            plan_id=plan_id,
            action="approve",
            approved_by="VP of Global Supply Operations",
            comments="Approved for immediate rerouting and buffer reallocation.",
            apply_operational_changes=True,
        )

        assert approval_res["decision"] == "approve"
        assert approval_res["new_plan_status"] == "active"
        assert approval_res["approval_history_id"] is not None

        # Verify DB plan status
        with db.session() as s:
            plan = ResiliencePlanCRUD.get(s, plan_id)
            assert plan.status == PlanStatus.ACTIVE
            assert plan.approved_at is not None

        # Verify audit trail history
        history = workflow.get_approval_audit_trail(plan_id)
        assert len(history) == 1
        assert history[0]["action"] == "approve"
        assert history[0]["approved_by"] == "VP of Global Supply Operations"

    def test_review_decision_reject(self, db, resilience_fixture):
        planner = AutonomousResiliencePlanner(db)
        plan_out = planner.generate_and_compare_plans(
            shipment_id=resilience_fixture["shipment_id"],
            risk_profile={"composite_risk_score": 0.50, "persisted_risk_assessment_id": resilience_fixture["risk_id"]},
        )
        plan_id = plan_out["persisted_resilience_plan_id"]

        workflow = HumanApprovalWorkflowManager(db)
        res = workflow.review_and_decide(
            plan_id=plan_id,
            action="reject",
            approved_by="Logistics Director",
            comments="Cost exceeds budget threshold.",
        )
        assert res["decision"] == "reject"
        assert res["new_plan_status"] == "archived"
