"""
Unit tests for Inventory Criticality and Optimization Engine.
"""

import pytest

from database.crud import InventoryCRUD, SupplierCRUD
from modules.inventory.intelligence import InventoryIntelligence
from modules.inventory.optimizer import InventoryOptimizer


class TestInventoryOptimizerMath:
    def test_reorder_point_calculation(self):
        rop = InventoryOptimizer.calculate_reorder_point(
            average_daily_demand=50.0,
            lead_time_days=10,
            safety_stock=200,
        )
        assert rop == 700  # (50 * 10) + 200

    def test_safety_stock_calculation(self):
        safety = InventoryOptimizer.calculate_safety_stock(
            max_daily_demand=80.0,
            avg_daily_demand=50.0,
            max_lead_time_days=15,
            avg_lead_time_days=10,
        )
        assert safety == 700  # (80 * 15) - (50 * 10) = 1200 - 500 = 700

    def test_eoq_calculation(self):
        eoq = InventoryOptimizer.economic_order_quantity(
            annual_demand=10000,
            order_cost=50.0,
            holding_cost_per_unit_year=4.0,
        )
        assert eoq == 500  # sqrt((2 * 10000 * 50) / 4) = sqrt(250000) = 500


class TestInventoryIntelligence:
    def test_stockout_condition_yields_critical_urgency(self, db):
        with db.session() as s:
            sup = SupplierCRUD.create(s, name="Chipmaker", country="USA", reliability_score=0.90)
            item = InventoryCRUD.create(
                s, sku="CHIP-ZERO", product_name="Critical CPU",
                supplier_id=sup.id, quantity_on_hand=0, reorder_point=100, safety_stock=50,
            )

        intel = InventoryIntelligence(db)
        eval_data = intel.assess_sku_criticality("CHIP-ZERO")

        assert eval_data["inventory_status"] == "STOCKOUT"
        assert eval_data["stockout_risk"] == 1.0
        assert eval_data["urgency_tier"] == "critical"
        assert len(eval_data["recommendations"]) > 0

    def test_healthy_inventory_low_criticality(self, db):
        with db.session() as s:
            sup = SupplierCRUD.create(s, name="Resistor Co", country="Japan", reliability_score=0.98)
            item = InventoryCRUD.create(
                s, sku="RES-OK", product_name="1k Resistor",
                supplier_id=sup.id, quantity_on_hand=5000, reorder_point=500, safety_stock=200,
                unit_cost=0.05,
            )

        intel = InventoryIntelligence(db)
        eval_data = intel.assess_sku_criticality("RES-OK")

        assert eval_data["inventory_status"] == "HEALTHY"
        assert eval_data["urgency_tier"] == "low"
        assert eval_data["criticality_score"] < 0.30

    def test_scan_inventory_ranks_by_criticality(self, db):
        with db.session() as s:
            InventoryCRUD.create(s, sku="ITEM-CRIT", product_name="Rare Element", quantity_on_hand=2, reorder_point=50, safety_stock=20)
            InventoryCRUD.create(s, sku="ITEM-OK", product_name="Common Screw", quantity_on_hand=2000, reorder_point=100, safety_stock=50)

        intel = InventoryIntelligence(db)
        ranked = intel.scan_inventory_criticality()

        assert len(ranked) == 2
        assert ranked[0]["sku"] == "ITEM-CRIT"
        assert ranked[0]["criticality_score"] > ranked[1]["criticality_score"]
