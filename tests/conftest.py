"""Shared fixtures for the test suite."""
from __future__ import annotations

import pytest

from tests import _pgdb


@pytest.fixture
def pg_url():
    """Yield the URL of a fresh, empty PostgreSQL database, dropped on teardown.

    Replaces the per-test throwaway SQLite files the suite used previously.
    """
    url = _pgdb.create_database("kbcv_case")
    try:
        yield url
    finally:
        _pgdb.drop_database(url)
