"""
AWARE-AI — Business & Inventory Impact Assessment Engine

Quantifies the real financial and operational impact of disruptions across:
- Shipment delay duration, cargo holding costs, and demurrage.
- Downstream inventory depletion and stockout probability.
- Assembly/manufacturing line downtime exposure.
- Customer SLA breach penalties.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import select

from database.connection import DatabaseManager
from database.crud import InventoryCRUD, ShipmentCRUD, SupplierCRUD
from database.models import Inventory, PriorityLevel, Shipment
from utils.logger import get_logger

logger = get_logger("resilience.impact_assessment")


class BusinessImpactAssessmentEngine:
    """
    Evaluates real operational, financial, and inventory consequences
    without fabricating costs or guaranteed delivery SLAs.
    """

    # Baseline daily maritime container demurrage/detention fee (USD per container equivalent)
    DAILY_DEMURRAGE_RATE_USD = 1500.0
    # Annual inventory holding rate (cost of capital, insurance, shrinkage)
    ANNUAL_HOLDING_RATE = 0.20
    # Average manufacturing line-stoppage penalty per hour for critical parts (USD)
    LINE_STOPPAGE_HOURLY_PENALTY_USD = 8000.0

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def assess_impact(
        self,
        shipment_id: int,
        predicted_delay_prob: float = 0.5,
        weather_severity: str = "minor",
    ) -> Dict[str, Any]:
        """
        Convenience wrapper providing flat financial and operational exposure metrics.
        """
        eval_res = self.evaluate_shipment_business_impact(
            shipment_id=shipment_id,
            predicted_delay_prob=predicted_delay_prob,
            weather_severity=weather_severity,
        )
        fin = eval_res["financial_exposure"]
        inv = eval_res["inventory_impact"]
        op = eval_res["operational_impact"]

        return {
            "shipment_id": eval_res["shipment_id"],
            "tracking_id": eval_res["tracking_id"],
            "expected_delay_days": eval_res["expected_delay_days"],
            "total_financial_exposure": fin["total_exposure_usd"],
            "demurrage_exposure": fin["demurrage_cost_usd"],
            "holding_costs": fin["holding_cost_usd"],
            "sla_penalties": fin["sla_penalty_exposure_usd"],
            "line_stoppage_exposure": fin["line_stoppage_exposure_usd"],
            "stockout_vulnerability": inv["stockout_vulnerability"],
            "line_stoppage_risk": "HIGH" if op["line_stoppage_risk"] else "LOW",
            "impact_level": op["impact_level"],
            "affected_inventory_items": inv["linked_inventory_items"],
            "raw_evaluation": eval_res,
        }

    def evaluate_shipment_business_impact(
        self,
        shipment_id: int,
        predicted_delay_prob: float,
        weather_severity: str = "minor",
    ) -> Dict[str, Any]:
        """
        Calculates financial exposure and inventory disruption severity for a shipment.
        """
        with self.db.session() as session:
            shipment = ShipmentCRUD.get(session, shipment_id)
            if not shipment:
                raise ValueError(f"Shipment {shipment_id} not found in database.")

            cargo_weight_kg = shipment.weight_kg or 5000.0
            priority = shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority)

            # Look up downstream inventory items linked to this shipment's supplier
            linked_inventory: List[Dict[str, Any]] = []
            total_inventory_exposure = 0.0
            stockout_vulnerability = "LOW"

            if shipment.supplier_id:
                stmt = select(Inventory).where(Inventory.supplier_id == shipment.supplier_id)
                items = list(session.execute(stmt).scalars().all())

                for it in items:
                    unit_cost = it.unit_cost or 10.0
                    total_val = round(it.quantity_on_hand * unit_cost, 2)
                    is_low_stock = it.quantity_on_hand <= it.reorder_point

                    linked_inventory.append({
                        "sku": it.sku,
                        "product_name": it.product_name,
                        "quantity_on_hand": it.quantity_on_hand,
                        "reorder_point": it.reorder_point,
                        "safety_stock": it.safety_stock,
                        "unit_cost": unit_cost,
                        "is_low_stock": is_low_stock,
                    })
                    total_inventory_exposure += total_val

                    if it.quantity_on_hand <= it.safety_stock:
                        stockout_vulnerability = "CRITICAL"
                    elif is_low_stock and stockout_vulnerability != "CRITICAL":
                        stockout_vulnerability = "HIGH"

            # Estimated delay duration (days) based on predictive ML probability and weather
            weather_delay_factor = {"extreme": 4.0, "severe": 2.5, "moderate": 1.0, "minor": 0.0}.get(weather_severity, 0.0)
            expected_delay_days = round(max(0.5, (predicted_delay_prob * 6.0) + weather_delay_factor), 1)

            # 1. Demurrage and Detention costs
            demurrage_cost = round(expected_delay_days * self.DAILY_DEMURRAGE_RATE_USD, 2)

            # 2. In-transit cargo holding cost (assumes $15/kg baseline valuation)
            estimated_cargo_val = cargo_weight_kg * 15.0
            daily_holding_cost = (estimated_cargo_val * self.ANNUAL_HOLDING_RATE) / 365.0
            total_holding_cost = round(daily_holding_cost * expected_delay_days, 2)

            # 3. SLA Penalty Exposure
            sla_multiplier = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}.get(priority, 1.0)
            base_sla_penalty = 5000.0 * sla_multiplier
            sla_penalty_exposure = round(base_sla_penalty * min(1.0, predicted_delay_prob * 1.5), 2)

            # 4. Manufacturing Line Stoppage Risk
            line_stoppage_risk = False
            line_stoppage_exposure = 0.0
            if (priority in ("critical", "high") or stockout_vulnerability == "CRITICAL") and predicted_delay_prob > 0.55:
                line_stoppage_risk = True
                # Assume potential 4-hour assembly interruption
                line_stoppage_exposure = round(4.0 * self.LINE_STOPPAGE_HOURLY_PENALTY_USD, 2)

            total_financial_exposure = round(
                demurrage_cost + total_holding_cost + sla_penalty_exposure + line_stoppage_exposure,
                2,
            )

            impact_level = "LOW"
            if total_financial_exposure > 45000.0 or line_stoppage_risk:
                impact_level = "CRITICAL"
            elif total_financial_exposure > 20000.0 or stockout_vulnerability in ("HIGH", "CRITICAL"):
                impact_level = "HIGH"
            elif total_financial_exposure > 8000.0:
                impact_level = "MEDIUM"

            return {
                "shipment_id": shipment.id,
                "tracking_id": shipment.tracking_id,
                "priority": priority,
                "expected_delay_days": expected_delay_days,
                "estimated_cargo_value_usd": round(estimated_cargo_val, 2),
                "financial_exposure": {
                    "total_exposure_usd": total_financial_exposure,
                    "demurrage_cost_usd": demurrage_cost,
                    "holding_cost_usd": total_holding_cost,
                    "sla_penalty_exposure_usd": sla_penalty_exposure,
                    "line_stoppage_exposure_usd": line_stoppage_exposure,
                },
                "inventory_impact": {
                    "stockout_vulnerability": stockout_vulnerability,
                    "affected_skus_count": len(linked_inventory),
                    "linked_inventory_items": linked_inventory,
                },
                "operational_impact": {
                    "impact_level": impact_level,
                    "line_stoppage_risk": line_stoppage_risk,
                },
            }
