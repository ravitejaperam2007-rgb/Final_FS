"""
Tests — Migration system.
"""

import pytest
from sqlalchemy import inspect as sa_inspect

from database.connection import DatabaseManager
from database.migrations_mgr import Migration, MigrationManager


class TestMigrationManager:
    def test_run_pending_applies_all(self, db):
        migrator = MigrationManager(db.engine)
        applied = migrator.run_pending()
        assert len(applied) == 3  # three built-in migrations
        assert migrator.current_version() == 3

    def test_idempotent(self, db):
        migrator = MigrationManager(db.engine)
        migrator.run_pending()
        second_run = migrator.run_pending()
        assert len(second_run) == 0

    def test_pending_before_run(self, db):
        migrator = MigrationManager(db.engine)
        assert len(migrator.pending()) == 3

    def test_applied_versions(self, db):
        migrator = MigrationManager(db.engine)
        migrator.run_pending()
        assert migrator.applied() == {1, 2, 3}

    def test_run_to_partial(self, db):
        migrator = MigrationManager(db.engine)
        applied = migrator.run_to(1)
        assert len(applied) == 1
        assert migrator.current_version() == 1
        assert len(migrator.pending()) == 2

    def test_migration_adds_notes_column(self, db):
        migrator = MigrationManager(db.engine)
        migrator.run_to(1)
        inspector = sa_inspect(db.engine)
        columns = [c["name"] for c in inspector.get_columns("shipments")]
        assert "notes" in columns

    def test_migration_adds_audit_column(self, db):
        migrator = MigrationManager(db.engine)
        migrator.run_pending()
        inspector = sa_inspect(db.engine)
        columns = [c["name"] for c in inspector.get_columns("suppliers")]
        assert "last_audit_date" in columns

    def test_migration_adds_relational_integration_columns(self, db):
        migrator = MigrationManager(db.engine)
        migrator.run_pending()
        inspector = sa_inspect(db.engine)

        w_cols = [c["name"] for c in inspector.get_columns("weather_evidence")]
        assert "shipment_id" in w_cols

        m_cols = [c["name"] for c in inspector.get_columns("mitigation_recommendations")]
        assert "root_cause_id" in m_cols

        r_cols = [c["name"] for c in inspector.get_columns("resilience_plans")]
        assert "risk_assessment_id" in r_cols
        assert "mitigation_id" in r_cols
        assert "root_cause_id" in r_cols

    def test_custom_migration_registry(self, db):
        """Test with a custom single-step migration."""
        def _add_col(engine):
            from sqlalchemy import text
            inspector = sa_inspect(engine)
            cols = [c["name"] for c in inspector.get_columns("ports")]
            if "custom_field" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE ports ADD COLUMN custom_field TEXT"))

        custom = [Migration(100, "Add custom_field to ports", _add_col)]
        migrator = MigrationManager(db.engine, migrations=custom)
        applied = migrator.run_pending()
        assert len(applied) == 1
        assert migrator.current_version() == 100

        inspector = sa_inspect(db.engine)
        cols = [c["name"] for c in inspector.get_columns("ports")]
        assert "custom_field" in cols
