"""
AWARE-AI — Supplier Intelligence Agent

Responsible for:
- Evaluating supplier reliability metrics from empirical shipment outcomes.
- Profiling partner lead-time variance and delay frequency.
- Recommending dual-sourcing alternatives for underperforming suppliers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from database.connection import DatabaseManager
from modules.supplier.intelligence import SupplierIntelligence


class SupplierIntelligenceAgent(BaseAgent):
    """
    Autonomous agent managing supplier reliability and partner risk dossiers.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(name="SupplierIntelligenceAgent", db_manager=db_manager)
        if db_manager:
            self.supplier_intel = SupplierIntelligence(db_manager)
        else:
            self.supplier_intel = None

    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = context.get("supplier_id")
        if not supplier_id:
            # If no supplier is attached, return neutral baseline
            return {"has_supplier": False, "supplier_id": None}

        if not self.supplier_intel:
            raise RuntimeError("DatabaseManager required for SupplierIntelligenceAgent perception.")

        profile = self.supplier_intel.profile_supplier(supplier_id)
        alternatives = self.supplier_intel.find_alternatives(supplier_id, limit=3)

        return {
            "has_supplier": True,
            "supplier_id": supplier_id,
            "profile": profile,
            "alternatives": alternatives,
        }

    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        if not perception.get("has_supplier"):
            return {
                "supplier_reliability": 0.80,
                "supplier_risk_tier": "medium",
                "delay_vulnerability": "LOW",
                "requires_mitigation": False,
                "alternatives": [],
            }

        profile = perception["profile"]
        score = profile.get("reliability_score", 0.80)
        risk_tier = profile.get("risk_tier", "medium")
        metrics = profile.get("metrics", {})
        delay_rate = metrics.get("delay_rate") or 0.0

        requires_mitigation = score < 0.70 or risk_tier in ("high", "critical") or delay_rate > 0.25

        return {
            "supplier_id": perception["supplier_id"],
            "supplier_name": profile.get("name"),
            "supplier_reliability": score,
            "supplier_risk_tier": risk_tier,
            "delay_rate": delay_rate,
            "requires_mitigation": requires_mitigation,
            "alternatives": perception.get("alternatives", []),
        }

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "supplier_id": decision.get("supplier_id"),
            "supplier_name": decision.get("supplier_name"),
            "supplier_reliability": decision["supplier_reliability"],
            "supplier_risk_tier": decision["supplier_risk_tier"],
            "requires_mitigation": decision["requires_mitigation"],
            "recommended_alternatives": decision["alternatives"],
        }
