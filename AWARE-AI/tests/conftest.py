"""
Shared pytest fixtures for AWARE-AI database tests.

Every test gets a fresh in-memory SQLite database via the ``db`` fixture.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path for absolute imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from database.connection import DatabaseManager


@pytest.fixture()
def db():
    """
    Yield a DatabaseManager backed by an in-memory SQLite database.
    Tables are created before each test and torn down after.
    """
    manager = DatabaseManager(url="sqlite:///:memory:")
    manager.init()
    yield manager
    manager.drop()


@pytest.fixture()
def session(db):
    """Yield a raw Session for tests that only need simple inserts."""
    with db.session() as s:
        yield s


# ── sample data factories ──────────────────────────────────
@pytest.fixture()
def sample_port_data():
    return dict(
        name="Shanghai", code="CNSHA", country="China",
        latitude=31.23, longitude=121.47, port_type="sea",
    )


@pytest.fixture()
def sample_port_data_b():
    return dict(
        name="Los Angeles", code="USLAX", country="USA",
        latitude=33.74, longitude=-118.27, port_type="sea",
    )


@pytest.fixture()
def sample_supplier_data():
    return dict(
        name="Acme Components", country="China", region="East Asia",
        contact_email="acme@example.com", reliability_score=0.92,
        lead_time_days=14, risk_tier="low",
    )


@pytest.fixture()
def sample_shipment_data():
    """Note: requires origin/destination port IDs to be injected."""
    return dict(
        tracking_id="SHIP-001",
        cargo_description="Electronic components",
        weight_kg=5000.0,
    )


@pytest.fixture()
def sample_inventory_data():
    return dict(
        sku="ELEC-001", product_name="Capacitor 100µF",
        quantity_on_hand=5000, reorder_point=1000,
        safety_stock=500, unit_cost=0.15,
        warehouse_location="WH-A",
    )
