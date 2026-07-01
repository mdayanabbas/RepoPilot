from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.dependencies import get_db
from backend.app.dependencies import get_settings
from backend.app.main import app
from backend.app.settings import Settings


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def get_test_settings() -> Settings:
        return Settings(WORKSPACE_ROOT=str(tmp_path / "workspaces"), _env_file=None)

    def get_test_db():
        db: Session = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_db] = get_test_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_db, None)


def test_architecture_build_returns_json_graph(
    client: TestClient,
    tmp_path: Path,
) -> None:
    source = _write_fastapi_repo(tmp_path)

    response = client.post(
        "/api/v1/architecture/build",
        json={"source_type": "local", "source": str(source), "format": "json"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["framework"] == "fastapi"
    assert payload["graph"]["nodes"]
    assert payload["summary"]["route_count"] == 1
    assert payload["mermaid"] is None


def test_architecture_build_returns_mermaid(
    client: TestClient,
    tmp_path: Path,
) -> None:
    source = _write_fastapi_repo(tmp_path)

    response = client.post(
        "/api/v1/architecture/build",
        json={"source_type": "local", "source": str(source), "format": "mermaid"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["framework"] == "fastapi"
    assert payload["graph"] is None
    assert payload["mermaid"].startswith("graph TD")
    assert payload["summary"]["route_count"] == 1


def test_architecture_build_invalid_source_returns_error(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/api/v1/architecture/build",
        json={"source_type": "local", "source": str(tmp_path / "missing")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "RepositoryError"


def test_analysis_architecture_returns_not_implemented(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/analysis/analysis-1/architecture")

    assert response.status_code == 501
    assert "not available yet" in response.json()["message"]


def _write_fastapi_repo(tmp_path: Path) -> Path:
    source = tmp_path / "fastapi_repo"
    source.mkdir()
    (source / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (source / "main.py").write_text(
        """from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
""",
        encoding="utf-8",
    )
    return source
