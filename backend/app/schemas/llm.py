from typing import Any

from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: dict[str, Any]
    raw_response: Any = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency_ms: float = Field(ge=0.0)


class LLMProviderAttempt(BaseModel):
    provider: str
    model: str
    success: bool
    latency_ms: float = Field(ge=0.0)
    error: str | None = None


class LLMRouterResponse(BaseModel):
    provider_used: str
    response: LLMResponse
    attempts: list[LLMProviderAttempt] = Field(default_factory=list)
