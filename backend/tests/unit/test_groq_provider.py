import json

import httpx
import pytest

from backend.app.agent.providers.groq_provider import (
    GROQ_CHAT_COMPLETIONS_URL,
    GroqProvider,
)
from backend.app.core.errors import LLMProviderError
from backend.app.settings import Settings


def _settings(api_key: str | None = "test-key") -> Settings:
    return Settings(
        GROQ_API_KEY=api_key,
        GROQ_MODEL="test-model",
        _env_file=None,
    )


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_generate_json_returns_parsed_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == GROQ_CHAT_COMPLETIONS_URL
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model"
        assert payload["messages"][0]["role"] == "system"
        assert "Return valid JSON only" in payload["messages"][0]["content"]
        assert payload["messages"][1] == {
            "role": "user",
            "content": "diagnose this",
        }
        return httpx.Response(
            200,
            json={
                "id": "completion-1",
                "choices": [{"message": {"content": '{"cause": "bad import"}'}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            },
        )

    async with _client(httpx.MockTransport(handler)) as client:
        response = await GroqProvider(
            _settings(),
            client=client,
        ).generate_json("diagnose this", {"type": "object"})

    assert response.provider == "groq"
    assert response.model == "test-model"
    assert response.content == {"cause": "bad import"}
    assert response.raw_response["id"] == "completion-1"
    assert response.usage.total_tokens == 14
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_generate_json_parses_fenced_json_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"status": "ok"}\n```',
                        }
                    }
                ],
                "usage": {},
            },
        )
    )

    async with _client(transport) as client:
        response = await GroqProvider(_settings(), client=client).generate_json("prompt")

    assert response.content == {"status": "ok"}


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    provider = GroqProvider(_settings(api_key=None))

    with pytest.raises(LLMProviderError, match="API key"):
        await provider.generate_json("prompt")


@pytest.mark.asyncio
async def test_non_200_response_raises_provider_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, text="rate limited")
    )

    async with _client(transport) as client:
        provider = GroqProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_json("prompt")

    assert exc_info.value.details["status_code"] == 429
    assert exc_info.value.details["response_body"] == "rate limited"


@pytest.mark.asyncio
async def test_timeout_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with _client(httpx.MockTransport(handler)) as client:
        provider = GroqProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError, match="timed out"):
            await provider.generate_json("prompt")


@pytest.mark.asyncio
async def test_invalid_json_content_raises_provider_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "this is not JSON"}}]},
        )
    )

    async with _client(transport) as client:
        provider = GroqProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError, match="invalid JSON"):
            await provider.generate_json("prompt")
