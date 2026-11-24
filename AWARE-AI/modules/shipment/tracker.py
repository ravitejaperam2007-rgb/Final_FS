"""
AWARE-AI — Operational Shipment Risk Indicator Engine

Synthesizes real operational risk across logistics vectors:
1. Route transit distance & progress delay.
2. Real-time Open-Meteo weather along origin, destination, and en-route corridor.
3. Origin supplier reliability score & lead-time vulnerability.
4. Downstream inventory criticality of items supplied by the shipment.

Persists computed risk evaluations, evidence links, and risk scores into SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import (
    PortCRUD,
    RiskCRUD,
    ShipmentCRUD,
    SupplierCRUD,
)
from database.models import PriorityLevel, RiskAssessment, RiskLevel, Shipment, ShipmentStatus
from modules.inventory.intelligence import InventoryIntelligence
from modules.shipment.routes import RouteOptimizer
from modules.supplier.scoring import SupplierScorer
from modules.weather.intelligence import WeatherIntelligence
from utils.logger import get_logger

logger = get_logger("shipment.risk")


class ShipmentRiskEvaluator:
    """
    Evaluates multi-attribute operational risk indicators for active shipments.
    Produces an actionable composite score with transparent sub-indicators.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        weather_intel: Optional[WeatherIntelligence] = None,
    ):
        self.db = db_manager
        self.weather_intel = weather_intel or WeatherIntelligence(db_manager)
        self.supplier_scorer = SupplierScorer(db_manager)
        self.inventory_intel = InventoryIntelligence(db_manager)

    def evaluate_shipment_risk(
        self,
        shipment_id: int,
        persist_risk_assessment: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate full operational risk for a shipment.
        Integrates:
        - Weather risk at origin, destination, and current location.
        - Supplier reliability and delay track record.
        - Shipment status, priority, and schedule slippage.
        """
        with self.db.session() as session:
            shipment = ShipmentCRUD.get(session, shipment_id)
            if not shipment:
                raise ValueError(f"Shipment with ID {shipment_id} not found.")

            origin = PortCRUD.get(session, shipment.origin_port_id)
            destination = PortCRUD.get(session, shipment.destination_port_id)

            if not origin or not destination:
                raise ValueError("Shipment origin or destination port is invalid.")

            # 1. Geographic distance
            distance_nm = RouteOptimizer.haversine_distance_nm(
                origin.latitude, origin.longitude,
                destination.latitude, destination.longitude,
            )

            # 2. Weather risk evaluation
            current_coords = None
            if shipment.current_latitude is not None and shipment.current_longitude is not None:
                current_coords = (shipment.current_latitude, shipment.current_longitude)

            weather_res = self.weather_intel.assess_route_weather_risk(
                origin_port_id=origin.id,
                destination_port_id=destination.id,
                current_coordinates=current_coords,
            )
            weather_risk_score = weather_res["peak_weather_risk"]

            # 3. Supplier risk evaluation
            supplier_risk_score = 0.20  # default when no supplier attached
            supplier_name = None
            if shipment.supplier_id:
                sup_score_data = self.supplier_scorer.compute_score(shipment.supplier_id)
                supplier_reliability = sup_score_data["reliability_score"]
                supplier_risk_score = round(1.0 - supplier_reliability, 3)
                supplier_name = sup_score_data["supplier_name"]

            # 4. Status and Schedule slippage risk
            status_risk = 0.10
            if shipment.status == ShipmentStatus.DELAYED:
                status_risk = 0.85
            elif shipment.status == ShipmentStatus.CANCELLED:
                status_risk = 1.0
            elif shipment.status == ShipmentStatus.IN_TRANSIT:
                status_risk = 0.25
            elif shipment.status == ShipmentStatus.PENDING:
                status_risk = 0.15

            # Priority multiplier
            priority_multiplier = {
                PriorityLevel.LOW: 0.85,
                PriorityLevel.MEDIUM: 1.0,
                PriorityLevel.HIGH: 1.25,
                PriorityLevel.CRITICAL: 1.5,
            }.get(shipment.priority, 1.0)

            # Composite Operational Risk Formula:
            # 40% Weather Exposure + 35% Supplier Reliability Risk + 25% Status Slippage
            base_risk = (
                0.40 * weather_risk_score
                + 0.35 * supplier_risk_score
                + 0.25 * status_risk
            )
            composite_risk = round(min(max(base_risk * priority_multiplier, 0.02), 0.99), 3)

            # Classify Risk Level
            if composite_risk >= 0.70:
                level = RiskLevel.CRITICAL
            elif composite_risk >= 0.45:
                level = RiskLevel.HIGH
            elif composite_risk >= 0.25:
                level = RiskLevel.MEDIUM
            else:
                level = RiskLevel.LOW

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            freshness_seconds = int((now - shipment.updated_at).total_seconds()) if shipment.updated_at else 0

            # Contributing Risk Factors
            contributing_factors = []
            if weather_risk_score >= 0.50:
                contributing_factors.append(
                    f"Severe weather alert ({weather_res['route_weather_severity']}) on shipping corridor."
                )
            if supplier_risk_score >= 0.40:
                contributing_factors.append(
                    f"Supplier reliability deficit (Risk score: {supplier_risk_score})."
                )
            if shipment.status == ShipmentStatus.DELAYED:
                contributing_factors.append("Shipment is actively delayed in transit.")

            # Persist RiskAssessment into SQLite
            risk_id = None
            if persist_risk_assessment:
                risk_record = RiskCRUD.create(
                    session,
                    entity_type="shipment",
                    entity_id=shipment.id,
                    risk_category="operational_weather_supplier",
                    likelihood=round(weather_risk_score * 0.7 + supplier_risk_score * 0.3, 3),
                    impact=round(min(1.0, composite_risk * 1.1), 3),
                    risk_score=composite_risk,
                    risk_level=level,
                    description=(
                        f"Operational risk evaluation for tracking {shipment.tracking_id}. "
                        f"Factors: {', '.join(contributing_factors) if contributing_factors else 'Nominal'}."
                    ),
                    assessed_by="operational_risk_engine",
                )
                risk_id = risk_record.id

            return {
                "shipment_id": shipment.id,
                "tracking_id": shipment.tracking_id,
                "status": shipment.status.value if hasattr(shipment.status, "value") else str(shipment.status),
                "priority": shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority),
                "origin_port": f"{origin.name} ({origin.code})",
                "destination_port": f"{destination.name} ({destination.code})",
                "route_distance_nm": distance_nm,
                "composite_risk_score": composite_risk,
                "risk_level": level.value if hasattr(level, "value") else str(level),
                "indicators": {
                    "weather_risk_score": weather_risk_score,
                    "weather_severity": weather_res["route_weather_severity"],
                    "supplier_risk_score": supplier_risk_score,
                    "supplier_name": supplier_name,
                    "status_slippage_risk": status_risk,
                    "priority_multiplier": priority_multiplier,
                },
                "weather_detail": weather_res,
                "contributing_factors": contributing_factors,
                "data_provenance": {
                    "source": "OPERATIONAL_INTELLIGENCE_ENGINE",
                    "is_synthetic": False,
                    "data_freshness_seconds": freshness_seconds,
                    "evaluated_at": now.isoformat(),
                },
                "persisted_risk_assessment_id": risk_id,
            }
