from time import perf_counter

from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.core.errors import LLMProviderError
from backend.app.schemas.llm import (
    LLMProviderAttempt,
    LLMResponse,
    LLMRouterResponse,
)


class LLMRouter:
    def __init__(
        self,
        primary_provider: BaseLLMProvider,
        fallback_provider: BaseLLMProvider,
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMRouterResponse:
        attempts: list[LLMProviderAttempt] = []

        for provider in (self.primary_provider, self.fallback_provider):
            try:
                response = await self._attempt(
                    provider,
                    prompt,
                    response_schema,
                    attempts,
                )
            except LLMProviderError:
                continue

            return LLMRouterResponse(
                provider_used=provider.provider_name,
                response=response,
                attempts=attempts,
            )

        raise LLMProviderError(
            "All LLM providers failed",
            details={
                "attempts": [attempt.model_dump() for attempt in attempts],
            },
        )

    async def _attempt(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        response_schema: dict | None,
        attempts: list[LLMProviderAttempt],
    ) -> LLMResponse:
        started_at = perf_counter()
        try:
            response = await provider.generate_json(prompt, response_schema)
        except LLMProviderError as exc:
            attempts.append(
                LLMProviderAttempt(
                    provider=provider.provider_name,
                    model=provider.model_name,
                    success=False,
                    latency_ms=_elapsed_ms(started_at),
                    error=str(exc),
                )
            )
            raise

        attempts.append(
            LLMProviderAttempt(
                provider=provider.provider_name,
                model=provider.model_name,
                success=True,
                latency_ms=_elapsed_ms(started_at),
            )
        )
        return response


def _elapsed_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
