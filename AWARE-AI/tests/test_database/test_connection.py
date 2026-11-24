"""
Tests — Database connection, initialisation, and DatabaseManager.
"""

import pytest
from database.connection import DatabaseManager, get_engine, init_db
from database.models import ALL_MODELS


class TestGetEngine:
    """Engine factory tests."""

    def test_creates_engine(self):
        engine = get_engine(url="sqlite:///:memory:")
        assert engine is not None
        assert "memory" in str(engine.url)

    def test_foreign_keys_enabled(self):
        engine = get_engine(url="sqlite:///:memory:")
        with engine.connect() as conn:
            result = conn.execute(__import__("sqlalchemy").text("PRAGMA foreign_keys"))
            assert result.scalar() == 1


class TestInitDb:
    """Table creation tests."""

    def test_creates_all_tables(self):
        engine = get_engine(url="sqlite:///:memory:")
        init_db(engine)
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        table_names = set(inspector.get_table_names())
        expected = {m.__tablename__ for m in ALL_MODELS}
        assert expected.issubset(table_names)

    def test_idempotent(self):
        engine = get_engine(url="sqlite:///:memory:")
        init_db(engine)
        init_db(engine)  # should not raise


class TestDatabaseManager:
    """DatabaseManager lifecycle tests."""

    def test_init_creates_tables(self, db):
        tables = db.table_names()
        assert "ports" in tables
        assert "shipments" in tables
        assert "risk_assessments" in tables
        assert len(tables) >= 13

    def test_table_exists(self, db):
        assert db.table_exists("ports") is True
        assert db.table_exists("nonexistent") is False

    def test_row_count_empty(self, db):
        assert db.row_count("ports") == 0

    def test_reset(self, db):
        from database.crud import PortCRUD
        with db.session() as s:
            PortCRUD.create(s, name="X", code="XXXXX", country="X",
                            latitude=0.0, longitude=0.0)
        assert db.row_count("ports") == 1
        db.reset()
        assert db.row_count("ports") == 0

    def test_session_rollback_on_error(self, db):
        """Session should rollback and not persist partial writes on error."""
        try:
            with db.session() as s:
                from database.models import Port
                s.add(Port(name="A", code="AAAAA", country="A",
                           latitude=0.0, longitude=0.0))
                s.flush()
                raise RuntimeError("simulated error")
        except RuntimeError:
            pass
        assert db.row_count("ports") == 0
