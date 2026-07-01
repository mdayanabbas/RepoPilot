from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.models import AnalysisRunRecord, RepositoryRecord
from backend.app.database.repositories import create_architecture_graph_record
from backend.app.dependencies import get_db
from backend.app.dependencies import get_settings
from backend.app.main import app
from backend.app.schemas.architecture import ArchitectureGraph
from backend.app.settings import Settings


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(tmp_path: Path, db_session: Session) -> TestClient:

    def get_test_settings() -> Settings:
        return Settings(WORKSPACE_ROOT=str(tmp_path / "workspaces"), _env_file=None)

    def get_test_db():
        yield db_session

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


def test_analysis_architecture_returns_json(
    client: TestClient,
    db_session: Session,
) -> None:
    analysis_run = _seed_architecture_graph(db_session)

    response = client.get(f"/api/v1/analysis/{analysis_run.id}/architecture")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_run_id"] == analysis_run.id
    assert payload["framework"] == "fastapi"
    assert payload["graph"]["nodes"]
    assert payload["graph"]["edges"]
    assert payload["mermaid"] is None


def test_analysis_architecture_returns_mermaid(
    client: TestClient,
    db_session: Session,
) -> None:
    analysis_run = _seed_architecture_graph(db_session)

    response = client.get(
        f"/api/v1/analysis/{analysis_run.id}/architecture?format=mermaid"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_run_id"] == analysis_run.id
    assert payload["graph"] is None
    assert payload["mermaid"].startswith("graph TD")


def test_analysis_architecture_missing_analysis_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/analysis/missing-analysis/architecture")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Analysis run not found. Make sure you are using analysis_run_id, "
        "not trace_run_id."
    )


def test_analysis_architecture_missing_graph_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    analysis_run = _seed_analysis_run(db_session)

    response = client.get(f"/api/v1/analysis/{analysis_run.id}/architecture")

    assert response.status_code == 404
    assert "not available" in response.json()["detail"]


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


def _seed_architecture_graph(db: Session) -> AnalysisRunRecord:
    analysis_run = _seed_analysis_run(db)
    graph = ArchitectureGraph.model_validate(
        {
            "nodes": [
                {
                    "id": "file:main.py",
                    "type": "file",
                    "label": "main.py",
                    "file_path": "main.py",
                    "metadata": {},
                },
                {
                    "id": "route:GET:/health",
                    "type": "route",
                    "label": "GET /health",
                    "file_path": "main.py",
                    "metadata": {},
                },
            ],
            "edges": [
                {
                    "id": "handles:file:main.py->route:GET:/health",
                    "source": "file:main.py",
                    "target": "route:GET:/health",
                    "type": "handles_route",
                    "metadata": {},
                }
            ],
            "summary": {
                "total_nodes": 2,
                "total_edges": 1,
                "detected_layers": ["entrypoint"],
                "entrypoints": ["main.py"],
                "route_count": 1,
            },
        }
    )
    create_architecture_graph_record(
        db,
        analysis_run_id=analysis_run.id,
        framework="fastapi",
        graph=graph,
        mermaid='graph TD\n  file_main_py["main.py"]',
    )
    return analysis_run


def _seed_analysis_run(db: Session) -> AnalysisRunRecord:
    repository = RepositoryRecord(
        repo_name="demo",
        repo_url=None,
        local_path="workspace/demo",
        branch=None,
        framework="fastapi",
        total_files=1,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)

    analysis_run = AnalysisRunRecord(
        repository_id=repository.id,
        issue_text="Demo issue",
        status="success",
        detected_framework="fastapi",
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)
    return analysis_run
