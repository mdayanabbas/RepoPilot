import json
import re
from typing import Any

from backend.app.core.errors import LLMProviderError

FENCED_JSON_PATTERN = re.compile(
    r"^\s*```(?:json|JSON)?\s*(?P<content>.*?)\s*```\s*$",
    re.DOTALL,
)


def strip_markdown_code_fence(content: str) -> str:
    match = FENCED_JSON_PATTERN.match(content)
    if match is None:
        return content.strip()
    return match.group("content").strip()


def parse_json_object_content(content: str, provider_name: str) -> dict[str, Any]:
    stripped = strip_markdown_code_fence(content)
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError as exc:
        truncated_content = _truncate(content)
        raise LLMProviderError(
            f"{provider_name} returned invalid JSON content: {truncated_content}",
            details={"raw_content": truncated_content},
        ) from exc
    if not isinstance(decoded, dict):
        truncated_content = _truncate(content)
        raise LLMProviderError(
            f"{provider_name} returned JSON content that is not an object: "
            f"{truncated_content}",
            details={"raw_content": truncated_content},
        )
    return decoded


def _truncate(value: str, limit: int = 800) -> str:
    normalized = value.replace("\r", "\\r").replace("\n", "\\n")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
