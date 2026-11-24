"""
AWARE-AI — Autonomous Resilience Planning Engine

Responsibilities:
- Synthesizes targeted recovery plans based on root-cause diagnosis.
- Evaluates alternative maritime routes, emergency inventory splits, and vendor activations.
- Compares recovery plans side-by-side on: transit time, cost, weather exposure, operational feasibility, and risk reduction.
- Generates clear audit-ready reasoning explaining why a specific plan is recommended.
- Enforces strict DRAFT status pending human approval.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import (
    MitigationCRUD,
    ResiliencePlanCRUD,
    RiskCRUD,
    RootCauseCRUD,
    ShipmentCRUD,
    SupplierCRUD,
)
from database.models import PlanStatus, PriorityLevel, ResiliencePlan, RiskLevel, Shipment
from modules.resilience.impact_engine import BusinessImpactAssessmentEngine
from modules.resilience.maritime_routes import MaritimeRouteEvaluator
from utils.logger import get_logger

logger = get_logger("resilience.planner")


class AutonomousResiliencePlanner:
    """
    Core resilience planning engine generating, comparing, and recommending
    operational contingency playbooks.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        route_evaluator: Optional[MaritimeRouteEvaluator] = None,
        impact_engine: Optional[BusinessImpactAssessmentEngine] = None,
    ):
        self.db = db_manager
        self.route_evaluator = route_evaluator or MaritimeRouteEvaluator(db_manager)
        self.impact_engine = impact_engine or BusinessImpactAssessmentEngine(db_manager)

    def generate_and_compare_plans(
        self,
        shipment_id: int,
        risk_profile: Dict[str, Any],
        persist_plans: bool = True,
    ) -> Dict[str, Any]:
        """
        Generates alternative recovery plans, evaluates tradeoffs across cost/time/weather/feasibility,
        quantifies risk reduction, selects the optimal plan, and provides reasoning.
        """
        with self.db.session() as session:
            shipment = ShipmentCRUD.get(session, shipment_id)
            if not shipment:
                raise ValueError(f"Shipment {shipment_id} does not exist.")

            origin_port_id = shipment.origin_port_id
            dest_port_id = shipment.destination_port_id

            # 1. Evaluate Maritime Routes
            routes = self.route_evaluator.evaluate_primary_and_alternative_routes(
                origin_port_id=origin_port_id,
                destination_port_id=dest_port_id,
            )

            # 2. Evaluate Business Impact
            delay_prob = risk_profile.get("ml_delay_probability", 0.50)
            weather_sev = risk_profile.get("weather_severity", "minor")
            impact_analysis = self.impact_engine.evaluate_shipment_business_impact(
                shipment_id=shipment_id,
                predicted_delay_prob=delay_prob,
                weather_severity=weather_sev,
            )
            exposure_usd = impact_analysis["financial_exposure"]["total_exposure_usd"]
            initial_composite_risk = risk_profile.get("composite_risk_score", 0.60)

            # 3. Formulate Candidate Plans
            candidate_plans: List[Dict[str, Any]] = []

            # Plan A: Maritime Corridor Deviation (avoiding storms)
            best_diversion_route = None
            for r in routes:
                if r["route_type"] == "DIVERSION" and r["operational_feasibility"] in ("HIGH", "CAUTION"):
                    best_diversion_route = r
                    break
            if not best_diversion_route and len(routes) > 1:
                best_diversion_route = routes[1]
            elif not best_diversion_route:
                best_diversion_route = routes[0]

            direct_route = routes[0]

            # Plan 1: Weather-Routing Deviation
            reroute_cost = round(best_diversion_route["estimated_fuel_cost_usd"] - direct_route["estimated_fuel_cost_usd"] + 4500.0, 2)
            reroute_transit_days = best_diversion_route["transit_time_days"]
            weather_risk_after = best_diversion_route["weather_risk_score"]
            risk_red_p1 = round(max(0.10, initial_composite_risk * 0.45), 3)

            plan_1 = {
                "plan_key": "PLAN_DYNAMIC_REROUTE",
                "name": f"Maritime Corridor Deviation ({best_diversion_route['route_name']})",
                "risk_category": "weather",
                "strategies": ["dynamic_rerouting", "contingency_bunker_allocation", "port_priority_berthing"],
                "selected_route": best_diversion_route,
                "transit_time_days": reroute_transit_days,
                "implementation_cost_usd": max(1500.0, reroute_cost),
                "weather_risk_score": weather_risk_after,
                "operational_feasibility": best_diversion_route["operational_feasibility"],
                "estimated_risk_reduction": risk_red_p1,
                "projected_residual_risk": round(max(0.05, initial_composite_risk - risk_red_p1), 3),
                "avoids_financial_exposure_usd": round(exposure_usd * 0.70, 2),
                "trigger_conditions": {
                    "corridor_wind_speed_kmh_threshold": 75.0,
                    "weather_severity_alert": "severe",
                },
            }
            candidate_plans.append(plan_1)

            # Plan 2: Multi-Modal Express Freight Split (Air/Land Priority Dispatch)
            split_cost = round(22000.0 + (shipment.weight_kg or 5000.0) * 0.85, 2)
            risk_red_p2 = round(max(0.15, initial_composite_risk * 0.65), 3)
            plan_2 = {
                "plan_key": "PLAN_MULTIMODAL_SPLIT",
                "name": "Expedited Multi-Modal Air/Express Cargo Split",
                "risk_category": "operational",
                "strategies": ["air_freight_safety_split", "customs_pre_clearance", "direct_hub_injection"],
                "selected_route": direct_route,
                "transit_time_days": round(direct_route["transit_time_days"] * 0.4, 1),
                "implementation_cost_usd": split_cost,
                "weather_risk_score": round(direct_route["weather_risk_score"] * 0.3, 3),
                "operational_feasibility": "HIGH",
                "estimated_risk_reduction": risk_red_p2,
                "projected_residual_risk": round(max(0.05, initial_composite_risk - risk_red_p2), 3),
                "avoids_financial_exposure_usd": round(exposure_usd * 0.90, 2),
                "trigger_conditions": {
                    "predicted_delay_days_threshold": 4.0,
                    "line_stoppage_threat": True,
                },
            }
            candidate_plans.append(plan_2)

            # Plan 3: Dual-Sourcing & Downstream Buffer Safety Allocation
            buffer_cost = 9500.0
            risk_red_p3 = round(max(0.10, initial_composite_risk * 0.40), 3)
            plan_3 = {
                "plan_key": "PLAN_BUFFER_STOCK_AND_VENDOR",
                "name": "Downstream Buffer Reallocation & Dual-Vendor Sourcing",
                "risk_category": "supplier",
                "strategies": ["safety_stock_reallocation", "dual_vendor_activation", "expedited_batch_lot"],
                "selected_route": direct_route,
                "transit_time_days": direct_route["transit_time_days"],
                "implementation_cost_usd": buffer_cost,
                "weather_risk_score": direct_route["weather_risk_score"],
                "operational_feasibility": "HIGH",
                "estimated_risk_reduction": risk_red_p3,
                "projected_residual_risk": round(max(0.05, initial_composite_risk - risk_red_p3), 3),
                "avoids_financial_exposure_usd": round(exposure_usd * 0.55, 2),
                "trigger_conditions": {
                    "supplier_reliability_threshold": 0.65,
                    "inventory_safety_deficit": True,
                },
            }
            candidate_plans.append(plan_3)

            # 4. Compare Plans and Score Recommendation
            # Utility Formula: Maximize (Risk Reduction × 0.40 + Net Savings × 0.35 + Feasibility × 0.25)
            best_plan = None
            highest_score = -1.0
            feasibility_weights = {"HIGH": 1.0, "CAUTION": 0.65, "LOW_EFFICIENCY": 0.40, "RESTRICTED": 0.10}

            for p in candidate_plans:
                net_savings = max(0.0, p["avoids_financial_exposure_usd"] - p["implementation_cost_usd"])
                savings_score = min(1.0, net_savings / max(1.0, exposure_usd))
                feas_score = feasibility_weights.get(p["operational_feasibility"], 0.5)

                plan_utility = (
                    0.40 * p["estimated_risk_reduction"]
                    + 0.35 * savings_score
                    + 0.25 * feas_score
                )
                p["recommendation_score"] = round(plan_utility, 3)

                if plan_utility > highest_score:
                    highest_score = plan_utility
                    best_plan = p

            # 5. Formulate Recommendation Reasoning
            reasoning = self._generate_recommendation_reasoning(
                best_plan=best_plan,
                initial_risk=initial_composite_risk,
                impact_analysis=impact_analysis,
            )

            # 6. Database Persistence (Strict DRAFT status awaiting human approval)
            persisted_plan_id = None
            if persist_plans and best_plan:
                risk_assessment_id = risk_profile.get("persisted_risk_assessment_id")
                plan_record = ResiliencePlanCRUD.create(
                    session,
                    name=best_plan["name"],
                    description=(
                        f"Recommended operational recovery playbook for tracking #{shipment.tracking_id}. "
                        f"Reasoning: {reasoning}"
                    ),
                    risk_category=best_plan["risk_category"],
                    trigger_conditions_json=json.dumps(best_plan["trigger_conditions"]),
                    strategies_json=json.dumps(best_plan["strategies"]),
                    status=PlanStatus.DRAFT,  # Stays draft until Human approval
                    owner="AWARE-AI Resilience Engine",
                    risk_assessment_id=risk_assessment_id,
                )
                persisted_plan_id = plan_record.id

            return {
                "shipment_id": shipment.id,
                "tracking_id": shipment.tracking_id,
                "initial_composite_risk": initial_composite_risk,
                "financial_exposure_usd": exposure_usd,
                "candidate_plans": candidate_plans,
                "recommended_plan": best_plan,
                "recommendation_reasoning": reasoning,
                "requires_human_approval": True,
                "persisted_resilience_plan_id": persisted_plan_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }

    def _generate_recommendation_reasoning(
        self,
        best_plan: Dict[str, Any],
        initial_risk: float,
        impact_analysis: Dict[str, Any],
    ) -> str:
        """
        Generates an auditable plain-language explanation of the decision rationale.
        """
        exposure = impact_analysis["financial_exposure"]["total_exposure_usd"]
        plan_name = best_plan["name"]
        cost = best_plan["implementation_cost_usd"]
        risk_red = best_plan["estimated_risk_reduction"]
        feasibility = best_plan["operational_feasibility"]

        reasons = [
            f"Plan '{plan_name}' delivers the highest multi-objective utility score ({best_plan['recommendation_score']}).",
            f"Achieves {round(risk_red * 100, 1)}% absolute risk reduction, driving composite risk down to {best_plan['projected_residual_risk']}.",
            f"Mitigates up to ${best_plan['avoids_financial_exposure_usd']:,.2f} in financial exposure at an estimated cost of ${cost:,.2f}.",
            f"Operational feasibility is rated {feasibility} under current maritime corridor conditions.",
        ]
        if impact_analysis["operational_impact"]["line_stoppage_risk"]:
            reasons.append("Critical priority: effectively prevents projected manufacturing line downtime.")

        return " ".join(reasons)
