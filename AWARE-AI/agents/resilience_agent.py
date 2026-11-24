"""
AWARE-AI — Resilience Planning Agent

Responsible for:
- Assembling holistic, multi-strategy operational playbooks.
- Defining trigger conditions, strategic countermeasures (dual-sourcing, buffer allocation, rerouting).
- Persisting structured ResiliencePlan records into SQLite.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from database.crud import ResiliencePlanCRUD
from database.models import PlanStatus


class ResiliencePlanningAgent(BaseAgent):
    """
    Autonomous agent designing resilient contingency playbooks.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="ResiliencePlanningAgent", db_manager=db_manager)

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives root causes, mitigations, and shipment context.
        """
        risk_data = context.get("risk_findings", {})
        root_causes = context.get("root_cause_findings", {})
        mitigations = context.get("mitigation_findings", {})

        return {
            "shipment_id": context.get("shipment_id"),
            "risk_assessment_id": risk_data.get("persisted_risk_assessment_id"),
            "primary_cause": root_causes.get("primary_cause", {}),
            "recommendations": mitigations.get("recommendations", []),
            "persisted_mitigation_ids": mitigations.get("persisted_mitigation_ids", []),
            "persisted_cause_ids": root_causes.get("persisted_cause_ids", []),
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes a cohesive resilience playbook.
        """
        primary_cause = perception.get("primary_cause", {})
        category = primary_cause.get("cause_category", "operational")

        strategies = ["continuous_tracking"]
        triggers: Dict[str, Any] = {"risk_threshold": 0.45}

        if category == "weather":
            strategies.extend(["dynamic_rerouting", "contingency_fuel_allocation", "priority_docking_reservation"])
            triggers["wind_speed_kmh_threshold"] = 70.0
            triggers["weather_severity_alert"] = "severe"
            plan_name = f"Corridor Weather Contingency Playbook (Shipment #{perception.get('shipment_id')})"
        elif category == "supplier":
            strategies.extend(["dual_sourcing_activation", "air_freight_safety_split", "vendor_sla_audit"])
            triggers["supplier_delay_days_threshold"] = 3
            plan_name = f"Vendor Reliability Resilience Playbook (Shipment #{perception.get('shipment_id')})"
        else:
            strategies.extend(["safety_stock_reallocation", "customer_notification_protocol"])
            plan_name = f"Standard Operational Continuity Playbook (Shipment #{perception.get('shipment_id')})"

        return {
            "name": plan_name,
            "risk_category": category,
            "strategies": strategies,
            "trigger_conditions": triggers,
            "risk_assessment_id": perception.get("risk_assessment_id"),
            "mitigation_id": perception.get("persisted_mitigation_ids", [None])[0] if perception.get("persisted_mitigation_ids") else None,
            "root_cause_id": perception.get("persisted_cause_ids", [None])[0] if perception.get("persisted_cause_ids") else None,
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists the resilience playbook into SQLite.
        """
        plan_id = None
        if self.db:
            try:
                with self.db.session() as session:
                    plan = ResiliencePlanCRUD.create(
                        session,
                        name=decision["name"],
                        description=f"Automated resilience playbook for {decision['risk_category']} disruptions.",
                        risk_category=decision["risk_category"],
                        trigger_conditions_json=json.dumps(decision["trigger_conditions"]),
                        strategies_json=json.dumps(decision["strategies"]),
                        status=PlanStatus.DRAFT,
                        owner="Autonomous Resilience Engine",
                        risk_assessment_id=decision.get("risk_assessment_id"),
                        mitigation_id=decision.get("mitigation_id"),
                        root_cause_id=decision.get("root_cause_id"),
                    )
                    plan_id = plan.id
            except Exception as e:
                self.logger.warning("Could not persist resilience plan: %s", e)

        return {
            "plan_id": plan_id,
            "name": decision["name"],
            "risk_category": decision["risk_category"],
            "strategies": decision["strategies"],
            "trigger_conditions": decision["trigger_conditions"],
            "status": "draft",
        }
