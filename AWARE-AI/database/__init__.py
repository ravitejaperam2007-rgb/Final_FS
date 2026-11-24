"""
Database package — connection, ORM models, CRUD, validation, and migrations.
"""

import os

# Ensure pure-Python fallback for Cython C-extensions across environments
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")

from database.connection import DatabaseManager, get_engine, get_session, init_db
from database.models import (
    ALL_MODELS,
    Base,
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
)
from database.crud import (
    PortCRUD,
    SupplierCRUD,
    ShipmentCRUD,
    WeatherCRUD,
    InventoryCRUD,
    RiskCRUD,
    MLPredictionCRUD,
    AgentExecutionCRUD,
    RootCauseCRUD,
    MitigationCRUD,
    ResiliencePlanCRUD,
    ApprovalHistoryCRUD,
)
from database.migrations_mgr import Migration, MigrationManager
from database.services import BackendIntegrationService

__all__ = [
    # connection
    "DatabaseManager", "get_engine", "get_session", "init_db",
    # service
    "BackendIntegrationService",
    # models
    "ALL_MODELS", "Base",
    "Port", "Supplier", "Shipment", "ShipmentHistory",
    "WeatherEvidence", "Inventory", "RiskAssessment", "MLPrediction",
    "AgentExecution", "RootCause", "MitigationRecommendation",
    "ResiliencePlan", "ApprovalHistory",
    # CRUD
    "PortCRUD", "SupplierCRUD", "ShipmentCRUD", "WeatherCRUD",
    "InventoryCRUD", "RiskCRUD", "MLPredictionCRUD",
    "AgentExecutionCRUD", "RootCauseCRUD", "MitigationCRUD",
    "ResiliencePlanCRUD", "ApprovalHistoryCRUD",
    # migrations
    "Migration",
    "MigrationManager",
]
