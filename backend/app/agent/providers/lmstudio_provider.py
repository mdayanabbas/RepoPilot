import json
from time import perf_counter
from typing import Any

import httpx

from backend.app.agent.response_parser import parse_json_object_content
from backend.app.agent.providers.base import BaseLLMProvider
from backend.app.core.errors import LLMProviderError
from backend.app.schemas.llm import LLMResponse, LLMUsage
from backend.app.settings import Settings

DEFAULT_TIMEOUT_SECONDS = 30.0
JSON_SYSTEM_MESSAGE = "Return valid JSON only."


class LMStudioProvider(BaseLLMProvider):
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
        return "lmstudio"

    @property
    def model_name(self) -> str:
        return self.settings.LMSTUDIO_MODEL

    @property
    def chat_completions_url(self) -> str:
        base_url = self.settings.LMSTUDIO_BASE_URL.rstrip("/")
        return f"{base_url}/chat/completions"

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMResponse:
        payload = _build_payload(self.model_name, prompt, response_schema)
        started_at = perf_counter()

        try:
            response = await self._post(payload)
        except httpx.TimeoutException as exc:
            raise LLMProviderError("LM Studio request timed out") from exc
        except httpx.ConnectError as exc:
            raise LLMProviderError("LM Studio server is unavailable") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError("LM Studio request failed") from exc

        latency_ms = max((perf_counter() - started_at) * 1000, 0.0)
        if response.status_code != httpx.codes.OK:
            raise LLMProviderError(
                "LM Studio returned a non-success response",
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

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(
                self.chat_completions_url,
                json=payload,
                timeout=self.timeout_seconds,
            )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await client.post(self.chat_completions_url, json=payload)


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
        raise LLMProviderError("LM Studio returned a malformed response") from exc
    if not isinstance(decoded, dict):
        raise LLMProviderError("LM Studio returned a malformed response")
    return decoded


def _extract_response(
    raw_response: dict[str, Any],
) -> tuple[str, LLMUsage]:
    try:
        content = raw_response["choices"][0]["message"]["content"]
        raw_usage = raw_response.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )
    except (IndexError, KeyError, TypeError, AttributeError, ValueError) as exc:
        raise LLMProviderError("LM Studio returned a malformed response") from exc
    if not isinstance(content, str):
        raise LLMProviderError("LM Studio returned a malformed response")
    return content, usage


def _decode_content(content: str) -> dict[str, Any]:
    return parse_json_object_content(content, "LM Studio")
