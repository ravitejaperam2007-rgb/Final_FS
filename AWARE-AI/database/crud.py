"""
AWARE-AI — CRUD operations for all 13 database tables.

Every public function accepts a SQLAlchemy ``Session`` and returns model
instances or lists thereof.  Validation is performed before writes.

Usage::

    from database.connection import get_session, get_engine
    from database.crud import PortCRUD

    engine = get_engine()
    with get_session(engine) as session:
        port = PortCRUD.create(session, name="Shanghai", code="CNSHA",
                               country="China", latitude=31.23, longitude=121.47)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    AgentExecution,
    AgentTaskStatus,
    ApprovalHistory,
    Base,
    Inventory,
    MLPrediction,
    MitigationRecommendation,
    Port,
    ResiliencePlan,
    RiskAssessment,
    RiskLevel,
    RootCause,
    Shipment,
    ShipmentHistory,
    ShipmentStatus,
    Supplier,
    WeatherEvidence,
)
from database.validators import (
    validate_inventory_data,
    validate_ml_prediction_data,
    validate_port_data,
    validate_resilience_plan_data,
    validate_risk_data,
    validate_shipment_data,
    validate_supplier_data,
    validate_weather_data,
)

T = TypeVar("T", bound=Base)


# ── generic helpers ─────────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_by_id(session: Session, model: Type[T], record_id: int) -> T | None:
    return session.get(model, record_id)


def _get_all(
    session: Session,
    model: Type[T],
    *,
    filters: list | None = None,
    order_by: Any = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[T]:
    stmt = select(model)
    if filters:
        for f in filters:
            stmt = stmt.where(f)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars().all())


def _delete(session: Session, model: Type[T], record_id: int) -> bool:
    obj = session.get(model, record_id)
    if obj is None:
        return False
    session.delete(obj)
    session.flush()
    return True


def _count(session: Session, model: Type[T], filters: list | None = None) -> int:
    from sqlalchemy import func
    stmt = select(func.count()).select_from(model)
    if filters:
        for f in filters:
            stmt = stmt.where(f)
    return session.execute(stmt).scalar() or 0


# ============================================================
#  Port CRUD
# ============================================================
class PortCRUD:
    """CRUD operations for the ``ports`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> Port:
        validate_port_data(data)
        port = Port(**data)
        session.add(port)
        session.flush()
        return port

    @staticmethod
    def get(session: Session, port_id: int) -> Port | None:
        return _get_by_id(session, Port, port_id)

    @staticmethod
    def get_by_code(session: Session, code: str) -> Port | None:
        stmt = select(Port).where(Port.code == code)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_all(session: Session, *, country: str | None = None, active_only: bool = True) -> list[Port]:
        filters = []
        if active_only:
            filters.append(Port.is_active == True)  # noqa: E712
        if country:
            filters.append(Port.country == country)
        return _get_all(session, Port, filters=filters, order_by=Port.name)

    @staticmethod
    def update(session: Session, port_id: int, **data: Any) -> Port | None:
        port = session.get(Port, port_id)
        if port is None:
            return None
        for key, val in data.items():
            if hasattr(port, key):
                setattr(port, key, val)
        session.flush()
        return port

    @staticmethod
    def delete(session: Session, port_id: int) -> bool:
        return _delete(session, Port, port_id)


# ============================================================
#  Supplier CRUD
# ============================================================
class SupplierCRUD:
    """CRUD operations for the ``suppliers`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> Supplier:
        validate_supplier_data(data)
        supplier = Supplier(**data)
        session.add(supplier)
        session.flush()
        return supplier

    @staticmethod
    def get(session: Session, supplier_id: int) -> Supplier | None:
        return _get_by_id(session, Supplier, supplier_id)

    @staticmethod
    def list_all(
        session: Session,
        *,
        country: str | None = None,
        risk_tier: str | None = None,
        active_only: bool = True,
    ) -> list[Supplier]:
        filters = []
        if active_only:
            filters.append(Supplier.is_active == True)  # noqa: E712
        if country:
            filters.append(Supplier.country == country)
        if risk_tier:
            filters.append(Supplier.risk_tier == risk_tier)
        return _get_all(session, Supplier, filters=filters, order_by=Supplier.name)

    @staticmethod
    def update(session: Session, supplier_id: int, **data: Any) -> Supplier | None:
        supplier = session.get(Supplier, supplier_id)
        if supplier is None:
            return None
        for key, val in data.items():
            if hasattr(supplier, key):
                setattr(supplier, key, val)
        supplier.updated_at = _utcnow()
        session.flush()
        return supplier

    @staticmethod
    def delete(session: Session, supplier_id: int) -> bool:
        return _delete(session, Supplier, supplier_id)


# ============================================================
#  Shipment CRUD
# ============================================================
class ShipmentCRUD:
    """CRUD operations for the ``shipments`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> Shipment:
        changed_by = data.pop("changed_by", "system")
        change_reason = data.pop("change_reason", "Shipment created")
        validate_shipment_data(data)
        shipment = Shipment(**data)
        session.add(shipment)
        session.flush()

        # auto-create first history entry
        history = ShipmentHistory(
            shipment_id=shipment.id,
            previous_status=None,
            new_status=shipment.status or ShipmentStatus.PENDING,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        session.add(history)
        session.flush()
        return shipment

    @staticmethod
    def get(session: Session, shipment_id: int) -> Shipment | None:
        return _get_by_id(session, Shipment, shipment_id)

    @staticmethod
    def get_by_id(session: Session, shipment_id: int) -> Shipment | None:
        return _get_by_id(session, Shipment, shipment_id)

    @staticmethod
    def get_by_tracking_id(session: Session, tracking_id: str) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.tracking_id == tracking_id)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_all(
        session: Session,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Shipment]:
        filters = []
        if status:
            filters.append(Shipment.status == status)
        return _get_all(session, Shipment, filters=filters,
                        order_by=Shipment.created_at.desc(), limit=limit, offset=offset)

    @staticmethod
    def update_status(
        session: Session,
        shipment_id: int,
        new_status: str,
        *,
        changed_by: str = "system",
        reason: str | None = None,
    ) -> Shipment | None:
        """Transition a shipment to a new status and log the change."""
        shipment = session.get(Shipment, shipment_id)
        if shipment is None:
            return None
        old_status = shipment.status
        shipment.status = ShipmentStatus(new_status)
        shipment.updated_at = _utcnow()

        if new_status == "delivered":
            shipment.actual_arrival = _utcnow()

        history = ShipmentHistory(
            shipment_id=shipment.id,
            previous_status=old_status,
            new_status=ShipmentStatus(new_status),
            changed_by=changed_by,
            change_reason=reason,
        )
        session.add(history)
        session.flush()
        return shipment

    @staticmethod
    def update(session: Session, shipment_id: int, **data: Any) -> Shipment | None:
        shipment = session.get(Shipment, shipment_id)
        if shipment is None:
            return None
        changed_by = data.pop("changed_by", "system")
        change_reason = data.pop("change_reason", None)
        old_status = shipment.status
        status_changed = False

        for key, val in data.items():
            if hasattr(shipment, key):
                if key == "status":
                    new_st = ShipmentStatus(val) if isinstance(val, str) else val
                    if new_st != old_status:
                        status_changed = True
                        shipment.status = new_st
                else:
                    setattr(shipment, key, val)
        shipment.updated_at = _utcnow()

        if status_changed:
            if shipment.status == ShipmentStatus.DELIVERED and shipment.actual_arrival is None:
                shipment.actual_arrival = _utcnow()
            history = ShipmentHistory(
                shipment_id=shipment.id,
                previous_status=old_status,
                new_status=shipment.status,
                changed_by=changed_by,
                change_reason=change_reason,
            )
            session.add(history)

        session.flush()
        return shipment

    @staticmethod
    def delete(session: Session, shipment_id: int) -> bool:
        return _delete(session, Shipment, shipment_id)

    @staticmethod
    def get_history(session: Session, shipment_id: int) -> list[ShipmentHistory]:
        return _get_all(session, ShipmentHistory,
                        filters=[ShipmentHistory.shipment_id == shipment_id],
                        order_by=ShipmentHistory.timestamp)


# ============================================================
#  Weather Evidence CRUD
# ============================================================
class WeatherCRUD:
    """CRUD operations for the ``weather_evidence`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> WeatherEvidence:
        validate_weather_data(data)
        event = WeatherEvidence(**data)
        session.add(event)
        session.flush()
        return event

    @staticmethod
    def get(session: Session, weather_id: int) -> WeatherEvidence | None:
        return _get_by_id(session, WeatherEvidence, weather_id)

    @staticmethod
    def list_by_port(session: Session, port_id: int) -> list[WeatherEvidence]:
        return _get_all(session, WeatherEvidence,
                        filters=[WeatherEvidence.port_id == port_id],
                        order_by=WeatherEvidence.start_time.desc())

    @staticmethod
    def list_by_severity(session: Session, severity: str) -> list[WeatherEvidence]:
        return _get_all(session, WeatherEvidence,
                        filters=[WeatherEvidence.severity == severity],
                        order_by=WeatherEvidence.start_time.desc())

    @staticmethod
    def list_by_shipment(session: Session, shipment_id: int) -> list[WeatherEvidence]:
        return _get_all(session, WeatherEvidence,
                        filters=[WeatherEvidence.shipment_id == shipment_id],
                        order_by=WeatherEvidence.start_time.desc())

    @staticmethod
    def delete(session: Session, weather_id: int) -> bool:
        return _delete(session, WeatherEvidence, weather_id)


# ============================================================
#  Inventory CRUD
# ============================================================
class InventoryCRUD:
    """CRUD operations for the ``inventory`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> Inventory:
        validate_inventory_data(data)
        item = Inventory(**data)
        session.add(item)
        session.flush()
        return item

    @staticmethod
    def get(session: Session, inventory_id: int) -> Inventory | None:
        return _get_by_id(session, Inventory, inventory_id)

    @staticmethod
    def get_by_id(session: Session, inventory_id: int) -> Inventory | None:
        return _get_by_id(session, Inventory, inventory_id)

    @staticmethod
    def list_all(session: Session, limit: int | None = None, offset: int | None = None) -> list[Inventory]:
        return _get_all(session, Inventory, order_by=Inventory.created_at.desc(), limit=limit, offset=offset)

    @staticmethod
    def get_by_sku(session: Session, sku: str) -> Inventory | None:
        stmt = select(Inventory).where(Inventory.sku == sku)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_low_stock(session: Session) -> list[Inventory]:
        """Return items whose quantity is at or below the reorder point."""
        return _get_all(
            session, Inventory,
            filters=[Inventory.quantity_on_hand <= Inventory.reorder_point],
            order_by=Inventory.quantity_on_hand,
        )

    @staticmethod
    def update(session: Session, inventory_id: int, **data: Any) -> Inventory | None:
        item = session.get(Inventory, inventory_id)
        if item is None:
            return None
        for key, val in data.items():
            if hasattr(item, key):
                setattr(item, key, val)
        item.updated_at = _utcnow()
        session.flush()
        return item

    @staticmethod
    def adjust_quantity(session: Session, inventory_id: int, delta: int) -> Inventory | None:
        """Increase (positive) or decrease (negative) quantity on hand."""
        item = session.get(Inventory, inventory_id)
        if item is None:
            return None
        new_qty = item.quantity_on_hand + delta
        if new_qty < 0:
            raise ValueError(f"Adjustment would result in negative stock: {new_qty}")
        item.quantity_on_hand = new_qty
        item.updated_at = _utcnow()
        session.flush()
        return item

    @staticmethod
    def delete(session: Session, inventory_id: int) -> bool:
        return _delete(session, Inventory, inventory_id)


# ============================================================
#  Risk Assessment CRUD
# ============================================================
class RiskCRUD:
    """CRUD operations for the ``risk_assessments`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> RiskAssessment:
        validate_risk_data(data)
        # auto-compute risk_score if not supplied
        if "risk_score" not in data:
            data["risk_score"] = round(data["likelihood"] * data["impact"], 4)
        # auto-determine risk level
        if "risk_level" not in data:
            score = data["risk_score"]
            if score >= 0.75:
                data["risk_level"] = RiskLevel.CRITICAL
            elif score >= 0.50:
                data["risk_level"] = RiskLevel.HIGH
            elif score >= 0.25:
                data["risk_level"] = RiskLevel.MEDIUM
            else:
                data["risk_level"] = RiskLevel.LOW
        risk = RiskAssessment(**data)
        session.add(risk)
        session.flush()
        return risk

    @staticmethod
    def get(session: Session, risk_id: int) -> RiskAssessment | None:
        return _get_by_id(session, RiskAssessment, risk_id)

    @staticmethod
    def list_by_entity(session: Session, entity_type: str, entity_id: int) -> list[RiskAssessment]:
        return _get_all(
            session, RiskAssessment,
            filters=[
                RiskAssessment.entity_type == entity_type,
                RiskAssessment.entity_id == entity_id,
            ],
            order_by=RiskAssessment.assessed_at.desc(),
        )

    @staticmethod
    def list_by_level(session: Session, level: str) -> list[RiskAssessment]:
        return _get_all(session, RiskAssessment,
                        filters=[RiskAssessment.risk_level == level],
                        order_by=RiskAssessment.risk_score.desc())

    @staticmethod
    def delete(session: Session, risk_id: int) -> bool:
        return _delete(session, RiskAssessment, risk_id)

    @staticmethod
    def count(session: Session, *, level: str | None = None) -> int:
        filters = []
        if level:
            filters.append(RiskAssessment.risk_level == level)
        return _count(session, RiskAssessment, filters=filters)


# ============================================================
#  ML Prediction CRUD
# ============================================================
class MLPredictionCRUD:
    """CRUD operations for the ``ml_predictions`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> MLPrediction:
        validate_ml_prediction_data(data)
        pred = MLPrediction(**data)
        session.add(pred)
        session.flush()
        return pred

    @staticmethod
    def get(session: Session, prediction_id: int) -> MLPrediction | None:
        return _get_by_id(session, MLPrediction, prediction_id)

    @staticmethod
    def list_by_model(session: Session, model_name: str) -> list[MLPrediction]:
        return _get_all(session, MLPrediction,
                        filters=[MLPrediction.model_name == model_name],
                        order_by=MLPrediction.created_at.desc())

    @staticmethod
    def delete(session: Session, prediction_id: int) -> bool:
        return _delete(session, MLPrediction, prediction_id)


# ============================================================
#  Agent Execution CRUD
# ============================================================
class AgentExecutionCRUD:
    """CRUD operations for the ``agent_executions`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> AgentExecution:
        execution = AgentExecution(**data)
        session.add(execution)
        session.flush()
        return execution

    @staticmethod
    def get(session: Session, execution_id: int) -> AgentExecution | None:
        return _get_by_id(session, AgentExecution, execution_id)

    @staticmethod
    def complete(
        session: Session,
        execution_id: int,
        *,
        output_summary: str | None = None,
        error_message: str | None = None,
    ) -> AgentExecution | None:
        """Mark an execution as completed or failed."""
        ex = session.get(AgentExecution, execution_id)
        if ex is None:
            return None
        now = _utcnow()
        if error_message:
            ex.status = AgentTaskStatus.FAILED
            ex.error_message = error_message
        else:
            ex.status = AgentTaskStatus.COMPLETED
        ex.output_summary = output_summary
        ex.completed_at = now
        if ex.started_at:
            ex.duration_ms = int((now - ex.started_at).total_seconds() * 1000)
        session.flush()
        return ex

    @staticmethod
    def list_by_agent(session: Session, agent_name: str) -> list[AgentExecution]:
        return _get_all(session, AgentExecution,
                        filters=[AgentExecution.agent_name == agent_name],
                        order_by=AgentExecution.started_at.desc())

    @staticmethod
    def delete(session: Session, execution_id: int) -> bool:
        return _delete(session, AgentExecution, execution_id)


# ============================================================
#  Root Cause CRUD
# ============================================================
class RootCauseCRUD:
    """CRUD operations for the ``root_causes`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> RootCause:
        cause = RootCause(**data)
        session.add(cause)
        session.flush()
        return cause

    @staticmethod
    def get(session: Session, cause_id: int) -> RootCause | None:
        return _get_by_id(session, RootCause, cause_id)

    @staticmethod
    def list_by_risk(session: Session, risk_assessment_id: int) -> list[RootCause]:
        return _get_all(session, RootCause,
                        filters=[RootCause.risk_assessment_id == risk_assessment_id])

    @staticmethod
    def delete(session: Session, cause_id: int) -> bool:
        return _delete(session, RootCause, cause_id)


# ============================================================
#  Mitigation Recommendation CRUD
# ============================================================
class MitigationCRUD:
    """CRUD operations for the ``mitigation_recommendations`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> MitigationRecommendation:
        rec = MitigationRecommendation(**data)
        session.add(rec)
        session.flush()
        return rec

    @staticmethod
    def get(session: Session, rec_id: int) -> MitigationRecommendation | None:
        return _get_by_id(session, MitigationRecommendation, rec_id)

    @staticmethod
    def list_by_risk(session: Session, risk_assessment_id: int) -> list[MitigationRecommendation]:
        return _get_all(session, MitigationRecommendation,
                        filters=[MitigationRecommendation.risk_assessment_id == risk_assessment_id])

    @staticmethod
    def list_by_root_cause(session: Session, root_cause_id: int) -> list[MitigationRecommendation]:
        return _get_all(session, MitigationRecommendation,
                        filters=[MitigationRecommendation.root_cause_id == root_cause_id])

    @staticmethod
    def update_status(session: Session, rec_id: int, status: str) -> MitigationRecommendation | None:
        rec = session.get(MitigationRecommendation, rec_id)
        if rec is None:
            return None
        rec.status = status
        session.flush()
        return rec

    @staticmethod
    def delete(session: Session, rec_id: int) -> bool:
        return _delete(session, MitigationRecommendation, rec_id)


# ============================================================
#  Resilience Plan CRUD
# ============================================================
class ResiliencePlanCRUD:
    """CRUD operations for the ``resilience_plans`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> ResiliencePlan:
        validate_resilience_plan_data(data)
        plan = ResiliencePlan(**data)
        session.add(plan)
        session.flush()
        return plan

    @staticmethod
    def get(session: Session, plan_id: int) -> ResiliencePlan | None:
        return _get_by_id(session, ResiliencePlan, plan_id)

    @staticmethod
    def list_all(session: Session, *, status: str | None = None, risk_assessment_id: int | None = None) -> list[ResiliencePlan]:
        filters = []
        if status:
            filters.append(ResiliencePlan.status == status)
        if risk_assessment_id:
            filters.append(ResiliencePlan.risk_assessment_id == risk_assessment_id)
        return _get_all(session, ResiliencePlan, filters=filters, order_by=ResiliencePlan.created_at.desc())

    @staticmethod
    def update(session: Session, plan_id: int, **data: Any) -> ResiliencePlan | None:
        plan = session.get(ResiliencePlan, plan_id)
        if plan is None:
            return None
        for key, val in data.items():
            if hasattr(plan, key):
                setattr(plan, key, val)
        plan.updated_at = _utcnow()
        session.flush()
        return plan

    @staticmethod
    def delete(session: Session, plan_id: int) -> bool:
        return _delete(session, ResiliencePlan, plan_id)


# ============================================================
#  Approval History CRUD
# ============================================================
class ApprovalHistoryCRUD:
    """CRUD operations for the ``approval_history`` table."""

    @staticmethod
    def create(session: Session, **data: Any) -> ApprovalHistory:
        approval = ApprovalHistory(**data)
        session.add(approval)
        session.flush()
        return approval

    @staticmethod
    def get(session: Session, approval_id: int) -> ApprovalHistory | None:
        return _get_by_id(session, ApprovalHistory, approval_id)

    @staticmethod
    def list_by_entity(session: Session, entity_type: str, entity_id: int) -> list[ApprovalHistory]:
        return _get_all(session, ApprovalHistory,
                        filters=[
                            ApprovalHistory.entity_type == entity_type,
                            ApprovalHistory.entity_id == entity_id,
                        ],
                        order_by=ApprovalHistory.decided_at.desc())

    @staticmethod
    def delete(session: Session, approval_id: int) -> bool:
        return _delete(session, ApprovalHistory, approval_id)
