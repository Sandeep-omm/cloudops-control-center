import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def pytest_configure():
    os.environ["DATABASE_URL"] = os.getenv(
        "CLOUDOPS_TEST_DATABASE_URL", "sqlite:///./tests/test-cloudops.db"
    )
    os.environ["DATA_DIR"] = os.getenv(
        "CLOUDOPS_TEST_DATA_DIR", str(Path(__file__).parent / ".data")
    )


@pytest.fixture
def client():
    from app.db import Base, SessionLocal, engine
    from app.main import app
    from app.models import Job

    test_data_dir = Path(os.environ["DATA_DIR"])
    shutil.rmtree(test_data_dir, ignore_errors=True)
    test_data_dir.mkdir(parents=True, exist_ok=True)
    with engine.begin() as connection:
        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)

    with TestClient(app) as test_client:
        yield test_client

    with SessionLocal() as session:
        session.query(Job).delete()
        session.commit()
    shutil.rmtree(test_data_dir, ignore_errors=True)
