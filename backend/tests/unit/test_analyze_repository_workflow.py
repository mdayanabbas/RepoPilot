from pathlib import Path
from typing import Any

import pytest

from backend.app.core.errors import RepositoryError
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import AnalyzeRepositoryRequest
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.llm import LLMResponse, LLMRouterResponse
from backend.app.schemas.repository import RepositorySourceType
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow


class FakeLLMService:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or _valid_fix_plan_payload()
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMRouterResponse:
        self.calls.append((prompt, response_schema))
        return LLMRouterResponse(
            provider_used="fake",
            response=LLMResponse(
                provider="fake",
                model="fake-model",
                content=self.payload,
                latency_ms=1.0,
            ),
        )


def _request(source: Path, issue: str) -> AnalyzeRepositoryRequest:
    return AnalyzeRepositoryRequest(
        source_type=RepositorySourceType.local,
        source=str(source),
        branch=None,
        issue=issue,
    )


def _workflow(tmp_path: Path, llm_service: FakeLLMService) -> AnalyzeRepositoryWorkflow:
    return AnalyzeRepositoryWorkflow(
        llm_service,
        repository_service=RepositoryService(tmp_path / "workspaces"),
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


def _write_flask_repo(path: Path) -> None:
    path.mkdir()
    (path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    (path / "app.py").write_text(
        """from flask import Flask

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    return {"ok": True}
""",
        encoding="utf-8",
    )


def _write_unknown_repo(path: Path) -> None:
    path.mkdir()
    (path / "main.py").write_text(
        """def login():
    return {"ok": True}
""",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_fastapi_repo_analysis_success(tmp_path: Path) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)
    llm_service = FakeLLMService()

    result = await _workflow(tmp_path, llm_service).run(
        _request(source, "POST /login returns 500")
    )

    assert result.framework.framework == SupportedFramework.fastapi
    assert result.extracted_routes.routes[0].path == "/login"
    assert result.extracted_routes.routes[0].method == "POST"
    assert result.retrieval.files
    assert result.context_summary.selected_file_count > 0
    assert isinstance(result.fix_plan, FixPlan)
    assert len(llm_service.calls) == 1


@pytest.mark.asyncio
async def test_flask_repo_analysis_success(tmp_path: Path) -> None:
    source = tmp_path / "flask_repo"
    _write_flask_repo(source)
    llm_service = FakeLLMService()

    result = await _workflow(tmp_path, llm_service).run(
        _request(source, "POST /login returns 500")
    )

    assert result.framework.framework == SupportedFramework.flask
    assert result.extracted_routes.routes[0].path == "/login"
    assert result.extracted_routes.routes[0].method == "POST"
    assert result.retrieval.files
    assert isinstance(result.fix_plan, FixPlan)
    assert len(llm_service.calls) == 1


@pytest.mark.asyncio
async def test_unknown_framework_skips_llm(tmp_path: Path) -> None:
    source = tmp_path / "unknown_repo"
    _write_unknown_repo(source)
    llm_service = FakeLLMService()

    result = await _workflow(tmp_path, llm_service).run(
        _request(source, "POST /login returns 500")
    )

    assert result.framework.framework == SupportedFramework.unknown
    assert result.fix_plan is None
    assert result.extracted_routes.routes == []
    assert llm_service.calls == []


@pytest.mark.asyncio
async def test_invalid_local_repo_path_raises_repository_error(tmp_path: Path) -> None:
    llm_service = FakeLLMService()
    missing = tmp_path / "missing"

    with pytest.raises(RepositoryError):
        await _workflow(tmp_path, llm_service).run(
            _request(missing, "POST /login returns 500")
        )

    assert llm_service.calls == []
