"""
AWARE-AI — Input validation for database operations.

Each validator raises ``ValueError`` with a descriptive message on failure
and returns ``None`` on success, so callers can do::

    validate_port_data(data)   # raises or passes silently
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


# ── generic helpers ─────────────────────────────────────────
def _require(data: dict, field: str, expected_type: type | tuple[type, ...]) -> None:
    """Raise ValueError if *field* is missing or has the wrong type."""
    if field not in data:
        raise ValueError(f"Missing required field: '{field}'")
    if not isinstance(data[field], expected_type):
        raise ValueError(
            f"Field '{field}' must be {expected_type}, got {type(data[field]).__name__}"
        )


def _optional_type(data: dict, field: str, expected_type: type | tuple[type, ...]) -> None:
    """Raise ValueError if *field* is present but has the wrong type."""
    if field in data and data[field] is not None:
        if not isinstance(data[field], expected_type):
            raise ValueError(
                f"Field '{field}' must be {expected_type}, got {type(data[field]).__name__}"
            )


def _in_range(value: float | int, lo: float, hi: float, name: str) -> None:
    if not (lo <= value <= hi):
        raise ValueError(f"'{name}' must be between {lo} and {hi}, got {value}")


# ── email ───────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str, field: str = "email") -> None:
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Invalid email in '{field}': {email!r}")


# ============================================================
#  Port
# ============================================================
def validate_port_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating / updating a Port."""
    _require(data, "name", str)
    _require(data, "code", str)
    _require(data, "country", str)
    _require(data, "latitude", (int, float))
    _require(data, "longitude", (int, float))

    if len(data["code"]) > 20:
        raise ValueError("Port 'code' must be ≤ 20 characters")
    _in_range(data["latitude"], -90, 90, "latitude")
    _in_range(data["longitude"], -180, 180, "longitude")
    _optional_type(data, "port_type", str)
    _optional_type(data, "timezone", str)


# ============================================================
#  Supplier
# ============================================================
_VALID_RISK_TIERS = {"low", "medium", "high", "critical"}


def validate_supplier_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating / updating a Supplier."""
    _require(data, "name", str)
    _require(data, "country", str)

    _optional_type(data, "contact_email", str)
    if data.get("contact_email"):
        _validate_email(data["contact_email"], "contact_email")

    _optional_type(data, "reliability_score", (int, float))
    if "reliability_score" in data and data["reliability_score"] is not None:
        _in_range(data["reliability_score"], 0.0, 1.0, "reliability_score")

    _optional_type(data, "lead_time_days", int)
    if "lead_time_days" in data and data["lead_time_days"] is not None:
        if data["lead_time_days"] < 0:
            raise ValueError("'lead_time_days' must be ≥ 0")

    _optional_type(data, "risk_tier", str)
    if data.get("risk_tier") and data["risk_tier"] not in _VALID_RISK_TIERS:
        raise ValueError(f"'risk_tier' must be one of {_VALID_RISK_TIERS}")


# ============================================================
#  Shipment
# ============================================================
_VALID_STATUSES = {"pending", "in_transit", "delayed", "delivered", "cancelled"}
_VALID_PRIORITIES = {"low", "medium", "high", "critical"}


def validate_shipment_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating / updating a Shipment."""
    _require(data, "tracking_id", str)
    _require(data, "origin_port_id", int)
    _require(data, "destination_port_id", int)

    if data["origin_port_id"] == data["destination_port_id"]:
        raise ValueError("Origin and destination ports must differ")

    _optional_type(data, "weight_kg", (int, float))
    if data.get("weight_kg") is not None and data["weight_kg"] <= 0:
        raise ValueError("'weight_kg' must be > 0")

    _optional_type(data, "status", str)
    if data.get("status") and data["status"] not in _VALID_STATUSES:
        raise ValueError(f"'status' must be one of {_VALID_STATUSES}")

    _optional_type(data, "priority", str)
    if data.get("priority") and data["priority"] not in _VALID_PRIORITIES:
        raise ValueError(f"'priority' must be one of {_VALID_PRIORITIES}")


# ============================================================
#  Weather Evidence
# ============================================================
_VALID_SEVERITIES = {"minor", "moderate", "severe", "extreme"}


def validate_weather_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating Weather Evidence."""
    _require(data, "port_id", int)
    _require(data, "event_type", str)
    _require(data, "severity", str)
    _require(data, "start_time", datetime)

    if data["severity"] not in _VALID_SEVERITIES:
        raise ValueError(f"'severity' must be one of {_VALID_SEVERITIES}")

    _optional_type(data, "wind_speed_kmh", (int, float))
    if data.get("wind_speed_kmh") is not None and data["wind_speed_kmh"] < 0:
        raise ValueError("'wind_speed_kmh' must be ≥ 0")

    _optional_type(data, "shipment_id", int)


# ============================================================
#  Inventory
# ============================================================
def validate_inventory_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating / updating an Inventory record."""
    _require(data, "sku", str)
    _require(data, "product_name", str)

    for field in ("quantity_on_hand", "reorder_point", "safety_stock"):
        _optional_type(data, field, int)
        if field in data and data[field] is not None and data[field] < 0:
            raise ValueError(f"'{field}' must be ≥ 0")

    _optional_type(data, "unit_cost", (int, float))
    if data.get("unit_cost") is not None and data["unit_cost"] < 0:
        raise ValueError("'unit_cost' must be ≥ 0")


# ============================================================
#  Risk Assessment
# ============================================================
_VALID_ENTITY_TYPES = {"shipment", "supplier", "route", "port", "inventory"}


def validate_risk_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating a Risk Assessment."""
    _require(data, "entity_type", str)
    _require(data, "entity_id", int)
    _require(data, "risk_category", str)
    _require(data, "likelihood", (int, float))
    _require(data, "impact", (int, float))

    if data["entity_type"] not in _VALID_ENTITY_TYPES:
        raise ValueError(f"'entity_type' must be one of {_VALID_ENTITY_TYPES}")

    _in_range(data["likelihood"], 0.0, 1.0, "likelihood")
    _in_range(data["impact"], 0.0, 1.0, "impact")

    # risk_score is auto-computed if missing
    if "risk_score" in data:
        _in_range(data["risk_score"], 0.0, 1.0, "risk_score")


# ============================================================
#  ML Prediction
# ============================================================
def validate_ml_prediction_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating an ML Prediction record."""
    _require(data, "model_name", str)
    _require(data, "model_version", str)
    _require(data, "prediction_type", str)
    _require(data, "predicted_value", (int, float))

    _optional_type(data, "confidence", (int, float))
    if data.get("confidence") is not None:
        _in_range(data["confidence"], 0.0, 1.0, "confidence")


# ============================================================
#  Resilience Plan
# ============================================================
def validate_resilience_plan_data(data: dict[str, Any]) -> None:
    """Validate data dict for creating / updating a Resilience Plan."""
    _require(data, "name", str)
    _require(data, "risk_category", str)

    _optional_type(data, "status", str)
    valid_statuses = {"draft", "active", "archived"}
    if data.get("status") and data["status"] not in valid_statuses:
        raise ValueError(f"'status' must be one of {valid_statuses}")

    _optional_type(data, "risk_assessment_id", int)
    _optional_type(data, "mitigation_id", int)
    _optional_type(data, "root_cause_id", int)
