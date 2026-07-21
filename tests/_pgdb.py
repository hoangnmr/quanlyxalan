"""Provision throwaway PostgreSQL databases for the test suite.

Each test module needs its own database so modules stay isolated the way the
per-file SQLite databases used to be. ``ADMIN_URL`` points at a maintenance
database used only to CREATE/DROP the per-test databases.
"""
from __future__ import annotations

import os
import uuid

from sqlalchemy import create_engine, text

ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql+psycopg://localhost/postgres"
)
BASE_URL = ADMIN_URL.rsplit("/", 1)[0]


def _admin_execute(statement: str) -> None:
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text(statement))
    finally:
        engine.dispose()


def create_database(prefix: str = "kbcv_test") -> str:
    """Create a uniquely named database and return its SQLAlchemy URL."""
    name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    _admin_execute(f'CREATE DATABASE "{name}"')
    return f"{BASE_URL}/{name}"


def drop_database(url: str) -> None:
    """Drop a database created by :func:`create_database`, ignoring absence."""
    name = url.rsplit("/", 1)[-1]
    _admin_execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
