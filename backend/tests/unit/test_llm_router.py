from typing import Any

import pytest

from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.agent.router import LLMRouter
from backend.app.core.errors import LLMProviderError
from backend.app.schemas.llm import LLMResponse, LLMUsage


class FakeProvider(BaseLLMProvider):
    def __init__(
        self,
        provider_name: str,
        model_name: str,
        *,
        response: LLMResponse | None = None,
        error: LLMProviderError | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._model_name = model_name
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict | None]] = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        self.calls.append((prompt, response_schema))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _response(provider: str, model: str) -> LLMResponse:
    return LLMResponse(
        provider=provider,
        model=model,
        content={"answer": "ok"},
        raw_response={"id": "fake-response"},
        usage=LLMUsage(prompt_tokens=4, completion_tokens=2),
        latency_ms=1.5,
    )


@pytest.mark.asyncio
async def test_router_uses_primary_provider_first() -> None:
    primary = FakeProvider(
        "primary",
        "model-a",
        response=_response("primary", "model-a"),
    )
    fallback = FakeProvider(
        "fallback",
        "model-b",
        response=_response("fallback", "model-b"),
    )
    schema: dict[str, Any] = {"type": "object"}

    result = await LLMRouter(primary, fallback).generate_json("prompt", schema)

    assert result.provider_used == "primary"
    assert result.response.content == {"answer": "ok"}
    assert [attempt.provider for attempt in result.attempts] == ["primary"]
    assert result.attempts[0].success is True
    assert primary.calls == [("prompt", schema)]
    assert fallback.calls == []


@pytest.mark.asyncio
async def test_router_falls_back_after_provider_error() -> None:
    primary = FakeProvider(
        "primary",
        "model-a",
        error=LLMProviderError("primary unavailable"),
    )
    fallback = FakeProvider(
        "fallback",
        "model-b",
        response=_response("fallback", "model-b"),
    )

    result = await LLMRouter(primary, fallback).generate_json("prompt")

    assert result.provider_used == "fallback"
    assert [attempt.provider for attempt in result.attempts] == [
        "primary",
        "fallback",
    ]
    assert [attempt.success for attempt in result.attempts] == [False, True]
    assert result.attempts[0].error == "primary unavailable"


@pytest.mark.asyncio
async def test_router_raises_when_both_providers_fail() -> None:
    primary = FakeProvider(
        "primary",
        "model-a",
        error=LLMProviderError("primary unavailable"),
    )
    fallback = FakeProvider(
        "fallback",
        "model-b",
        error=LLMProviderError("fallback unavailable"),
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await LLMRouter(primary, fallback).generate_json("prompt")

    attempts = exc_info.value.details["attempts"]
    assert [attempt["provider"] for attempt in attempts] == ["primary", "fallback"]
    assert all(attempt["success"] is False for attempt in attempts)


@pytest.mark.asyncio
async def test_router_does_not_hide_unexpected_errors() -> None:
    class BrokenProvider(FakeProvider):
        async def generate_json(
            self,
            prompt: str,
            response_schema: dict | None = None,
        ) -> LLMResponse:
            raise RuntimeError("programming error")

    primary = BrokenProvider("primary", "model-a")
    fallback = FakeProvider(
        "fallback",
        "model-b",
        response=_response("fallback", "model-b"),
    )

    with pytest.raises(RuntimeError, match="programming error"):
        await LLMRouter(primary, fallback).generate_json("prompt")

    assert fallback.calls == []
