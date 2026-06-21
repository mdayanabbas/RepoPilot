import json

import httpx
import pytest

from backend.app.agent.providers.lmstudio_provider import LMStudioProvider
from backend.app.core.errors import LLMProviderError
from backend.app.settings import Settings

LMSTUDIO_CHAT_URL = "http://localhost:1234/v1/chat/completions"


def _settings() -> Settings:
    return Settings(
        LMSTUDIO_BASE_URL="http://localhost:1234/v1/",
        LMSTUDIO_MODEL="test-local-model",
        _env_file=None,
    )


def _client(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_generate_json_returns_parsed_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LMSTUDIO_CHAT_URL
        payload = json.loads(request.content)
        assert payload["model"] == "test-local-model"
        assert payload["messages"][0]["role"] == "system"
        assert "Return valid JSON only" in payload["messages"][0]["content"]
        assert payload["messages"][1] == {
            "role": "user",
            "content": "diagnose locally",
        }
        return httpx.Response(
            200,
            json={
                "id": "local-completion-1",
                "choices": [{"message": {"content": '{"cause": "bad route"}'}}],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 3,
                    "total_tokens": 11,
                },
            },
        )

    async with _client(httpx.MockTransport(handler)) as client:
        response = await LMStudioProvider(
            _settings(),
            client=client,
        ).generate_json("diagnose locally", {"type": "object"})

    assert response.provider == "lmstudio"
    assert response.model == "test-local-model"
    assert response.content == {"cause": "bad route"}
    assert response.raw_response["id"] == "local-completion-1"
    assert response.usage.total_tokens == 11
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_server_unavailable_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with _client(httpx.MockTransport(handler)) as client:
        provider = LMStudioProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError, match="server is unavailable"):
            await provider.generate_json("prompt")


@pytest.mark.asyncio
async def test_non_200_response_raises_provider_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, text="model is loading")
    )

    async with _client(transport) as client:
        provider = LMStudioProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_json("prompt")

    assert exc_info.value.details["status_code"] == 503
    assert exc_info.value.details["response_body"] == "model is loading"


@pytest.mark.asyncio
async def test_timeout_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with _client(httpx.MockTransport(handler)) as client:
        provider = LMStudioProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError, match="timed out"):
            await provider.generate_json("prompt")


@pytest.mark.asyncio
async def test_invalid_json_content_raises_provider_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not JSON"}}]},
        )
    )

    async with _client(transport) as client:
        provider = LMStudioProvider(_settings(), client=client)
        with pytest.raises(LLMProviderError, match="invalid JSON"):
            await provider.generate_json("prompt")
