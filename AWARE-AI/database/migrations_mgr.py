"""
AWARE-AI — Safe schema migrations for SQLite.

A lightweight, file-less migration system that tracks applied versions in a
``_schema_versions`` meta-table and runs Python callables to evolve the schema.

Usage::

    from database.connection import DatabaseManager
    from database.migrations import MigrationManager

    db = DatabaseManager()
    db.init()
    migrator = MigrationManager(db.engine)
    migrator.run_pending()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import Engine, text, inspect as sa_inspect


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── migration registry ──────────────────────────────────────
@dataclass
class Migration:
    """A single versioned migration step."""
    version: int
    description: str
    upgrade: Callable[[Engine], None]


# ── meta-table management ───────────────────────────────────
_META_TABLE = "_schema_versions"

_CREATE_META_SQL = f"""
CREATE TABLE IF NOT EXISTS {_META_TABLE} (
    version   INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


def _ensure_meta_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(_CREATE_META_SQL))


def _applied_versions(engine: Engine) -> set[int]:
    _ensure_meta_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT version FROM {_META_TABLE}")).fetchall()
    return {row[0] for row in rows}


def _record_migration(engine: Engine, migration: Migration) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT INTO {_META_TABLE} (version, description, applied_at) "
                f"VALUES (:v, :d, :a)"
            ),
            {"v": migration.version, "d": migration.description, "a": _utcnow().isoformat()},
        )


# ── built-in migrations ────────────────────────────────────
def _migration_001_add_notes_to_shipments(engine: Engine) -> None:
    """Example: add an optional 'notes' column to shipments (idempotent)."""
    inspector = sa_inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("shipments")]
    if "notes" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE shipments ADD COLUMN notes TEXT"))


def _migration_002_add_last_audit_to_suppliers(engine: Engine) -> None:
    """Add an optional 'last_audit_date' column to suppliers."""
    inspector = sa_inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("suppliers")]
    if "last_audit_date" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN last_audit_date TEXT"))


def _migration_003_add_relational_integration_columns(engine: Engine) -> None:
    """Add integration foreign keys linking weather to shipments, mitigations to root causes, and resilience plans to risks."""
    inspector = sa_inspect(engine)

    weather_cols = [c["name"] for c in inspector.get_columns("weather_evidence")]
    if "shipment_id" not in weather_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE weather_evidence ADD COLUMN shipment_id INTEGER REFERENCES shipments(id) ON DELETE SET NULL"))

    mitigation_cols = [c["name"] for c in inspector.get_columns("mitigation_recommendations")]
    if "root_cause_id" not in mitigation_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE mitigation_recommendations ADD COLUMN root_cause_id INTEGER REFERENCES root_causes(id) ON DELETE SET NULL"))

    resilience_cols = [c["name"] for c in inspector.get_columns("resilience_plans")]
    with engine.begin() as conn:
        if "risk_assessment_id" not in resilience_cols:
            conn.execute(text("ALTER TABLE resilience_plans ADD COLUMN risk_assessment_id INTEGER REFERENCES risk_assessments(id) ON DELETE SET NULL"))
        if "mitigation_id" not in resilience_cols:
            conn.execute(text("ALTER TABLE resilience_plans ADD COLUMN mitigation_id INTEGER REFERENCES mitigation_recommendations(id) ON DELETE SET NULL"))
        if "root_cause_id" not in resilience_cols:
            conn.execute(text("ALTER TABLE resilience_plans ADD COLUMN root_cause_id INTEGER REFERENCES root_causes(id) ON DELETE SET NULL"))


# Registry — append new Migration objects here as the schema evolves.
MIGRATIONS: list[Migration] = [
    Migration(1, "Add notes column to shipments", _migration_001_add_notes_to_shipments),
    Migration(2, "Add last_audit_date to suppliers", _migration_002_add_last_audit_to_suppliers),
    Migration(3, "Add relational integration columns across modules", _migration_003_add_relational_integration_columns),
]


# ── migration manager ──────────────────────────────────────
class MigrationManager:
    """
    Run registered migrations that haven't been applied yet.

    Parameters
    ----------
    engine : Engine | DatabaseManager
        The SQLAlchemy engine or DatabaseManager connected to the target database.
    migrations : list[Migration], optional
        Override the default migration registry (useful for testing).
    """

    def __init__(self, engine: Engine | any = None, migrations: list[Migration] | None = None, db_manager: any = None):
        if db_manager is not None:
            self.engine = getattr(db_manager, "engine", db_manager)
        elif hasattr(engine, "engine"):
            self.engine = engine.engine
        else:
            self.engine = engine
        self.migrations = migrations if migrations is not None else MIGRATIONS

    def latest_version(self) -> int:
        """Return the highest version in the migration registry."""
        return max((m.version for m in self.migrations), default=0)

    def history(self) -> list[dict]:
        """Return applied migration history records."""
        _ensure_meta_table(self.engine)
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT version, description, applied_at FROM {_META_TABLE} ORDER BY version ASC")
            ).fetchall()
        return [
            {"version": r[0], "description": r[1], "applied_at": r[2], "success": True}
            for r in rows
        ]

    # ---- public API ----
    def pending(self) -> list[Migration]:
        """Return migrations that have not yet been applied."""
        applied = _applied_versions(self.engine)
        return [m for m in self.migrations if m.version not in applied]

    def applied(self) -> set[int]:
        """Return the set of already-applied version numbers."""
        return _applied_versions(self.engine)

    def run_pending(self) -> list[Migration]:
        """
        Apply all pending migrations in version order.

        Returns the list of migrations that were applied.
        """
        _ensure_meta_table(self.engine)
        to_run = sorted(self.pending(), key=lambda m: m.version)
        applied: list[Migration] = []
        for migration in to_run:
            migration.upgrade(self.engine)
            _record_migration(self.engine, migration)
            applied.append(migration)
        return applied

    def current_version(self) -> int:
        """Return the highest applied version, or 0 if none."""
        versions = _applied_versions(self.engine)
        return max(versions) if versions else 0

    def run_to(self, target_version: int) -> list[Migration]:
        """Apply pending migrations up to (and including) *target_version*."""
        _ensure_meta_table(self.engine)
        applied_set = _applied_versions(self.engine)
        to_run = sorted(
            [m for m in self.migrations if m.version not in applied_set and m.version <= target_version],
            key=lambda m: m.version,
        )
        applied: list[Migration] = []
        for migration in to_run:
            migration.upgrade(self.engine)
            _record_migration(self.engine, migration)
            applied.append(migration)
        return applied
