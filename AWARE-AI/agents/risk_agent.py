"""
AWARE-AI — Risk Assessment Agent

Responsible for:
- Combining operational shipment indicators, live weather, supplier scoring, and ML delay probability.
- Executing the LightGBM ML pipeline and TreeSHAP feature attributions.
- Generating the transparent Composite Risk Score and Risk Classification.
- Persisting structured RiskAssessments and MLPredictions into SQLite.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline


class RiskAssessmentAgent(BaseAgent):
    """
    Autonomous agent coordinating predictive and composite risk evaluation.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="RiskAssessmentAgent", db_manager=db_manager)
        if db_manager:
            self.ml_pipeline = MLExplainabilityPipeline(db_manager=db_manager)
        else:
            self.ml_pipeline = None

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gathers shipment ID, weather agent findings, and supplier agent findings.
        """
        shipment_id = context.get("shipment_id")
        if not shipment_id:
            raise ValueError("RiskAssessmentAgent requires shipment_id in context.")

        weather_findings = context.get("weather_findings", {})
        supplier_findings = context.get("supplier_findings", {})

        return {
            "shipment_id": shipment_id,
            "weather_override": {
                "severity": weather_findings.get("weather_severity", "minor"),
                "wind_speed_kmh": weather_findings.get("wind_speed_kmh", 25.0),
                "precipitation_mm": weather_findings.get("precipitation_mm", 0.0),
            },
            "supplier_reliability": supplier_findings.get("supplier_reliability"),
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the LightGBM predictive model, extracts SHAP attributions,
        and computes the composite risk classification.
        """
        if not self.ml_pipeline:
            raise RuntimeError("DatabaseManager required for RiskAssessmentAgent decide phase.")

        shipment_id = perception["shipment_id"]
        weather_override = perception["weather_override"]

        # Run full pipeline with ML probability, composite risk, and SHAP
        eval_result = self.ml_pipeline.predict_and_explain_shipment(
            shipment_id=shipment_id,
            weather_override=weather_override,
            persist=True,
        )

        return eval_result

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structures risk evaluation dossier for root-cause and mitigation agents.
        """
        return {
            "shipment_id": decision["shipment_id"],
            "tracking_id": decision["tracking_id"],
            "ml_delay_probability": decision["ml_delay_probability"],
            "composite_risk_score": decision["composite_risk_score"],
            "risk_classification": decision["risk_classification"],
            "risk_breakdown": decision["risk_breakdown"],
            "shap_explanation": decision["shap_explanation"],
            "persisted_risk_assessment_id": decision.get("persisted_risk_assessment_id"),
            "persisted_prediction_id": decision.get("persisted_prediction_id"),
        }
