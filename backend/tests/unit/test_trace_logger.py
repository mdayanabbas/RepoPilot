from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import AnalyzeRepositoryRequest
from backend.app.schemas.llm import LLMResponse, LLMRouterResponse
from backend.app.schemas.repository import RepositorySourceType
from backend.app.tracing.service import TraceService
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


def test_start_run_creates_run_id() -> None:
    trace_service = TraceService()

    context = trace_service.start_run({"workflow": "test"})

    assert context.run_id
    assert context.metadata == {"workflow": "test"}


def test_log_event_stores_event() -> None:
    trace_service = TraceService()
    context = trace_service.start_run()

    trace_service.log_event(
        context,
        step_name="scan_repository",
        status="success",
        duration_ms=2.5,
        metadata={"files": 3},
    )

    trace = trace_service.get_trace(context.run_id)
    assert len(trace.events) == 1
    assert trace.events[0].step_name == "scan_repository"
    assert trace.events[0].metadata == {"files": 3}


def test_get_trace_returns_events_ordered_by_created_at() -> None:
    trace_service = TraceService()
    context = trace_service.start_run()
    first = trace_service.log_event(
        context,
        step_name="first",
        status="success",
        duration_ms=1.0,
    )
    second = trace_service.log_event(
        context,
        step_name="second",
        status="success",
        duration_ms=1.0,
    )
    first.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second.created_at = first.created_at + timedelta(seconds=1)
    trace_service._events[context.run_id] = [second, first]

    trace = trace_service.get_trace(context.run_id)

    assert [event.step_name for event in trace.events] == ["first", "second"]


def test_failed_event_stores_error_message() -> None:
    trace_service = TraceService()
    context = trace_service.start_run()

    trace_service.log_event(
        context,
        step_name="load_repository",
        status="failed",
        duration_ms=1.0,
        error_message="Local repository path does not exist",
    )

    trace = trace_service.get_trace(context.run_id)
    assert trace.events[0].status == "failed"
    assert trace.events[0].error_message == "Local repository path does not exist"


@pytest.mark.asyncio
async def test_analysis_workflow_result_includes_run_id(tmp_path: Path) -> None:
    source = tmp_path / "fastapi_repo"
    _write_fastapi_repo(source)
    trace_service = TraceService()
    workflow = AnalyzeRepositoryWorkflow(
        FakeLLMService(),
        repository_service=RepositoryService(tmp_path / "workspaces"),
        trace_service=trace_service,
    )

    result = await workflow.run(
        AnalyzeRepositoryRequest(
            source_type=RepositorySourceType.local,
            source=str(source),
            branch=None,
            issue="POST /login returns 500",
        )
    )

    assert result.run_id
    assert trace_service.get_trace(result.run_id).run_id == result.run_id


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
