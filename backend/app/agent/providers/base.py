from abc import ABC, abstractmethod

from backend.app.schemas.llm import LLMResponse


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable name used to identify the provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used by this provider."""

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        """Generate and parse one JSON response."""
