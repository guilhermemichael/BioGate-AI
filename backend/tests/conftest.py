from __future__ import annotations

import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / "test_suite.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.services.rate_limit_service import rate_limiter


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rate_limiter._events.clear()
    yield
    Base.metadata.drop_all(bind=engine)
    rate_limiter._events.clear()


@pytest.fixture
def client():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Guilherme Michael",
            "email": "guilherme@example.com",
            "password": "StrongPass123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def auth_headers(registered_user: dict[str, object]):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
