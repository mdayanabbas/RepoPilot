import pytest

from backend.app.agent.provider_factory import ProviderFactory
from backend.app.agent.providers.groq_provider import GroqProvider
from backend.app.agent.providers.lmstudio_provider import LMStudioProvider
from backend.app.core.errors import LLMProviderError
from backend.app.settings import Settings


def _settings(primary: str, fallback: str) -> Settings:
    return Settings(
        PRIMARY_LLM_PROVIDER=primary,
        FALLBACK_LLM_PROVIDER=fallback,
        _env_file=None,
    )


def test_factory_wires_groq_primary_and_lmstudio_fallback() -> None:
    settings = _settings("groq", "lmstudio")

    router = ProviderFactory(settings).create_router()

    assert isinstance(router.primary_provider, GroqProvider)
    assert isinstance(router.fallback_provider, LMStudioProvider)
    assert router.primary_provider.settings is settings
    assert router.fallback_provider.settings is settings


def test_factory_wires_lmstudio_primary_and_groq_fallback() -> None:
    settings = _settings("lmstudio", "groq")

    router = ProviderFactory(settings).create_router()

    assert isinstance(router.primary_provider, LMStudioProvider)
    assert isinstance(router.fallback_provider, GroqProvider)


def test_unknown_provider_raises_provider_error() -> None:
    settings = _settings("unknown-provider", "groq")

    with pytest.raises(LLMProviderError, match="Unknown LLM provider") as exc_info:
        ProviderFactory(settings).create_router()

    assert exc_info.value.details == {"provider": "unknown-provider"}
