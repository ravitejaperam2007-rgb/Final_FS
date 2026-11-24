"""
AWARE-AI — Central Multi-Agent Orchestrator

Coordinates the sequential and parallel execution of the 7 specialized autonomous agents:
1. Weather Intelligence Agent
2. Supplier Intelligence Agent
3. Risk Assessment Agent (LightGBM + Composite Risk + SHAP)
4. Root Cause Analysis Agent
5. Impact Assessment Agent
6. Mitigation Recommendation Agent
7. Resilience Planning Agent

Features:
- Full end-to-end multi-agent workflow dispatch.
- Structured communication between agents via immutable state context passing.
- Database execution tracking and history retrieval.
- Comprehensive fault isolation and diagnostics.
"""

from __future__ import annotations

import concurrent.futures
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from agents.impact_agent import ImpactAssessmentAgent
from agents.mitigation_agent import MitigationRecommendationAgent
from agents.resilience_agent import ResiliencePlanningAgent
from agents.risk_agent import RiskAssessmentAgent
from agents.root_cause_agent import RootCauseAnalysisAgent
from agents.supplier_agent import SupplierIntelligenceAgent
from agents.weather_agent import WeatherIntelligenceAgent
from database.connection import DatabaseManager
from database.crud import AgentExecutionCRUD, ShipmentCRUD
from utils.logger import get_logger

logger = get_logger("agents.orchestrator")


class AgentOrchestrator:
    """
    Central multi-agent orchestrator managing agent lifecycles, execution order,
    and workflow state.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager
        self.logger = logger
        self.agents: Dict[str, BaseAgent] = {}

        # Instantiate the 7 core specialized agents
        self.register(WeatherIntelligenceAgent(db_manager=db_manager))
        self.register(SupplierIntelligenceAgent(db_manager=db_manager))
        self.register(RiskAssessmentAgent(db_manager=db_manager))
        self.register(RootCauseAnalysisAgent(db_manager=db_manager))
        self.register(ImpactAssessmentAgent(db_manager=db_manager))
        self.register(MitigationRecommendationAgent(db_manager=db_manager))
        self.register(ResiliencePlanningAgent(db_manager=db_manager))

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance with the orchestrator."""
        self.agents[agent.name] = agent
        self.logger.info("Registered agent: %s", agent.name)

    def run_shipment_intelligence_cycle(
        self,
        shipment_id: int,
    ) -> Dict[str, Any]:
        """
        Executes the complete multi-agent intelligence cycle for a specific shipment:
        Perceive Environment (Weather + Supplier)
        -> Compute ML Probability & Composite Risk (Risk Assessment)
        -> Diagnose Root Causes (Root Cause Analysis)
        -> Evaluate Monetary & Operational Impact (Impact Assessment)
        -> Propose Targeted Mitigations (Mitigation Recommendation)
        -> Formulate Playbook (Resilience Planning)
        """
        start_ts = time.time()
        self.logger.info("Starting Multi-Agent intelligence cycle for shipment ID %s", shipment_id)

        # 1. Fetch shipment core coordinates and supplier linkage
        origin_port_id = None
        destination_port_id = None
        supplier_id = None
        current_coordinates = None

        if self.db:
            with self.db.session() as session:
                shipment = ShipmentCRUD.get(session, shipment_id)
                if not shipment:
                    raise ValueError(f"Shipment with ID {shipment_id} does not exist.")
                origin_port_id = shipment.origin_port_id
                destination_port_id = shipment.destination_port_id
                supplier_id = shipment.supplier_id
                if shipment.current_latitude is not None and shipment.current_longitude is not None:
                    current_coordinates = (shipment.current_latitude, shipment.current_longitude)

        workflow_context: Dict[str, Any] = {
            "shipment_id": shipment_id,
            "origin_port_id": origin_port_id,
            "destination_port_id": destination_port_id,
            "supplier_id": supplier_id,
            "current_coordinates": current_coordinates,
        }

        agent_logs: Dict[str, Any] = {}

        # Stage 1 & 2: Weather and Supplier Intelligence Agents (executed concurrently for optimal latency)
        weather_agent = self.agents["WeatherIntelligenceAgent"]
        supplier_agent = self.agents["SupplierIntelligenceAgent"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_weather = executor.submit(
                weather_agent.execute,
                {**workflow_context, "task_type": "weather_monitoring"},
            )
            future_supplier = executor.submit(
                supplier_agent.execute,
                {**workflow_context, "task_type": "supplier_evaluation"},
            )
            weather_out = future_weather.result()
            supplier_out = future_supplier.result()

        agent_logs["WeatherIntelligenceAgent"] = weather_out
        workflow_context["weather_findings"] = weather_out.get("action_result", {})

        agent_logs["SupplierIntelligenceAgent"] = supplier_out
        workflow_context["supplier_findings"] = supplier_out.get("action_result", {})

        # Stage 3: Risk Assessment Agent (LightGBM + Composite Risk + TreeSHAP)
        risk_agent = self.agents["RiskAssessmentAgent"]
        risk_out = risk_agent.execute({
            **workflow_context,
            "task_type": "predictive_risk_assessment",
        })
        agent_logs["RiskAssessmentAgent"] = risk_out
        workflow_context["risk_findings"] = risk_out.get("action_result", {})

        # Stage 4: Root Cause Analysis Agent
        root_cause_agent = self.agents["RootCauseAnalysisAgent"]
        root_cause_out = root_cause_agent.execute({
            **workflow_context,
            "task_type": "causal_diagnosis",
        })
        agent_logs["RootCauseAnalysisAgent"] = root_cause_out
        workflow_context["root_cause_findings"] = root_cause_out.get("action_result", {})

        # Stage 5: Impact Assessment Agent
        impact_agent = self.agents["ImpactAssessmentAgent"]
        impact_out = impact_agent.execute({
            **workflow_context,
            "task_type": "impact_sizing",
        })
        agent_logs["ImpactAssessmentAgent"] = impact_out
        workflow_context["impact_findings"] = impact_out.get("action_result", {})

        # Stage 6: Mitigation Recommendation Agent
        mitigation_agent = self.agents["MitigationRecommendationAgent"]
        mitigation_out = mitigation_agent.execute({
            **workflow_context,
            "task_type": "remediation_formulation",
        })
        agent_logs["MitigationRecommendationAgent"] = mitigation_out
        workflow_context["mitigation_findings"] = mitigation_out.get("action_result", {})

        # Stage 7: Resilience Planning Agent
        resilience_agent = self.agents["ResiliencePlanningAgent"]
        resilience_out = resilience_agent.execute({
            **workflow_context,
            "task_type": "resilience_playbook_design",
        })
        agent_logs["ResiliencePlanningAgent"] = resilience_out
        workflow_context["resilience_findings"] = resilience_out.get("action_result", {})

        total_duration_ms = int((time.time() - start_ts) * 1000)

        return {
            "shipment_id": shipment_id,
            "cycle_status": "completed",
            "total_duration_ms": total_duration_ms,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "weather_severity": workflow_context["weather_findings"].get("weather_severity"),
                "supplier_reliability": workflow_context["supplier_findings"].get("supplier_reliability"),
                "ml_delay_probability": workflow_context["risk_findings"].get("ml_delay_probability"),
                "composite_risk_score": workflow_context["risk_findings"].get("composite_risk_score"),
                "risk_classification": workflow_context["risk_findings"].get("risk_classification"),
                "primary_root_cause": workflow_context["root_cause_findings"].get("primary_cause", {}).get("description"),
                "estimated_financial_exposure_usd": workflow_context["impact_findings"].get("estimated_financial_exposure_usd"),
                "recommended_mitigations_count": len(workflow_context["mitigation_findings"].get("recommendations", [])),
                "resilience_playbook_name": workflow_context["resilience_findings"].get("name"),
            },
            "agent_executions": agent_logs,
        }

    def get_agent_execution_history(
        self,
        agent_name: Optional[str] = None,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Fetch agent execution logs and telemetry from SQLite.
        """
        if not self.db:
            return []

        with self.db.session() as session:
            if agent_name:
                records = AgentExecutionCRUD.list_by_agent(session, agent_name)
            else:
                # Query all recent agent executions
                from database.models import AgentExecution
                records = (
                    session.query(AgentExecution)
                    .order_by(AgentExecution.started_at.desc())
                    .limit(limit)
                    .all()
                )

            return [
                {
                    "id": r.id,
                    "agent_name": r.agent_name,
                    "task_type": r.task_type,
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "duration_ms": r.duration_ms,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "error_message": r.error_message,
                }
                for r in records
            ]
