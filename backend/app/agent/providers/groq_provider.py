import json
from time import perf_counter
from typing import Any

import httpx

from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.core.errors import LLMProviderError
from backend.app.schemas.llm import LLMResponse, LLMUsage
from backend.app.settings import Settings

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 30.0
JSON_SYSTEM_MESSAGE = "Return valid JSON only."


class GroqProvider(BaseLLMProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.settings = settings
        self.client = client
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self.settings.GROQ_MODEL

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        api_key = self.settings.GROQ_API_KEY
        if not api_key:
            raise LLMProviderError("Groq API key is not configured")

        payload = _build_payload(self.model_name, prompt, response_schema)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        started_at = perf_counter()

        try:
            response = await self._post(payload, headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError("Groq request timed out") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError("Groq request failed") from exc

        latency_ms = max((perf_counter() - started_at) * 1000, 0.0)
        if response.status_code != httpx.codes.OK:
            raise LLMProviderError(
                "Groq returned a non-success response",
                details={
                    "status_code": response.status_code,
                    "response_body": response.text,
                },
            )

        raw_response = _decode_response(response)
        content_text, usage = _extract_response(raw_response)
        content = _decode_content(content_text)

        return LLMResponse(
            provider=self.provider_name,
            model=self.model_name,
            content=content,
            raw_response=raw_response,
            usage=usage,
            latency_ms=latency_ms,
        )

    async def _post(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
            )


def _build_payload(
    model_name: str,
    prompt: str,
    response_schema: dict | None,
) -> dict[str, Any]:
    system_message = JSON_SYSTEM_MESSAGE
    if response_schema is not None:
        serialized_schema = json.dumps(response_schema, sort_keys=True)
        system_message = f"{system_message} Match this JSON schema: {serialized_schema}"

    return {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    }


def _decode_response(response: httpx.Response) -> dict[str, Any]:
    try:
        decoded = response.json()
    except ValueError as exc:
        raise LLMProviderError("Groq returned a malformed response") from exc
    if not isinstance(decoded, dict):
        raise LLMProviderError("Groq returned a malformed response")
    return decoded


def _extract_response(
    raw_response: dict[str, Any],
) -> tuple[str, LLMUsage]:
    try:
        content = raw_response["choices"][0]["message"]["content"]
        raw_usage = raw_response.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )
    except (IndexError, KeyError, TypeError, AttributeError, ValueError) as exc:
        raise LLMProviderError("Groq returned a malformed response") from exc
    if not isinstance(content, str):
        raise LLMProviderError("Groq returned a malformed response")
    return content, usage


def _decode_content(content: str) -> dict[str, Any]:
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("Groq returned invalid JSON content") from exc
    if not isinstance(decoded, dict):
        raise LLMProviderError("Groq returned invalid JSON content")
    return decoded
