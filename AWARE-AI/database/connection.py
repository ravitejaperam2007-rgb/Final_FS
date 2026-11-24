"""
AWARE-AI — Database connection and session management (SQLite).

Provides:
  • DatabaseManager   – singleton-style manager for engine + session factory.
  • get_engine()      – create a new SQLAlchemy Engine.
  • get_session()     – context-manager that yields a scoped Session.
  • init_db()         – create all tables (safe to call repeatedly).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

# Default database path (project root)
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "aware_ai.db"
_DEFAULT_URL = f"sqlite:///{_DEFAULT_DB_PATH}"


# ── SQLite PRAGMA tuning ────────────────────────────────────
def _set_sqlite_pragmas(dbapi_conn, connection_record) -> None:  # noqa: ANN001
    """Enable WAL mode, foreign keys, synchronous=NORMAL, and 64MB memory cache on connections."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA cache_size=-64000;")  # 64MB memory cache
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.execute("PRAGMA mmap_size=268435456;")  # 256MB memory map
    cursor.close()


# ── Engine factory ──────────────────────────────────────────
def get_engine(url: str | None = None, echo: bool = False) -> Engine:
    """
    Create and return a SQLAlchemy Engine.

    Parameters
    ----------
    url : str, optional
        SQLAlchemy connection URL.  Defaults to ``sqlite:///aware_ai.db``
        in the project root, overridden by the ``DATABASE_URL`` env var.
    echo : bool
        If True, emit SQL statements to stdout (useful for debugging).
    """
    db_url = url or os.getenv("DATABASE_URL", _DEFAULT_URL)
    engine_kwargs = {"echo": echo, "future": True}
    if db_url == "sqlite:///:memory:":
        from sqlalchemy.pool import StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(db_url, **engine_kwargs)

    # Attach PRAGMA listener for SQLite engines
    if db_url.startswith("sqlite"):
        event.listen(engine, "connect", _set_sqlite_pragmas)

    return engine


# ── Session helpers ─────────────────────────────────────────
@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """
    Yield a transactional Session and handle commit / rollback.

    Usage::

        with get_session(engine) as session:
            session.add(Port(...))
    """
    eng = engine or get_engine()
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Initialisation ──────────────────────────────────────────
def init_db(engine: Engine | None = None) -> Engine:
    """
    Create all tables if they do not exist.  Safe to call more than once.

    Returns the engine used so callers can reuse it.
    """
    eng = engine or get_engine()
    Base.metadata.create_all(eng)
    return eng


def drop_db(engine: Engine) -> None:
    """
    Drop all tables.  **Destructive** — intended for testing only.
    """
    Base.metadata.drop_all(engine)


# ── High-level manager ──────────────────────────────────────
class DatabaseManager:
    """
    Convenience wrapper that owns an engine and exposes session helpers.

    Typical usage::

        db = DatabaseManager("sqlite:///my.db")
        db.init()
        with db.session() as s:
            s.add(Port(...))
    """

    def __init__(self, url: str | None = None, echo: bool = False):
        self.engine = get_engine(url=url, echo=echo)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    # ---- lifecycle ----
    def init(self) -> None:
        """Create all tables (idempotent)."""
        init_db(self.engine)

    def drop(self) -> None:
        """Drop all tables (destructive)."""
        drop_db(self.engine)

    def reset(self) -> None:
        """Drop then re-create all tables."""
        self.drop()
        self.init()

    # ---- sessions ----
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a managed session with auto commit/rollback."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ---- introspection ----
    def table_names(self) -> list[str]:
        """Return a sorted list of table names present in the database."""
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(self.engine)
        return sorted(inspector.get_table_names())

    def table_exists(self, name: str) -> bool:
        """Check whether a specific table exists."""
        return name in self.table_names()

    def row_count(self, table_name: str) -> int:
        """Return the number of rows in a table."""
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM [{table_name}]"))
            return result.scalar() or 0
