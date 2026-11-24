"""
AWARE-AI — Mitigation Recommendation Agent

Responsible for:
- Formulating concrete, actionable remediation steps for identified root causes.
- Estimating implementation costs and execution timeframe in days.
- Prioritizing recommendations and persisting MitigationRecommendations into SQLite.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from database.crud import MitigationCRUD
from database.models import PriorityLevel, RecommendationStatus


class MitigationRecommendationAgent(BaseAgent):
    """
    Autonomous agent synthesizing tailored remediation actions.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="MitigationRecommendationAgent", db_manager=db_manager)

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives risk assessments, root cause diagnoses, and impact assessments.
        """
        risk_data = context.get("risk_findings", {})
        root_causes = context.get("root_cause_findings", {})
        impact_data = context.get("impact_findings", {})

        return {
            "risk_assessment_id": risk_data.get("persisted_risk_assessment_id"),
            "root_causes": root_causes.get("root_causes", []),
            "persisted_cause_ids": root_causes.get("persisted_cause_ids", []),
            "impact_tier": impact_data.get("impact_tier", "MEDIUM"),
            "financial_exposure": impact_data.get("estimated_financial_exposure_usd", 10000.0),
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Matches specific operational strategies to root cause categories.
        """
        recommendations: List[Dict[str, Any]] = []
        root_causes = perception.get("root_causes", [])
        cause_ids = perception.get("persisted_cause_ids", [])

        for idx, cause in enumerate(root_causes):
            category = cause.get("cause_category")
            c_id = cause_ids[idx] if idx < len(cause_ids) else None

            if category == "weather":
                recommendations.append({
                    "root_cause_id": c_id,
                    "recommendation": "Initiate dynamic weather route deviation around storm cell via southern maritime passage.",
                    "priority": PriorityLevel.HIGH,
                    "estimated_cost": 8500.0,
                    "estimated_time_days": 2,
                })
            elif category == "supplier":
                recommendations.append({
                    "root_cause_id": c_id,
                    "recommendation": "Activate pre-vetted regional backup supplier and expedite 25% safety lot via express freight.",
                    "priority": PriorityLevel.HIGH,
                    "estimated_cost": 14000.0,
                    "estimated_time_days": 4,
                })
            elif category == "inventory":
                recommendations.append({
                    "root_cause_id": c_id,
                    "recommendation": "Reallocate safety stock from central logistics hub to destination assembly depot.",
                    "priority": PriorityLevel.MEDIUM,
                    "estimated_cost": 3200.0,
                    "estimated_time_days": 1,
                })
            else:
                recommendations.append({
                    "root_cause_id": c_id,
                    "recommendation": "Increase shipment GPS polling frequency and notify customer logistics coordinator.",
                    "priority": PriorityLevel.LOW,
                    "estimated_cost": 500.0,
                    "estimated_time_days": 1,
                })

        if not recommendations:
            recommendations.append({
                "root_cause_id": None,
                "recommendation": "Maintain standard tracking protocol with automated 6-hour checkpoint alerts.",
                "priority": PriorityLevel.LOW,
                "estimated_cost": 0.0,
                "estimated_time_days": 1,
            })

        return {
            "risk_assessment_id": perception.get("risk_assessment_id"),
            "recommendations": recommendations,
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists mitigation recommendations into SQLite database.
        """
        persisted_rec_ids = []
        risk_assessment_id = decision.get("risk_assessment_id")

        if self.db and risk_assessment_id:
            try:
                with self.db.session() as session:
                    for rec in decision["recommendations"]:
                        m = MitigationCRUD.create(
                            session,
                            risk_assessment_id=risk_assessment_id,
                            root_cause_id=rec.get("root_cause_id"),
                            recommendation=rec["recommendation"],
                            priority=rec.get("priority", PriorityLevel.MEDIUM),
                            estimated_cost=rec.get("estimated_cost"),
                            estimated_time_days=rec.get("estimated_time_days"),
                            status=RecommendationStatus.PROPOSED,
                            recommended_by=self.name,
                        )
                        persisted_rec_ids.append(m.id)
            except Exception as e:
                self.logger.warning("Could not persist mitigation recommendations: %s", e)

        return {
            "recommendations": decision["recommendations"],
            "persisted_mitigation_ids": persisted_rec_ids,
        }
