"""
AWARE-AI — Unified Backend Service Integration Layer

Connects backend intelligence modules, ML pipelines, and multi-agent systems
directly to the SQLite persistence layer with robust validation and transactional safety.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.connection import DatabaseManager, get_session
from database.crud import (
    AgentExecutionCRUD,
    ApprovalHistoryCRUD,
    InventoryCRUD,
    MitigationCRUD,
    MLPredictionCRUD,
    PortCRUD,
    ResiliencePlanCRUD,
    RiskCRUD,
    RootCauseCRUD,
    ShipmentCRUD,
    SupplierCRUD,
    WeatherCRUD,
)
from database.models import (
    AgentExecution,
    AgentTaskStatus,
    ApprovalAction,
    Inventory,
    MitigationRecommendation,
    MLPrediction,
    PlanStatus,
    Port,
    PriorityLevel,
    ResiliencePlan,
    RiskAssessment,
    RiskLevel,
    RootCause,
    Shipment,
    ShipmentStatus,
    Supplier,
    WeatherEvidence,
    WeatherSeverity,
)


class BackendIntegrationService:
    """
    Unified backend service orchestrating storage and relational integration across:
    - Shipments & Shipment History
    - Weather Evidence
    - Suppliers & Inventory
    - Risk Assessments & Root Cause Analysis
    - Mitigation Recommendations & Resilience Plans
    - ML Predictions & Agent Executions
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    # ── Shipments & Tracking Integration ────────────────────────
    def register_shipment(
        self,
        tracking_id: str,
        origin_port_id: int,
        destination_port_id: int,
        supplier_id: Optional[int] = None,
        cargo_description: Optional[str] = None,
        weight_kg: Optional[float] = None,
        priority: str = "medium",
        created_by: str = "system",
    ) -> Shipment:
        with self.db.session() as session:
            return ShipmentCRUD.create(
                session,
                tracking_id=tracking_id,
                origin_port_id=origin_port_id,
                destination_port_id=destination_port_id,
                supplier_id=supplier_id,
                cargo_description=cargo_description,
                weight_kg=weight_kg,
                priority=priority,
                changed_by=created_by,
            )

    def transition_shipment_status(
        self,
        shipment_id: int,
        new_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
    ) -> Optional[Shipment]:
        with self.db.session() as session:
            return ShipmentCRUD.update_status(
                session,
                shipment_id=shipment_id,
                new_status=new_status,
                changed_by=changed_by,
                reason=reason,
            )

    def attach_weather_to_shipment(
        self,
        shipment_id: int,
        port_id: int,
        event_type: str,
        severity: str,
        start_time: datetime,
        description: Optional[str] = None,
        wind_speed_kmh: Optional[float] = None,
        temperature_celsius: Optional[float] = None,
        precipitation_mm: Optional[float] = None,
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> WeatherEvidence:
        with self.db.session() as session:
            return WeatherCRUD.create(
                session,
                port_id=port_id,
                shipment_id=shipment_id,
                event_type=event_type,
                severity=severity,
                start_time=start_time,
                description=description,
                wind_speed_kmh=wind_speed_kmh,
                temperature_celsius=temperature_celsius,
                precipitation_mm=precipitation_mm,
                raw_data_json=json.dumps(raw_data) if raw_data else None,
            )

    # ── Risk Assessment & Resilience Pipeline ───────────────────
    def record_risk_incident(
        self,
        entity_type: str,
        entity_id: int,
        risk_category: str,
        likelihood: float,
        impact: float,
        description: Optional[str] = None,
        assessed_by: str = "risk_engine",
        root_causes: Optional[List[Dict[str, Any]]] = None,
        mitigations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Record a comprehensive risk incident with associated root causes and mitigation recommendations.
        """
        with self.db.session() as session:
            risk = RiskCRUD.create(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                risk_category=risk_category,
                likelihood=likelihood,
                impact=impact,
                description=description,
                assessed_by=assessed_by,
            )

            created_causes = []
            if root_causes:
                for rc_data in root_causes:
                    rc = RootCauseCRUD.create(
                        session,
                        risk_assessment_id=risk.id,
                        cause_category=rc_data.get("cause_category", risk_category),
                        description=rc_data.get("description", ""),
                        contributing_factors_json=json.dumps(rc_data.get("contributing_factors", [])),
                        identified_by=assessed_by,
                    )
                    created_causes.append(rc)

            created_mitigations = []
            if mitigations:
                for mit_data in mitigations:
                    root_cause_id = mit_data.get("root_cause_id")
                    if not root_cause_id and created_causes:
                        root_cause_id = created_causes[0].id

                    mit = MitigationCRUD.create(
                        session,
                        risk_assessment_id=risk.id,
                        root_cause_id=root_cause_id,
                        recommendation=mit_data.get("recommendation", ""),
                        priority=mit_data.get("priority", PriorityLevel.MEDIUM),
                        estimated_cost=mit_data.get("estimated_cost"),
                        estimated_time_days=mit_data.get("estimated_time_days"),
                        recommended_by=assessed_by,
                    )
                    created_mitigations.append(mit)

            return {
                "risk": risk,
                "root_causes": created_causes,
                "mitigations": created_mitigations,
            }

    def create_resilience_playbook(
        self,
        name: str,
        risk_category: str,
        strategies: List[str],
        risk_assessment_id: Optional[int] = None,
        mitigation_id: Optional[int] = None,
        root_cause_id: Optional[int] = None,
        trigger_conditions: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
    ) -> ResiliencePlan:
        with self.db.session() as session:
            return ResiliencePlanCRUD.create(
                session,
                name=name,
                risk_category=risk_category,
                strategies_json=json.dumps(strategies),
                risk_assessment_id=risk_assessment_id,
                mitigation_id=mitigation_id,
                root_cause_id=root_cause_id,
                trigger_conditions_json=json.dumps(trigger_conditions) if trigger_conditions else None,
                owner=owner,
            )

    # ── ML Predictions & Agent Executions ───────────────────────
    def log_ml_prediction(
        self,
        model_name: str,
        model_version: str,
        prediction_type: str,
        predicted_value: float,
        confidence: Optional[float] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        features: Optional[Dict[str, Any]] = None,
        shap_values: Optional[Dict[str, Any]] = None,
    ) -> MLPrediction:
        with self.db.session() as session:
            return MLPredictionCRUD.create(
                session,
                model_name=model_name,
                model_version=model_version,
                prediction_type=prediction_type,
                predicted_value=predicted_value,
                confidence=confidence,
                entity_type=entity_type,
                entity_id=entity_id,
                features_json=json.dumps(features) if features else None,
                shap_values_json=json.dumps(shap_values) if shap_values else None,
            )

    def log_agent_lifecycle(
        self,
        agent_name: str,
        task_type: str,
        input_data: Any,
        output_data: Optional[Any] = None,
        error_message: Optional[str] = None,
    ) -> AgentExecution:
        with self.db.session() as session:
            exec_record = AgentExecutionCRUD.create(
                session,
                agent_name=agent_name,
                task_type=task_type,
                input_summary=json.dumps(input_data) if isinstance(input_data, (dict, list)) else str(input_data),
            )
            return AgentExecutionCRUD.complete(
                session,
                execution_id=exec_record.id,
                output_summary=json.dumps(output_data) if isinstance(output_data, (dict, list)) else (str(output_data) if output_data else None),
                error_message=error_message,
            )
