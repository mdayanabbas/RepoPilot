from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.repositories import (
    create_analysis_run_record,
    create_fix_plan_record,
    create_repository_record,
    create_retrieval_result_records,
    update_analysis_run_status,
)
from backend.app.dependencies import get_db
from backend.app.main import app
from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.retrieval import RelevantFile, RetrievalResult


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def get_test_db() -> Generator[Session, None, None]:
        request_db = TestingSessionLocal()
        try:
            yield request_db
        finally:
            request_db.close()

    app.dependency_overrides[get_db] = get_test_db
    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    del db_session
    return TestClient(app)


def test_list_analysis_runs(client: TestClient, db_session: Session) -> None:
    repository = _seed_repository(db_session)
    first = _seed_analysis(db_session, repository.id, issue="First issue")
    second = _seed_analysis(db_session, repository.id, issue="Second issue")

    response = client.get("/api/v1/analysis")

    assert response.status_code == 200
    payload = response.json()
    ids = {item["analysis_run_id"] for item in payload}
    assert {first.id, second.id}.issubset(ids)
    assert payload[0]["repo_name"] == "sample-api"


def test_get_analysis_by_id(client: TestClient, db_session: Session) -> None:
    repository = _seed_repository(db_session)
    analysis = _seed_analysis(db_session, repository.id)
    create_retrieval_result_records(
        db_session,
        analysis_run_id=analysis.id,
        retrieval=RetrievalResult(
            files=[
                RelevantFile(
                    file_path="main.py",
                    score=0.8,
                    reason="Matched route",
                )
            ]
        ),
    )
    create_fix_plan_record(
        db_session,
        analysis_run_id=analysis.id,
        fix_plan=_fix_plan(),
    )

    response = client.get(f"/api/v1/analysis/{analysis.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_run_id"] == analysis.id
    assert payload["repository"]["repo_name"] == "sample-api"
    assert "local_path" not in payload["repository"]
    assert payload["retrieval_results"][0]["file_path"] == "main.py"
    assert payload["fix_plan"]["suspected_issue"] == "The login route fails."


def test_get_missing_analysis_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/analysis/missing-analysis-id")

    assert response.status_code == 404


def test_list_analyses_for_repository(
    client: TestClient,
    db_session: Session,
) -> None:
    repository = _seed_repository(db_session)
    analysis = _seed_analysis(db_session, repository.id)

    response = client.get(f"/api/v1/repositories/{repository.id}/analyses")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["analysis_run_id"] == analysis.id
    assert payload[0]["repository_id"] == repository.id


def test_missing_repository_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/repositories/missing-repository-id/analyses")

    assert response.status_code == 404


def _seed_repository(db: Session):
    return create_repository_record(
        db,
        repo_name="sample-api",
        local_path="/tmp/sample-api",
        branch=None,
        framework="fastapi",
        total_files=3,
    )


def _seed_analysis(
    db: Session,
    repository_id: str,
    *,
    issue: str = "POST /login returns 500",
):
    record = create_analysis_run_record(
        db,
        repository_id=repository_id,
        issue_text=issue,
        status="running",
        detected_framework="fastapi",
    )
    updated = update_analysis_run_status(
        db,
        analysis_run_id=record.id,
        status="success",
        detected_framework="fastapi",
    )
    assert updated is not None
    return updated


def _fix_plan() -> FixPlan:
    return FixPlan(
        suspected_issue="The login route fails.",
        root_cause="The handler raises unexpectedly.",
        files_to_change=[
            {
                "file_path": "main.py",
                "reason": "Update handler",
                "risk": "low",
            }
        ],
        fix_plan=[
            {
                "step": 1,
                "description": "Fix login handler.",
                "target_file": "main.py",
            }
        ],
        validation_plan=[
            {
                "command": "pytest",
                "purpose": "Verify login behavior.",
            }
        ],
        confidence=0.8,
        risk_level="low",
        requires_human_review=False,
        assumptions=[],
    )
