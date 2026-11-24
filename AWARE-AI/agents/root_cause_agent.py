"""
AWARE-AI — Root Cause Analysis Agent

Responsible for:
- Analyzing SHAP positive drivers and empirical operational anomalies.
- Identifying primary and secondary root causes (e.g. meteorological gale, supplier lead-time slippage, route distance).
- Persisting structured RootCause entities linked to the active RiskAssessment in SQLite.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from database.crud import RootCauseCRUD


class RootCauseAnalysisAgent(BaseAgent):
    """
    Autonomous agent performing causal diagnosis on supply-chain risk alerts.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="RootCauseAnalysisAgent", db_manager=db_manager)

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives risk assessment outputs, SHAP explanations, weather, and supplier data.
        """
        risk_data = context.get("risk_findings", {})
        shap_explanation = risk_data.get("shap_explanation", {})
        weather_findings = context.get("weather_findings", {})
        supplier_findings = context.get("supplier_findings", {})

        return {
            "risk_assessment_id": risk_data.get("persisted_risk_assessment_id"),
            "composite_risk_score": risk_data.get("composite_risk_score", 0.0),
            "risk_classification": risk_data.get("risk_classification", "LOW"),
            "top_drivers": shap_explanation.get("top_positive_drivers", []),
            "weather_severity": weather_findings.get("weather_severity", "minor"),
            "supplier_reliability": supplier_findings.get("supplier_reliability", 0.85),
            "supplier_name": supplier_findings.get("supplier_name"),
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes causal diagnosis from top SHAP contributors and operational conditions.
        """
        diagnosed_causes: List[Dict[str, Any]] = []

        # 1. Weather Causality
        if perception["weather_severity"] in ("severe", "extreme"):
            diagnosed_causes.append({
                "cause_category": "weather",
                "description": f"Severe meteorological disruption ({perception['weather_severity']}) on active transit corridor.",
                "contributing_factors": ["High wind speed", "Wave action", "Reduced visibility"],
                "confidence": 0.92,
            })

        # 2. Supplier Causality
        if perception["supplier_reliability"] < 0.70:
            diagnosed_causes.append({
                "cause_category": "supplier",
                "description": f"Supplier reliability deficit for {perception.get('supplier_name') or 'assigned vendor'} (Score: {perception['supplier_reliability']}).",
                "contributing_factors": ["Historical delay frequency", "Lead time volatility"],
                "confidence": 0.85,
            })

        # 3. Check SHAP feature drivers
        for driver in perception.get("top_drivers", []):
            feat = driver.get("feature")
            if feat == "route_distance_nm" and driver.get("impact", 0) > 0.15:
                diagnosed_causes.append({
                    "cause_category": "logistics",
                    "description": f"Extended transit corridor distance ({driver.get('value')} NM) amplifies cumulative delay risk.",
                    "contributing_factors": ["Long-haul maritime route", "Multi-zone weather vulnerability"],
                    "confidence": 0.78,
                })
            elif feat == "inventory_stockout_risk" and driver.get("impact", 0) > 0.15:
                diagnosed_causes.append({
                    "cause_category": "inventory",
                    "description": "Downstream inventory depletion increases schedule sensitivity.",
                    "contributing_factors": ["Low safety stock", "High consumption velocity"],
                    "confidence": 0.82,
                })

        if not diagnosed_causes:
            diagnosed_causes.append({
                "cause_category": "operational",
                "description": "Minor operational schedule deviation within standard tolerance thresholds.",
                "contributing_factors": ["Routine maritime variance"],
                "confidence": 0.70,
            })

        return {
            "risk_assessment_id": perception.get("risk_assessment_id"),
            "diagnosed_causes": diagnosed_causes,
            "primary_cause": diagnosed_causes[0],
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists root cause records into database if risk_assessment_id is available.
        """
        persisted_cause_ids = []
        risk_assessment_id = decision.get("risk_assessment_id")

        if self.db and risk_assessment_id:
            try:
                with self.db.session() as session:
                    for cause in decision["diagnosed_causes"]:
                        rc = RootCauseCRUD.create(
                            session,
                            risk_assessment_id=risk_assessment_id,
                            cause_category=cause["cause_category"],
                            description=cause["description"],
                            contributing_factors_json=json.dumps(cause.get("contributing_factors", [])),
                            identified_by=self.name,
                        )
                        persisted_cause_ids.append(rc.id)
            except Exception as e:
                self.logger.warning("Could not persist root causes: %s", e)

        return {
            "root_causes": decision["diagnosed_causes"],
            "primary_cause": decision["primary_cause"],
            "persisted_cause_ids": persisted_cause_ids,
        }
