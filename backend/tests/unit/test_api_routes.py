from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.dependencies import get_db
from backend.app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_test_database() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def get_test_db():
        db: Session = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


def test_health_returns_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_v1_health_returns_200() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_llm_providers_returns_configured_provider_names() -> None:
    response = client.get("/api/v1/llm/providers")

    assert response.status_code == 200
    assert response.json() == {
        "primary_provider": "groq",
        "fallback_provider": "lmstudio",
        "supported_providers": ["groq", "lmstudio"],
    }


def test_repository_load_with_invalid_path_returns_error(tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/repositories/load",
        json={
            "source_type": "local",
            "source": str(tmp_path / "missing"),
            "branch": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "RepositoryError"


def test_analysis_run_with_invalid_path_returns_error(tmp_path: Path) -> None:
    response = client.post(
        "/api/v1/analysis/run",
        json={
            "source_type": "local",
            "source": str(tmp_path / "missing"),
            "branch": None,
            "issue": "POST /login returns 500",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "RepositoryError"
