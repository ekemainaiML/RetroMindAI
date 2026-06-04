import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow integration tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow (run with --runslow)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="use --runslow to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    yield


from api.main import app  # noqa: E402
from core.auth import hash_api_key  # noqa: E402
from core.database import SessionLocal  # noqa: E402
from core.models import Intake, Job, Workshop  # noqa: E402

TEST_API_KEY = "rm_test_" + "a" * 37
TEST_API_KEY_HASH = hash_api_key(TEST_API_KEY)


@pytest.fixture(scope="session", autouse=True)
def seed_test_workshop(run_migrations):
    db = SessionLocal()
    try:
        existing = db.query(Workshop).filter(Workshop.name == "Test Workshop").first()
        if not existing:
            workshop = Workshop(
                id=uuid.uuid4(),
                name="Test Workshop",
                api_key_hash=TEST_API_KEY_HASH,
                api_key_prefix="rm_test",
                is_active=True,
            )
            db.add(workshop)
            db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    try:
        workshop = db.query(Workshop).filter(Workshop.name == "Test Workshop").first()
        if workshop:
            intake_ids = [
                row[0] for row in db.query(Intake.id).filter(Intake.workshop_id == workshop.id).all()
            ]
            if intake_ids:
                db.query(Job).filter(Job.intake_id.in_(intake_ids)).delete(synchronize_session=False)
            db.query(Intake).filter(Intake.workshop_id == workshop.id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def get_test_workshop_id() -> str:
    db = SessionLocal()
    try:
        workshop = db.query(Workshop).filter(Workshop.name == "Test Workshop").first()
        return str(workshop.id) if workshop else ""
    finally:
        db.close()


def auth_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    client.headers.update(auth_headers())
    return client
