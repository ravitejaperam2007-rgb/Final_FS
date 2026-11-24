"""
AWARE-AI — Inventory Optimization & Criticality Engine

Computes:
- Stockout probability and safety stock coverage.
- Multi-factor inventory criticality index based on on-hand stock, reorder point, unit value, and supplier lead-time.
- Economic Order Quantity (EOQ) and dynamic replenishment triggers.
- Data freshness and inventory staleness detection.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import InventoryCRUD, SupplierCRUD
from database.models import Inventory
from utils.logger import get_logger

logger = get_logger("inventory.optimizer")


class InventoryOptimizer:
    """
    Inventory optimization calculus: Reorder points, safety stock buffers,
    and economic order quantity calculation.
    """

    @staticmethod
    def calculate_reorder_point(
        average_daily_demand: float,
        lead_time_days: int,
        safety_stock: int,
    ) -> int:
        """
        Standard formula: ROP = (Average Daily Demand × Lead Time) + Safety Stock
        """
        lead_time_demand = average_daily_demand * max(1, lead_time_days)
        return int(math.ceil(lead_time_demand + safety_stock))

    @staticmethod
    def calculate_safety_stock(
        max_daily_demand: float,
        avg_daily_demand: float,
        max_lead_time_days: int,
        avg_lead_time_days: int,
    ) -> int:
        """
        Standard buffer formula: (Max Demand × Max Lead Time) - (Avg Demand × Avg Lead Time)
        """
        buffer = (max_daily_demand * max_lead_time_days) - (avg_daily_demand * avg_lead_time_days)
        return max(0, int(math.ceil(buffer)))

    @staticmethod
    def economic_order_quantity(
        annual_demand: float,
        order_cost: float = 50.0,
        holding_cost_per_unit_year: float = 5.0,
    ) -> int:
        """
        Wilson EOQ formula: sqrt((2 * Demand * Order Cost) / Holding Cost)
        """
        if annual_demand <= 0 or holding_cost_per_unit_year <= 0:
            return 0
        eoq = math.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit_year)
        return int(math.ceil(eoq))

    def calculate_eoq(
        self,
        annual_demand: float,
        ordering_cost: float,
        unit_cost: float,
        holding_cost_rate: float,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper calculating Wilson EOQ with holding cost rate.
        """
        holding_per_unit = unit_cost * holding_cost_rate
        eoq = self.economic_order_quantity(annual_demand, ordering_cost, holding_per_unit)
        return {
            "eoq_units": eoq,
            "annual_demand": annual_demand,
            "ordering_cost": ordering_cost,
            "holding_cost_per_unit": holding_per_unit,
        }


class InventoryIntelligence:
    """
    Inventory Criticality and Health Assessment Engine.
    Directly connected to SQLite inventory and supplier records.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.optimizer = InventoryOptimizer()

    def assess_sku_criticality(self, sku: str) -> Dict[str, Any]:
        """
        Compute comprehensive criticality index for a specific SKU.
        Returns stockout risk, coverage ratio, freshness, and action recommendations.
        """
        with self.db.session() as session:
            item = InventoryCRUD.get_by_sku(session, sku)
            if not item:
                raise ValueError(f"SKU {sku!r} not found in inventory.")

            supplier = None
            lead_time = 14
            supplier_reliability = 0.85
            if item.supplier_id:
                supplier = SupplierCRUD.get(session, item.supplier_id)
                if supplier:
                    lead_time = supplier.lead_time_days or 14
                    supplier_reliability = supplier.reliability_score or 0.85

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            item_updated = item.updated_at or item.created_at
            freshness_seconds = int((now - item_updated).total_seconds()) if item_updated else 0

            # Compute stock ratios
            qoh = item.quantity_on_hand
            rop = item.reorder_point
            safety = item.safety_stock
            unit_cost = item.unit_cost

            # Stockout Risk factor:
            # 1.0 if stock == 0 (immediate stockout)
            # 0.8 if stock <= safety stock
            # 0.5 if stock <= reorder point
            # drops toward 0.0 as stock exceeds reorder point
            if qoh == 0:
                stock_risk = 1.0
                status = "STOCKOUT"
            elif qoh <= safety:
                stock_risk = 0.85
                status = "CRITICAL_DEFICIT"
            elif qoh <= rop:
                stock_risk = 0.50
                status = "REORDER_TRIGGERED"
            else:
                margin = (qoh - rop) / max(1, rop)
                stock_risk = max(0.05, 0.40 - 0.20 * min(margin, 2.0))
                status = "HEALTHY"

            # Supplier Lead-Time & Reliability weighting
            supplier_risk_component = (1.0 - supplier_reliability) * 0.5 + min(1.0, lead_time / 60.0) * 0.5

            # Cost Impact weighting: items with high unit cost create higher financial exposure
            cost_weight = min(1.0, unit_cost / 500.0)

            # Criticality Index in range [0.0, 1.0]
            # 50% Stockout Risk + 30% Supplier Delivery Risk + 20% Cost Exposure
            criticality_score = round(
                0.50 * stock_risk + 0.30 * supplier_risk_component + 0.20 * cost_weight,
                3,
            )

            urgency = "low"
            if criticality_score >= 0.75 or status in ("STOCKOUT", "CRITICAL_DEFICIT"):
                urgency = "critical"
            elif criticality_score >= 0.50 or status == "REORDER_TRIGGERED":
                urgency = "high"
            elif criticality_score >= 0.30:
                urgency = "medium"

            # Recommendations
            recommendations = []
            if status == "STOCKOUT":
                recommendations.append("Immediate emergency purchase requisition required.")
            elif status == "CRITICAL_DEFICIT":
                recommendations.append("Stock below safety threshold. Expedite open purchase orders.")
            elif status == "REORDER_TRIGGERED":
                recommendations.append("Reorder point reached. Generate replenishment order.")

            if supplier_reliability < 0.70:
                recommendations.append("Supplier reliability is low; consider dual-sourcing for this SKU.")

            return {
                "sku": item.sku,
                "product_name": item.product_name,
                "warehouse_location": item.warehouse_location,
                "quantity_on_hand": qoh,
                "reorder_point": rop,
                "safety_stock": safety,
                "unit_cost": unit_cost,
                "inventory_status": status,
                "criticality_score": criticality_score,
                "urgency_tier": urgency,
                "stockout_risk": round(stock_risk, 3),
                "supplier_info": {
                    "supplier_id": supplier.id if supplier else None,
                    "supplier_name": supplier.name if supplier else None,
                    "lead_time_days": lead_time,
                    "reliability_score": supplier_reliability,
                },
                "data_provenance": {
                    "source": "DATABASE_INVENTORY_TABLE",
                    "is_synthetic": False,
                    "data_freshness_seconds": freshness_seconds,
                    "evaluated_at": now.isoformat(),
                },
                "recommendations": recommendations,
            }

    def scan_inventory_criticality(self) -> List[Dict[str, Any]]:
        """
        Scan all inventory SKUs in the database and rank by criticality index descending.
        """
        with self.db.session() as session:
            all_items = InventoryCRUD.list_low_stock(session)
            # Also fetch other items if total count is small
            stmt = session.query(Inventory.sku).all()
            skus = [row[0] for row in stmt]

        results = [self.assess_sku_criticality(sku) for sku in skus]
        results.sort(key=lambda x: x["criticality_score"], reverse=True)
        return results
