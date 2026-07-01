from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.errors import LLMProviderError
from backend.app.database.base import Base
from backend.app.database.models import (
    AnalysisRunRecord,
    FixPlanRecord,
    ModelCallRecord,
    RepositoryRecord,
    RetrievalResultRecord,
    ToolCallRecord,
    TraceEventRecord,
)
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import AnalyzeRepositoryRequest
from backend.app.schemas.llm import LLMResponse, LLMRouterResponse
from backend.app.schemas.repository import RepositorySourceType
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow


class FakeLLMService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMRouterResponse:
        del prompt, response_schema
        if self.fail:
            raise LLMProviderError("fake provider failed")
        return LLMRouterResponse(
            provider_used="fake",
            response=LLMResponse(
                provider="fake",
                model="fake-model",
                content=_valid_fix_plan_payload(),
                latency_ms=1.0,
            ),
        )


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_successful_analysis_persists_records(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    result = await _workflow(tmp_path, db_session).run(
        _request(source, "POST /login returns 500")
    )

    repository = _one(db_session, RepositoryRecord)
    analysis_run = _one(db_session, AnalysisRunRecord)

    assert repository.repo_name == "fastapi_repo"
    assert analysis_run.id == result.analysis_run_id
    assert analysis_run.repository_id == repository.id
    assert analysis_run.status == "success"
    assert analysis_run.detected_framework == "fastapi"
    assert _count(db_session, TraceEventRecord) > 0
    assert _count(db_session, ToolCallRecord) > 0
    assert _count(db_session, ModelCallRecord) == 1
    assert _count(db_session, RetrievalResultRecord) > 0
    assert _count(db_session, FixPlanRecord) == 1


@pytest.mark.asyncio
async def test_failed_analysis_updates_status_to_failed(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    with pytest.raises(LLMProviderError):
        await _workflow(tmp_path, db_session, fail=True).run(
            _request(source, "POST /login returns 500")
        )

    analysis_run = _one(db_session, AnalysisRunRecord)
    assert analysis_run.status == "failed"
    assert analysis_run.error_message
    assert _count(db_session, RepositoryRecord) == 1
    assert _count(db_session, TraceEventRecord) > 0
    assert _count(db_session, RetrievalResultRecord) > 0
    assert _count(db_session, FixPlanRecord) == 0


def _workflow(
    tmp_path: Path,
    db: Session,
    *,
    fail: bool = False,
) -> AnalyzeRepositoryWorkflow:
    return AnalyzeRepositoryWorkflow(
        FakeLLMService(fail=fail),
        repository_service=RepositoryService(tmp_path / "workspaces"),
        db=db,
    )


def _request(source: Path, issue: str) -> AnalyzeRepositoryRequest:
    return AnalyzeRepositoryRequest(
        source_type=RepositorySourceType.local,
        source=str(source),
        branch=None,
        issue=issue,
    )


def _write_fastapi_repo(path: Path) -> None:
    path.mkdir()
    (path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (path / "main.py").write_text(
        """from fastapi import FastAPI

app = FastAPI()


@app.post("/login")
def login():
    return {"ok": True}
""",
        encoding="utf-8",
    )


def _valid_fix_plan_payload() -> dict[str, Any]:
    return {
        "suspected_issue": "The route fails for the reported request.",
        "root_cause": "The handler has a framework-specific bug.",
        "files_to_change": [
            {
                "file_path": "main.py",
                "reason": "Update the route handler.",
                "risk": "low",
            }
        ],
        "fix_plan": [
            {
                "step": 1,
                "description": "Adjust the handler logic.",
                "target_file": "main.py",
            }
        ],
        "validation_plan": [
            {
                "command": "pytest",
                "purpose": "Verify the application behavior.",
            }
        ],
        "confidence": 0.8,
        "risk_level": "low",
        "requires_human_review": False,
        "assumptions": ["The failing route is covered by tests."],
    }


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _one(db: Session, model: type):
    return db.scalars(select(model)).one()
