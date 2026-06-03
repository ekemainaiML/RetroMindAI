"""Unit-test conftest: overrides auto-seeded DB fixtures.

These tests never touch PostgreSQL, so seed_test_workshop and clean_db
are replaced with no-ops to avoid connection errors.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def seed_test_workshop():
    yield


@pytest.fixture(autouse=True)
def clean_db():
    yield
