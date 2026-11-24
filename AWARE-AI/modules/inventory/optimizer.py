"""
AWARE-AI — Inventory Optimization Calculus (ROP, Safety Stock, EOQ)
"""

from __future__ import annotations

import math
from typing import Optional


class InventoryOptimizer:
    """Calculate optimal inventory parameters."""

    @staticmethod
    def calculate_reorder_point(
        average_daily_demand: float,
        lead_time_days: int,
        safety_stock: int,
    ) -> int:
        """
        ROP = (Average Daily Demand × Lead Time) + Safety Stock
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
        Buffer formula: (Max Demand × Max Lead Time) - (Avg Demand × Avg Lead Time)
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
    ) -> dict[str, float | int]:
        """
        Convenience method calculating Wilson EOQ with holding cost rate.
        """
        holding_per_unit = unit_cost * holding_cost_rate
        eoq = self.economic_order_quantity(annual_demand, ordering_cost, holding_per_unit)
        return {
            "eoq_units": eoq,
            "annual_demand": annual_demand,
            "ordering_cost": ordering_cost,
            "holding_cost_per_unit": holding_per_unit,
        }

    def reorder_point(self, sku: str) -> float:
        raise NotImplementedError("Use calculate_reorder_point or InventoryIntelligence.assess_sku_criticality")

    def safety_stock(self, sku: str) -> float:
        raise NotImplementedError("Use calculate_safety_stock or InventoryIntelligence.assess_sku_criticality")
