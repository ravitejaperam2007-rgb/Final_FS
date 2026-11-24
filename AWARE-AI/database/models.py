"""
AWARE-AI — SQLAlchemy ORM Model Definitions (SQLite)

13 tables covering the full supply-chain intelligence domain:
  Shipments, ShipmentHistory, Ports, WeatherEvidence, Suppliers,
  Inventory, RiskAssessments, MLPredictions, AgentExecutionHistory,
  RootCauses, MitigationRecommendations, ResiliencePlans, ApprovalHistory.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ── helpers ─────────────────────────────────────────────────
def _utcnow() -> datetime:
    # Use timezone-naive UTC for SQLite compatibility (SQLite stores as string without tz)
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── enums ───────────────────────────────────────────────────
class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PriorityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WeatherSeverity(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ApprovalAction(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class AgentTaskStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


# ── base ────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Root declarative base for all AWARE-AI models."""
    pass


# ============================================================
#  1. Ports
# ============================================================
class Port(Base):
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    code = Column(String(20), nullable=False, unique=True)          # UN/LOCODE
    country = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    port_type = Column(String(50), default="sea")                   # sea / air / land
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # relationships
    weather_events = relationship("WeatherEvidence", back_populates="port")
    origin_shipments = relationship(
        "Shipment", foreign_keys="Shipment.origin_port_id", back_populates="origin_port",
    )
    destination_shipments = relationship(
        "Shipment", foreign_keys="Shipment.destination_port_id", back_populates="destination_port",
    )

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_port_lat"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_port_lon"),
        Index("ix_ports_country", "country"),
    )

    def __repr__(self) -> str:
        return f"<Port {self.code} – {self.name}>"


# ============================================================
#  2. Suppliers
# ============================================================
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    country = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    contact_email = Column(String(254), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    reliability_score = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=0)
    category = Column(String(100), nullable=True)
    risk_tier = Column(String(20), default="medium")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # relationships
    shipments = relationship("Shipment", back_populates="supplier")
    inventory_items = relationship("Inventory", back_populates="supplier")

    __table_args__ = (
        CheckConstraint(
            "reliability_score BETWEEN 0.0 AND 1.0",
            name="ck_supplier_reliability",
        ),
        CheckConstraint("lead_time_days >= 0", name="ck_supplier_lead_time"),
        Index("ix_suppliers_country", "country"),
        Index("ix_suppliers_risk_tier", "risk_tier"),
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.id} – {self.name}>"


# ============================================================
#  3. Shipments
# ============================================================
class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tracking_id = Column(String(50), nullable=False, unique=True)
    origin_port_id = Column(Integer, ForeignKey("ports.id"), nullable=False)
    destination_port_id = Column(Integer, ForeignKey("ports.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    cargo_description = Column(String(500), nullable=True)
    weight_kg = Column(Float, nullable=True)
    status = Column(
        Enum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False,
    )
    priority = Column(
        Enum(PriorityLevel), default=PriorityLevel.MEDIUM, nullable=False,
    )
    departure_date = Column(DateTime, nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # relationships
    origin_port = relationship("Port", foreign_keys=[origin_port_id], back_populates="origin_shipments")
    destination_port = relationship("Port", foreign_keys=[destination_port_id], back_populates="destination_shipments")
    supplier = relationship("Supplier", back_populates="shipments")
    history = relationship(
        "ShipmentHistory",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentHistory.timestamp",
    )

    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_shipment_weight"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_departure", "departure_date"),
    )

    def __repr__(self) -> str:
        return f"<Shipment {self.tracking_id} [{self.status}]>"


# ============================================================
#  4. Shipment History
# ============================================================
class ShipmentHistory(Base):
    __tablename__ = "shipment_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    previous_status = Column(Enum(ShipmentStatus), nullable=True)
    new_status = Column(Enum(ShipmentStatus), nullable=False)
    changed_by = Column(String(100), nullable=False, default="system")
    change_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False)

    # relationships
    shipment = relationship("Shipment", back_populates="history")

    __table_args__ = (
        Index("ix_shipment_history_shipment", "shipment_id"),
        Index("ix_shipment_history_ts", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ShipmentHistory {self.shipment_id}: {self.previous_status} → {self.new_status}>"


# ============================================================
#  5. Weather Evidence
# ============================================================
class WeatherEvidence(Base):
    __tablename__ = "weather_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(Integer, ForeignKey("ports.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)                 # hurricane, flood, fog …
    severity = Column(Enum(WeatherSeverity), nullable=False)
    description = Column(Text, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    visibility_km = Column(Float, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    source = Column(String(100), nullable=True)                      # API provider name
    raw_data_json = Column(Text, nullable=True)                      # original payload
    recorded_at = Column(DateTime, default=_utcnow, nullable=False)

    # relationships
    port = relationship("Port", back_populates="weather_events")
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    shipment = relationship("Shipment", backref="weather_evidence")

    __table_args__ = (
        Index("ix_weather_port", "port_id"),
        Index("ix_weather_severity", "severity"),
        Index("ix_weather_start", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<WeatherEvidence {self.event_type} @port={self.port_id} [{self.severity}]>"


# ============================================================
#  6. Inventory
# ============================================================
class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(50), nullable=False, unique=True)
    product_name = Column(String(200), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    reorder_point = Column(Integer, default=0, nullable=False)
    safety_stock = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    warehouse_location = Column(String(100), nullable=True)
    last_replenished = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # relationships
    supplier = relationship("Supplier", back_populates="inventory_items")

    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_inv_qty"),
        CheckConstraint("reorder_point >= 0", name="ck_inv_reorder"),
        CheckConstraint("safety_stock >= 0", name="ck_inv_safety"),
        CheckConstraint("unit_cost >= 0", name="ck_inv_cost"),
        Index("ix_inventory_sku", "sku"),
    )

    def __repr__(self) -> str:
        return f"<Inventory {self.sku} qty={self.quantity_on_hand}>"


# ============================================================
#  7. Risk Assessments
# ============================================================
class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)                 # shipment / supplier / route / port
    entity_id = Column(Integer, nullable=False)
    risk_category = Column(String(100), nullable=False)              # weather / geopolitical / quality …
    likelihood = Column(Float, nullable=False)                       # 0.0 – 1.0
    impact = Column(Float, nullable=False)                           # 0.0 – 1.0
    risk_score = Column(Float, nullable=False)                       # likelihood × impact
    risk_level = Column(Enum(RiskLevel), nullable=False)
    description = Column(Text, nullable=True)
    assessed_by = Column(String(100), nullable=False, default="system")
    assessed_at = Column(DateTime, default=_utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # relationships
    root_causes = relationship("RootCause", back_populates="risk_assessment")
    mitigations = relationship("MitigationRecommendation", back_populates="risk_assessment")

    __table_args__ = (
        CheckConstraint("likelihood BETWEEN 0.0 AND 1.0", name="ck_risk_likelihood"),
        CheckConstraint("impact BETWEEN 0.0 AND 1.0", name="ck_risk_impact"),
        CheckConstraint("risk_score BETWEEN 0.0 AND 1.0", name="ck_risk_score"),
        Index("ix_risk_entity", "entity_type", "entity_id"),
        Index("ix_risk_level", "risk_level"),
    )

    def __repr__(self) -> str:
        return f"<RiskAssessment {self.entity_type}:{self.entity_id} [{self.risk_level}]>"


# ============================================================
#  8. ML Predictions
# ============================================================
class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction_type = Column(String(100), nullable=False)            # demand_forecast / risk / anomaly
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    predicted_value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    features_json = Column(Text, nullable=True)                      # input features snapshot
    shap_values_json = Column(Text, nullable=True)                   # SHAP explanation
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence BETWEEN 0.0 AND 1.0)",
            name="ck_ml_confidence",
        ),
        Index("ix_ml_model", "model_name", "model_version"),
        Index("ix_ml_type", "prediction_type"),
    )

    def __repr__(self) -> str:
        return f"<MLPrediction {self.model_name}:{self.prediction_type} = {self.predicted_value}>"


# ============================================================
#  9. Agent Execution History
# ============================================================
class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    status = Column(Enum(AgentTaskStatus), nullable=False, default=AgentTaskStatus.RUNNING)
    started_at = Column(DateTime, default=_utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_agent_name", "agent_name"),
        Index("ix_agent_status", "status"),
        Index("ix_agent_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentExecution {self.agent_name}:{self.task_type} [{self.status}]>"


# ============================================================
#  10. Root Causes
# ============================================================
class RootCause(Base):
    __tablename__ = "root_causes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_assessment_id = Column(
        Integer, ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False,
    )
    cause_category = Column(String(100), nullable=False)             # weather / supplier / logistics …
    description = Column(Text, nullable=False)
    contributing_factors_json = Column(Text, nullable=True)          # JSON array
    identified_by = Column(String(100), nullable=False, default="system")
    identified_at = Column(DateTime, default=_utcnow, nullable=False)

    # relationships
    risk_assessment = relationship("RiskAssessment", back_populates="root_causes")
    resilience_plans = relationship("ResiliencePlan", back_populates="root_cause")
    mitigations = relationship("MitigationRecommendation", back_populates="root_cause")

    __table_args__ = (
        Index("ix_rootcause_risk", "risk_assessment_id"),
    )

    def __repr__(self) -> str:
        return f"<RootCause {self.cause_category} for risk={self.risk_assessment_id}>"


# ============================================================
#  11. Mitigation Recommendations
# ============================================================
class MitigationRecommendation(Base):
    __tablename__ = "mitigation_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_assessment_id = Column(
        Integer, ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False,
    )
    recommendation = Column(Text, nullable=False)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    estimated_time_days = Column(Integer, nullable=True)
    status = Column(
        Enum(RecommendationStatus), default=RecommendationStatus.PROPOSED, nullable=False,
    )
    recommended_by = Column(String(100), nullable=False, default="system")
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # relationships
    risk_assessment = relationship("RiskAssessment", back_populates="mitigations")
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True)
    root_cause = relationship("RootCause", back_populates="mitigations")
    resilience_plans = relationship("ResiliencePlan", back_populates="mitigation")

    __table_args__ = (
        Index("ix_mitigation_risk", "risk_assessment_id"),
        Index("ix_mitigation_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<MitigationRecommendation {self.id} [{self.status}]>"


# ============================================================
#  12. Resilience Plans
# ============================================================
class ResiliencePlan(Base):
    __tablename__ = "resilience_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    risk_category = Column(String(100), nullable=False)
    trigger_conditions_json = Column(Text, nullable=True)            # JSON
    strategies_json = Column(Text, nullable=True)                    # JSON array of strategy keys
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT, nullable=False)
    owner = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)

    # relationships to linked recommendations / root causes / risks
    risk_assessment_id = Column(Integer, ForeignKey("risk_assessments.id", ondelete="SET NULL"), nullable=True)
    risk_assessment = relationship("RiskAssessment", backref="resilience_plans")
    mitigation_id = Column(Integer, ForeignKey("mitigation_recommendations.id", ondelete="SET NULL"), nullable=True)
    mitigation = relationship("MitigationRecommendation", back_populates="resilience_plans")
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True)
    root_cause = relationship("RootCause", back_populates="resilience_plans")

    __table_args__ = (
        Index("ix_plan_status", "status"),
        Index("ix_plan_category", "risk_category"),
    )

    def __repr__(self) -> str:
        return f"<ResiliencePlan {self.name!r} [{self.status}]>"


# ============================================================
#  13. Approval History
# ============================================================
class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)                 # resilience_plan / mitigation …
    entity_id = Column(Integer, nullable=False)
    action = Column(Enum(ApprovalAction), nullable=False)
    approved_by = Column(String(100), nullable=False)
    comments = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_approval_entity", "entity_type", "entity_id"),
        Index("ix_approval_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalHistory {self.entity_type}:{self.entity_id} [{self.action}]>"


# ── convenience list of all models ──────────────────────────
ALL_MODELS: list[type[Base]] = [
    Port,
    Supplier,
    Shipment,
    ShipmentHistory,
    WeatherEvidence,
    Inventory,
    RiskAssessment,
    MLPrediction,
    AgentExecution,
    RootCause,
    MitigationRecommendation,
    ResiliencePlan,
    ApprovalHistory,
]
