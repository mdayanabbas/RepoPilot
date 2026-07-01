from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.base import Base
from backend.app.database.models import ArchitectureGraphRecord, TraceEventRecord
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import AnalyzeRepositoryRequest
from backend.app.schemas.llm import LLMResponse, LLMRouterResponse
from backend.app.schemas.repository import RepositorySourceType
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow


class FakeLLMService:
    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMRouterResponse:
        del prompt, response_schema
        return LLMRouterResponse(
            provider_used="fake",
            response=LLMResponse(
                provider="fake",
                model="fake-model",
                content=_valid_fix_plan_payload(),
                latency_ms=1.0,
            ),
        )


class FailingArchitectureService:
    def build_graph(self, **kwargs: Any) -> None:
        del kwargs
        raise RuntimeError("graph build failed")

    def export_mermaid(self, graph: object) -> str:
        del graph
        return ""


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
async def test_architecture_graph_record_is_persisted_after_successful_analysis(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    result = await _workflow(tmp_path, db_session).run(
        AnalyzeRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source),
            branch=None,
            issue="POST /api/login fails after auth change",
        )
    )

    record = db_session.scalars(select(ArchitectureGraphRecord)).one()
    assert record.analysis_run_id == result.analysis_run_id
    assert record.framework == "fastapi"


@pytest.mark.asyncio
async def test_persisted_graph_includes_nodes_and_edges(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    await _workflow(tmp_path, db_session).run(
        AnalyzeRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source),
            branch=None,
            issue="POST /api/login fails after auth change",
        )
    )

    record = db_session.scalars(select(ArchitectureGraphRecord)).one()
    assert record.graph_json["nodes"]
    assert record.graph_json["edges"]
    assert record.summary_json["route_count"] == 1


@pytest.mark.asyncio
async def test_persisted_mermaid_starts_with_graph_td(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    await _workflow(tmp_path, db_session).run(
        AnalyzeRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source),
            branch=None,
            issue="POST /api/login fails after auth change",
        )
    )

    record = db_session.scalars(select(ArchitectureGraphRecord)).one()
    assert record.mermaid.startswith("graph TD")


@pytest.mark.asyncio
async def test_architecture_graph_failure_does_not_fail_analysis(
    tmp_path: Path,
    db_session: Session,
) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)

    result = await _workflow(
        tmp_path,
        db_session,
        architecture_service=FailingArchitectureService(),
    ).run(
        AnalyzeRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source),
            branch=None,
            issue="POST /api/login fails after auth change",
        )
    )

    event = db_session.scalars(
        select(TraceEventRecord).where(
            TraceEventRecord.step_name == "build_architecture_graph"
        )
    ).one()
    assert result.analysis_run_id is not None
    assert event.status == "failed"
    assert event.metadata_json["error_message"] == "graph build failed"


def _workflow(
    tmp_path: Path,
    db: Session,
    *,
    architecture_service: Any | None = None,
) -> AnalyzeRepositoryWorkflow:
    return AnalyzeRepositoryWorkflow(
        FakeLLMService(),
        repository_service=RepositoryService(tmp_path / "workspaces"),
        db=db,
        architecture_service=architecture_service,
    )


def _write_fastapi_repo(path: Path) -> None:
    routes = path / "routes"
    services = path / "services"
    routes.mkdir(parents=True)
    services.mkdir()
    (path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (path / "main.py").write_text(
        """from fastapi import FastAPI
from routes.auth import router

app = FastAPI()
app.include_router(router)
""",
        encoding="utf-8",
    )
    (routes / "auth.py").write_text(
        """from fastapi import APIRouter
from services.auth_service import authenticate

router = APIRouter(prefix="/api")


@router.post("/login")
def login():
    return authenticate()
""",
        encoding="utf-8",
    )
    (services / "auth_service.py").write_text(
        """def authenticate():
    return {"ok": True}
""",
        encoding="utf-8",
    )


def _valid_fix_plan_payload() -> dict[str, Any]:
    return {
        "suspected_issue": "The login route fails for the reported request.",
        "root_cause": "The handler has a framework-specific bug.",
        "files_to_change": [
            {
                "file_path": "routes/auth.py",
                "reason": "Update the route handler.",
                "risk": "low",
            }
        ],
        "fix_plan": [
            {
                "step": 1,
                "description": "Adjust the handler logic.",
                "target_file": "routes/auth.py",
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
