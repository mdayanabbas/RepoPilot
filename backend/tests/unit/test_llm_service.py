import pytest

from backend.app.agent.provider_factory import ProviderFactory
from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.agent.service import LLMService
from backend.app.core.errors import LLMProviderError
from backend.app.schemas.llm import LLMResponse
from backend.app.settings import Settings


class FakeProvider(BaseLLMProvider):
    def __init__(self, name: str, *, should_fail: bool = False) -> None:
        self.name = name
        self.should_fail = should_fail
        self.calls: list[tuple[str, dict | None]] = []

    @property
    def provider_name(self) -> str:
        return self.name

    @property
    def model_name(self) -> str:
        return f"{self.name}-model"

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        self.calls.append((prompt, response_schema))
        if self.should_fail:
            raise LLMProviderError(f"{self.name} failed")
        return LLMResponse(
            provider=self.provider_name,
            model=self.model_name,
            content={"provider": self.provider_name},
            latency_ms=1.0,
        )


def _settings() -> Settings:
    return Settings(
        PRIMARY_LLM_PROVIDER="primary",
        FALLBACK_LLM_PROVIDER="fallback",
        _env_file=None,
    )


def _patch_providers(
    monkeypatch: pytest.MonkeyPatch,
    primary: FakeProvider,
    fallback: FakeProvider,
) -> None:
    providers = {"primary": primary, "fallback": fallback}

    def create_fake_provider(
        factory: ProviderFactory,
        name: str,
    ) -> BaseLLMProvider:
        del factory
        return providers[name]

    monkeypatch.setattr(
        ProviderFactory,
        "create_provider",
        create_fake_provider,
    )


@pytest.mark.asyncio
async def test_service_returns_primary_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = FakeProvider("primary")
    fallback = FakeProvider("fallback")
    _patch_providers(monkeypatch, primary, fallback)
    service = LLMService(_settings())
    schema = {"type": "object"}

    result = await service.generate_json("prompt", schema)

    assert result.provider_used == "primary"
    assert result.response.content == {"provider": "primary"}
    assert primary.calls == [("prompt", schema)]
    assert fallback.calls == []


@pytest.mark.asyncio
async def test_service_returns_fallback_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = FakeProvider("primary", should_fail=True)
    fallback = FakeProvider("fallback")
    _patch_providers(monkeypatch, primary, fallback)
    service = LLMService(_settings())

    result = await service.generate_json("prompt")

    assert result.provider_used == "fallback"
    assert [attempt.success for attempt in result.attempts] == [False, True]
    assert primary.calls == [("prompt", None)]
    assert fallback.calls == [("prompt", None)]


@pytest.mark.asyncio
async def test_service_raises_when_both_providers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = FakeProvider("primary", should_fail=True)
    fallback = FakeProvider("fallback", should_fail=True)
    _patch_providers(monkeypatch, primary, fallback)
    service = LLMService(_settings())

    with pytest.raises(LLMProviderError) as exc_info:
        await service.generate_json("prompt")

    attempts = exc_info.value.details["attempts"]
    assert [attempt["provider"] for attempt in attempts] == [
        "primary",
        "fallback",
    ]
