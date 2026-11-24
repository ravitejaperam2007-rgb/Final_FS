"""
AWARE-AI — Impact Assessment Agent

Responsible for:
- Quantifying operational, financial, and supply-chain repercussions of predicted delays.
- Computing estimated financial exposure, factory line-stoppage risk, and customer SLA breach penalty.
- Providing impact severity sizing for downstream mitigation decisions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from database.crud import InventoryCRUD, ShipmentCRUD


class ImpactAssessmentAgent(BaseAgent):
    """
    Autonomous agent evaluating operational and monetary impact of supply chain disruptions.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="ImpactAssessmentAgent", db_manager=db_manager)

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reads shipment details, cargo valuation, and root cause severity.
        """
        shipment_id = context.get("shipment_id")
        risk_data = context.get("risk_findings", {})
        root_causes = context.get("root_cause_findings", {})

        cargo_weight = 5000.0
        priority = "medium"
        supplier_id = None

        if self.db and shipment_id:
            with self.db.session() as session:
                shipment = ShipmentCRUD.get(session, shipment_id)
                if shipment:
                    cargo_weight = shipment.weight_kg or 5000.0
                    priority = shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority)
                    supplier_id = shipment.supplier_id

        return {
            "shipment_id": shipment_id,
            "cargo_weight_kg": cargo_weight,
            "priority": priority,
            "supplier_id": supplier_id,
            "ml_delay_probability": risk_data.get("ml_delay_probability", 0.20),
            "composite_risk_score": risk_data.get("composite_risk_score", 0.20),
            "primary_cause": root_causes.get("primary_cause", {}),
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates estimated financial exposure, SLA penalty risk, and operational criticality.
        """
        weight = perception["cargo_weight_kg"]
        priority = perception["priority"]
        delay_prob = perception["ml_delay_probability"]
        comp_risk = perception["composite_risk_score"]

        # Base estimated cargo valuation ($12 per kg default)
        estimated_cargo_value = weight * 12.0

        # Estimated delay in days based on ML probability
        estimated_delay_days = round(max(1.0, delay_prob * 7.5), 1)

        # Financial exposure calculation: demurrage + inventory holding + SLA penalty
        demurrage_per_day = 1200.0
        holding_cost_rate = 0.0005  # daily holding rate
        sla_penalty_multiplier = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}.get(priority, 1.0)

        total_exposure = (
            (demurrage_per_day * estimated_delay_days)
            + (estimated_cargo_value * holding_cost_rate * estimated_delay_days)
            + (5000.0 * sla_penalty_multiplier * (1.0 if delay_prob > 0.50 else 0.2))
        )

        impact_tier = "LOW"
        if comp_risk >= 0.70 or total_exposure > 50000.0:
            impact_tier = "CRITICAL"
        elif comp_risk >= 0.45 or total_exposure > 20000.0:
            impact_tier = "HIGH"
        elif comp_risk >= 0.25:
            impact_tier = "MEDIUM"

        return {
            "estimated_delay_days": estimated_delay_days,
            "estimated_cargo_value_usd": round(estimated_cargo_value, 2),
            "estimated_financial_exposure_usd": round(total_exposure, 2),
            "impact_tier": impact_tier,
            "sla_breach_risk": round(min(1.0, delay_prob * sla_penalty_multiplier * 0.7), 2),
            "production_line_stoppage_risk": bool(priority in ("critical", "high") and delay_prob > 0.60),
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns structured impact metrics.
        """
        return decision
