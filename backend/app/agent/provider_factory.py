from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.agent.providers.groq_provider import GroqProvider
from backend.app.agent.providers.lmstudio_provider import LMStudioProvider
from backend.app.agent.router import LLMRouter
from backend.app.core.errors import LLMProviderError
from backend.app.settings import Settings


class ProviderFactory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_provider(self, provider_name: str) -> BaseLLMProvider:
        normalized_name = provider_name.strip().lower()
        if normalized_name == "groq":
            return GroqProvider(self.settings)
        if normalized_name == "lmstudio":
            return LMStudioProvider(self.settings)
        raise LLMProviderError(
            f"Unknown LLM provider: {provider_name}",
            details={"provider": provider_name},
        )

    def create_router(self) -> LLMRouter:
        primary = self.create_provider(self.settings.PRIMARY_LLM_PROVIDER)
        fallback = self.create_provider(self.settings.FALLBACK_LLM_PROVIDER)
        return LLMRouter(
            primary_provider=primary,
            fallback_provider=fallback,
        )


LLMProviderFactory = ProviderFactory


def create_provider(
    provider_name: str,
    settings: Settings,
) -> BaseLLMProvider:
    return ProviderFactory(settings).create_provider(provider_name)


def create_llm_router(settings: Settings) -> LLMRouter:
    return ProviderFactory(settings).create_router()
