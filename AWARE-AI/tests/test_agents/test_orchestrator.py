"""
Unit and Integration Tests for AWARE-AI Multi-Agent AI System.

Tests:
1. BaseAgent error handling, duration tracking, and lifecycle logging.
2. Individual specialized agents:
   - WeatherIntelligenceAgent
   - SupplierIntelligenceAgent
   - RiskAssessmentAgent
   - RootCauseAnalysisAgent
   - ImpactAssessmentAgent
   - MitigationRecommendationAgent
   - ResiliencePlanningAgent
3. End-to-end multi-agent orchestration cycle on active shipments.
4. Agent execution history persistence and query verification in SQLite.
"""

import pytest

from agents.impact_agent import ImpactAssessmentAgent
from agents.mitigation_agent import MitigationRecommendationAgent
from agents.orchestrator import AgentOrchestrator
from agents.resilience_agent import ResiliencePlanningAgent
from agents.risk_agent import RiskAssessmentAgent
from agents.root_cause_agent import RootCauseAnalysisAgent
from agents.supplier_agent import SupplierIntelligenceAgent
from agents.weather_agent import WeatherIntelligenceAgent
from database.crud import AgentExecutionCRUD, PortCRUD, ShipmentCRUD, SupplierCRUD
from database.models import AgentTaskStatus


@pytest.fixture
def agent_environment(db):
    """Setup ports, supplier, and shipment for multi-agent workflows."""
    with db.session() as s:
        p1 = PortCRUD.create(
            s, name="Tokyo Port", code="JPTYO", country="Japan",
            latitude=35.61, longitude=139.77,
        )
        p2 = PortCRUD.create(
            s, name="San Francisco Port", code="USSFO", country="USA",
            latitude=37.81, longitude=-122.47,
        )
        sup = SupplierCRUD.create(
            s, name="Precision Motors Ltd", country="Japan",
            reliability_score=0.74, lead_time_days=25,
        )
        ship = ShipmentCRUD.create(
            s, tracking_id="AGENT-SHIP-01",
            origin_port_id=p1.id, destination_port_id=p2.id,
            supplier_id=sup.id, priority="high", weight_kg=18500.0,
        )
        return {
            "origin_port_id": p1.id,
            "destination_port_id": p2.id,
            "supplier_id": sup.id,
            "shipment_id": ship.id,
        }


class TestIndividualAgents:
    def test_weather_agent_execution(self, db, agent_environment):
        agent = WeatherIntelligenceAgent(db_manager=db)
        res = agent.execute({
            "origin_port_id": agent_environment["origin_port_id"],
            "destination_port_id": agent_environment["destination_port_id"],
            "task_type": "weather_monitoring",
        })
        assert res["status"] == "completed"
        assert "action_result" in res
        assert "weather_severity" in res["action_result"]
        assert "weather_risk_score" in res["action_result"]

    def test_supplier_agent_execution(self, db, agent_environment):
        agent = SupplierIntelligenceAgent(db_manager=db)
        res = agent.execute({
            "supplier_id": agent_environment["supplier_id"],
            "task_type": "supplier_evaluation",
        })
        assert res["status"] == "completed"
        assert res["action_result"]["supplier_id"] == agent_environment["supplier_id"]
        assert 0.0 <= res["action_result"]["supplier_reliability"] <= 1.0

    def test_risk_agent_execution(self, db, agent_environment):
        agent = RiskAssessmentAgent(db_manager=db)
        res = agent.execute({
            "shipment_id": agent_environment["shipment_id"],
            "weather_findings": {"weather_severity": "severe", "wind_speed_kmh": 70.0},
            "supplier_findings": {"supplier_reliability": 0.74},
            "task_type": "predictive_risk",
        })
        assert res["status"] == "completed"
        action_out = res["action_result"]
        assert "ml_delay_probability" in action_out
        assert "composite_risk_score" in action_out
        assert "shap_explanation" in action_out
        assert action_out["persisted_risk_assessment_id"] is not None

    def test_root_cause_agent_execution(self, db):
        agent = RootCauseAnalysisAgent(db_manager=db)
        res = agent.execute({
            "task_type": "causal_diagnosis",
            "risk_findings": {
                "composite_risk_score": 0.65,
                "risk_classification": "HIGH",
                "shap_explanation": {
                    "top_positive_drivers": [{"feature": "route_distance_nm", "impact": 0.22, "value": 4500}],
                },
            },
            "weather_findings": {"weather_severity": "severe"},
            "supplier_findings": {"supplier_reliability": 0.65, "supplier_name": "Vendor A"},
        })
        assert res["status"] == "completed"
        causes = res["action_result"]["root_causes"]
        assert len(causes) >= 2
        categories = [c["cause_category"] for c in causes]
        assert "weather" in categories
        assert "supplier" in categories

    def test_impact_agent_execution(self, db, agent_environment):
        agent = ImpactAssessmentAgent(db_manager=db)
        res = agent.execute({
            "shipment_id": agent_environment["shipment_id"],
            "task_type": "impact_sizing",
            "risk_findings": {"ml_delay_probability": 0.75, "composite_risk_score": 0.68},
            "root_cause_findings": {"primary_cause": {"cause_category": "weather"}},
        })
        assert res["status"] == "completed"
        action = res["action_result"]
        assert action["estimated_delay_days"] > 0
        assert action["estimated_financial_exposure_usd"] > 0
        assert action["impact_tier"] in ("MEDIUM", "HIGH", "CRITICAL")

    def test_mitigation_agent_execution(self, db):
        agent = MitigationRecommendationAgent(db_manager=db)
        res = agent.execute({
            "task_type": "remediation_formulation",
            "root_cause_findings": {
                "root_causes": [{"cause_category": "weather"}, {"cause_category": "supplier"}],
                "persisted_cause_ids": [10, 11],
            },
            "impact_findings": {"impact_tier": "HIGH", "estimated_financial_exposure_usd": 35000.0},
        })
        assert res["status"] == "completed"
        recs = res["action_result"]["recommendations"]
        assert len(recs) == 2
        assert recs[0]["estimated_cost"] > 0

    def test_resilience_agent_execution(self, db, agent_environment):
        # Create an actual risk assessment, root cause, and mitigation to satisfy foreign keys
        from database.crud import MitigationCRUD, RiskCRUD, RootCauseCRUD
        with db.session() as s:
            risk = RiskCRUD.create(
                s, entity_type="shipment", entity_id=agent_environment["shipment_id"],
                risk_category="weather", likelihood=0.7, impact=0.8,
            )
            rc = RootCauseCRUD.create(
                s, risk_assessment_id=risk.id,
                cause_category="weather", description="Storm gale",
            )
            mit = MitigationCRUD.create(
                s, risk_assessment_id=risk.id, root_cause_id=rc.id,
                recommendation="Reroute vessel",
            )
            r_id, rc_id, mit_id = risk.id, rc.id, mit.id

        agent = ResiliencePlanningAgent(db_manager=db)
        res = agent.execute({
            "shipment_id": agent_environment["shipment_id"],
            "task_type": "playbook_synthesis",
            "root_cause_findings": {
                "primary_cause": {"cause_category": "weather"},
                "persisted_cause_ids": [rc_id],
            },
            "mitigation_findings": {
                "recommendations": [{"recommendation": "Reroute"}],
                "persisted_mitigation_ids": [mit_id],
            },
            "risk_findings": {"persisted_risk_assessment_id": r_id},
        })
        assert res["status"] == "completed"
        action = res["action_result"]
        assert action["plan_id"] is not None
        assert "dynamic_rerouting" in action["strategies"]


class TestAgentOrchestrationWorkflow:
    def test_full_orchestration_cycle(self, db, agent_environment):
        orchestrator = AgentOrchestrator(db_manager=db)
        ship_id = agent_environment["shipment_id"]

        cycle_res = orchestrator.run_shipment_intelligence_cycle(shipment_id=ship_id)

        assert cycle_res["cycle_status"] == "completed"
        assert cycle_res["shipment_id"] == ship_id
        assert cycle_res["total_duration_ms"] > 0

        summary = cycle_res["summary"]
        assert summary["weather_severity"] is not None
        assert summary["ml_delay_probability"] is not None
        assert summary["composite_risk_score"] is not None
        assert summary["risk_classification"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert summary["primary_root_cause"] is not None
        assert summary["estimated_financial_exposure_usd"] > 0
        assert summary["recommended_mitigations_count"] > 0

        # Verify all 7 agents participated in the cycle
        executions = cycle_res["agent_executions"]
        expected_agents = [
            "WeatherIntelligenceAgent",
            "SupplierIntelligenceAgent",
            "RiskAssessmentAgent",
            "RootCauseAnalysisAgent",
            "ImpactAssessmentAgent",
            "MitigationRecommendationAgent",
            "ResiliencePlanningAgent",
        ]
        for name in expected_agents:
            assert name in executions
            assert executions[name]["status"] == "completed"

        # Verify execution history logging in SQLite
        history = orchestrator.get_agent_execution_history(limit=20)
        assert len(history) >= 7
        assert all(h["status"] == "completed" for h in history)
