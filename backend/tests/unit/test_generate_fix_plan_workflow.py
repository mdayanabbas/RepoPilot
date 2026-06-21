from typing import Any

import pytest

from backend.app.core.errors import LLMProviderError, SchemaValidationError
from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.llm import (
    LLMProviderAttempt,
    LLMResponse,
    LLMRouterResponse,
    LLMUsage,
)
from backend.app.schemas.retrieval import StructuredContext
from backend.app.workflows.generate_fix_plan_workflow import (
    GenerateFixPlanWorkflow,
)


class FakeLLMService:
    def __init__(
        self,
        response: LLMRouterResponse | None = None,
        error: LLMProviderError | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict | None]] = []

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMRouterResponse:
        self.calls.append((prompt, response_schema))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _context() -> StructuredContext:
    return StructuredContext(
        issue="POST /login returns 500",
        framework=SupportedFramework.fastapi,
        selected_files=[],
        total_context_chars=0,
    )


def _valid_payload() -> dict[str, Any]:
    return {
        "suspected_issue": "The login handler fails.",
        "root_cause": "The handler imports an outdated service.",
        "files_to_change": [
            {
                "file_path": "routes/auth.py",
                "reason": "Correct the import.",
                "risk": "low",
            }
        ],
        "fix_plan": [
            {
                "step": 1,
                "description": "Update the service import.",
                "target_file": "routes/auth.py",
            }
        ],
        "validation_plan": [
            {
                "command": "pytest tests/test_auth.py",
                "purpose": "Verify login behavior.",
            }
        ],
        "confidence": 0.9,
        "risk_level": "low",
        "requires_human_review": False,
        "assumptions": ["The service interface is unchanged."],
    }


def _router_response(payload: dict[str, Any]) -> LLMRouterResponse:
    return LLMRouterResponse(
        provider_used="groq",
        response=LLMResponse(
            provider="groq",
            model="test-model",
            content=payload,
            raw_response={"id": "response-1"},
            usage=LLMUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
            latency_ms=12.5,
        ),
        attempts=[
            LLMProviderAttempt(
                provider="groq",
                model="test-model",
                success=True,
                latency_ms=12.5,
            )
        ],
    )


@pytest.mark.asyncio
async def test_successful_fix_plan_generation_returns_validated_model() -> None:
    service = FakeLLMService(response=_router_response(_valid_payload()))

    result = await GenerateFixPlanWorkflow(service).run(_context())

    assert isinstance(result, FixPlan)
    assert result.root_cause == "The handler imports an outdated service."
    assert service.calls[0][1] == FixPlan.model_json_schema()
    assert "POST /login returns 500" in service.calls[0][0]


@pytest.mark.asyncio
async def test_workflow_captures_provider_metadata() -> None:
    service = FakeLLMService(response=_router_response(_valid_payload()))

    result = await GenerateFixPlanWorkflow(service).run(_context())

    assert result.provider_metadata is not None
    assert result.provider_metadata.provider_used == "groq"
    assert result.provider_metadata.model == "test-model"
    assert result.provider_metadata.usage.total_tokens == 150
    assert result.provider_metadata.attempts[0].success is True


@pytest.mark.asyncio
async def test_invalid_llm_payload_raises_schema_validation_error() -> None:
    invalid_payload = _valid_payload()
    del invalid_payload["root_cause"]
    service = FakeLLMService(response=_router_response(invalid_payload))

    with pytest.raises(SchemaValidationError):
        await GenerateFixPlanWorkflow(service).run(_context())


@pytest.mark.asyncio
async def test_llm_provider_failure_is_propagated() -> None:
    service = FakeLLMService(error=LLMProviderError("providers unavailable"))

    with pytest.raises(LLMProviderError, match="providers unavailable"):
        await GenerateFixPlanWorkflow(service).run(_context())
