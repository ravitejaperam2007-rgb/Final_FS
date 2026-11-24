"""
AWARE-AI — Supplier Intelligence Module

Provides supplier profiling, multi-attribute analytics, and alternative supplier discovery.
Integrates directly with the SQLite database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import SupplierCRUD
from database.models import Supplier
from modules.supplier.scoring import SupplierScorer
from utils.logger import get_logger

logger = get_logger("supplier.intelligence")


class SupplierIntelligence:
    """
    Supplier Intelligence engine orchestrating supplier risk evaluation,
    lead-time performance, and dual-sourcing recommendations.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.scorer = SupplierScorer(db_manager)

    def profile_supplier(self, supplier_id: int) -> Dict[str, Any]:
        """
        Build an exhaustive supplier profile including reliability score,
        risk classification, and operational insights.
        """
        score_data = self.scorer.compute_score(supplier_id)
        with self.db.session() as session:
            supplier = SupplierCRUD.get(session, supplier_id)
            if not supplier:
                raise ValueError(f"Supplier with ID {supplier_id} not found.")

            return {
                "supplier_id": supplier.id,
                "name": supplier.name,
                "country": supplier.country,
                "region": supplier.region,
                "contact_email": supplier.contact_email,
                "category": supplier.category,
                "reliability_score": score_data["reliability_score"],
                "risk_tier": score_data["risk_tier"],
                "lead_time_days": supplier.lead_time_days,
                "data_provenance": score_data["data_provenance"],
                "metrics": score_data["metrics"],
                "insights": score_data["insights"],
            }

    def find_alternatives(
        self,
        supplier_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Identify alternative suppliers in the database matching category or regional profile
        with superior or acceptable reliability metrics.
        """
        with self.db.session() as session:
            target = SupplierCRUD.get(session, supplier_id)
            if not target:
                raise ValueError(f"Supplier with ID {supplier_id} not found.")

            # Look up other active suppliers
            all_suppliers = SupplierCRUD.list_all(session, active_only=True)
            alternatives = []

            for s in all_suppliers:
                if s.id == target.id:
                    continue
                # Preference for same category or same region
                category_match = bool(target.category and s.category == target.category)
                region_match = bool(target.region and s.region == target.region)

                score_eval = self.scorer.compute_score(s.id)
                alternatives.append({
                    "supplier_id": s.id,
                    "name": s.name,
                    "country": s.country,
                    "category": s.category,
                    "reliability_score": score_eval["reliability_score"],
                    "risk_tier": score_eval["risk_tier"],
                    "lead_time_days": s.lead_time_days,
                    "category_match": category_match,
                    "region_match": region_match,
                })

            # Sort by reliability score descending, then lead time ascending
            alternatives.sort(
                key=lambda x: (x["category_match"], x["reliability_score"], -x["lead_time_days"]),
                reverse=True,
            )
            return alternatives[:limit]
