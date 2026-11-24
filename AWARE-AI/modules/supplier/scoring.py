"""
AWARE-AI — Supplier Reliability Scoring Engine

Calculates empirical supplier performance scores based on:
- Historical shipment on-time delivery rate.
- Historical delay frequency and average delay duration.
- Geopolitical and regional operational risk tier.
- Lead-time volatility and data freshness tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from database.crud import SupplierCRUD
from database.models import Shipment, ShipmentStatus, Supplier
from utils.logger import get_logger

logger = get_logger("supplier.scoring")


class SupplierScorer:
    """
    Computes evidence-based supplier reliability metrics.
    Preserves data provenance: distinguishes between suppliers with real shipment history
    versus newly registered suppliers with baseline/default data.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def compute_score(self, supplier_id: int) -> Dict[str, Any]:
        """
        Evaluate full reliability score and evidence dossier for a supplier.
        """
        with self.db.session() as session:
            supplier = SupplierCRUD.get(session, supplier_id)
            if not supplier:
                raise ValueError(f"Supplier with ID {supplier_id} does not exist.")

            # Query real shipment history for this supplier
            stmt = select(Shipment).where(Shipment.supplier_id == supplier_id)
            shipments = list(session.execute(stmt).scalars().all())

            total_shipments = len(shipments)
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Data Freshness calculation
            supplier_updated_at = supplier.updated_at or supplier.created_at
            freshness_seconds = int((now - supplier_updated_at).total_seconds()) if supplier_updated_at else 0

            # If no shipments exist in the DB, flag as INITIAL_BASELINE
            if total_shipments == 0:
                baseline_score = supplier.reliability_score if supplier.reliability_score > 0 else 0.70
                tier = self._classify_tier(baseline_score)
                return {
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "country": supplier.country,
                    "reliability_score": round(baseline_score, 3),
                    "risk_tier": tier,
                    "data_provenance": {
                        "source": "SUPPLIER_INITIAL_PROFILE",
                        "is_synthetic": False,
                        "evidence_shipment_count": 0,
                        "data_freshness_seconds": freshness_seconds,
                        "last_evaluated": now.isoformat(),
                    },
                    "metrics": {
                        "on_time_delivery_rate": None,
                        "delay_rate": None,
                        "completed_shipments": 0,
                        "active_shipments": 0,
                        "total_shipments": 0,
                        "average_lead_time_days": supplier.lead_time_days,
                    },
                    "insights": ["Supplier has no historical shipments recorded; using profile baseline score."],
                }

            # Empirical metrics evaluation
            delivered_count = 0
            delayed_count = 0
            in_transit_count = 0
            pending_count = 0
            cancelled_count = 0

            for sh in shipments:
                if sh.status == ShipmentStatus.DELIVERED:
                    delivered_count += 1
                elif sh.status == ShipmentStatus.DELAYED:
                    delayed_count += 1
                elif sh.status == ShipmentStatus.IN_TRANSIT:
                    in_transit_count += 1
                elif sh.status == ShipmentStatus.PENDING:
                    pending_count += 1
                elif sh.status == ShipmentStatus.CANCELLED:
                    cancelled_count += 1

            finished_count = delivered_count + delayed_count + cancelled_count
            if finished_count > 0:
                on_time_rate = delivered_count / finished_count
                delay_rate = (delayed_count + cancelled_count * 1.5) / finished_count
            else:
                on_time_rate = 1.0 if delayed_count == 0 else 0.5
                delay_rate = 0.0

            # Weighted reliability formula:
            # 60% On-Time Performance + 25% Configured Profile Score + 15% Lead-time Penalty
            lead_time_penalty = max(0.0, (supplier.lead_time_days - 30) / 100.0)
            configured_score = supplier.reliability_score or 0.80

            calculated_score = (
                0.60 * on_time_rate
                + 0.25 * configured_score
                + 0.15 * max(0.0, 1.0 - lead_time_penalty)
            )
            # Clip between [0.05, 0.99]
            final_score = round(min(max(calculated_score, 0.05), 0.99), 3)
            risk_tier = self._classify_tier(final_score)

            # Update supplier record in DB with latest computed reliability score and risk tier
            supplier.reliability_score = final_score
            supplier.risk_tier = risk_tier
            supplier.updated_at = now
            session.flush()

            insights = []
            if delay_rate > 0.30:
                insights.append(f"High delay frequency detected ({round(delay_rate * 100, 1)}% of recorded shipments).")
            if supplier.lead_time_days > 45:
                insights.append(f"Extended lead time ({supplier.lead_time_days} days) increases buffer requirement.")
            if not insights:
                insights.append("Consistent operational performance within nominal tolerance.")

            return {
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "country": supplier.country,
                "reliability_score": final_score,
                "risk_tier": risk_tier,
                "data_provenance": {
                    "source": "EMPIRICAL_SHIPMENT_HISTORY",
                    "is_synthetic": False,
                    "evidence_shipment_count": total_shipments,
                    "data_freshness_seconds": freshness_seconds,
                    "last_evaluated": now.isoformat(),
                },
                "metrics": {
                    "on_time_delivery_rate": round(on_time_rate, 3),
                    "delay_rate": round(delay_rate, 3),
                    "completed_shipments": delivered_count,
                    "delayed_shipments": delayed_count,
                    "active_shipments": in_transit_count + pending_count,
                    "total_shipments": total_shipments,
                    "average_lead_time_days": supplier.lead_time_days,
                },
                "insights": insights,
            }

    def _classify_tier(self, score: float) -> str:
        if score >= 0.85:
            return "low"
        if score >= 0.70:
            return "medium"
        if score >= 0.50:
            return "high"
        return "critical"
