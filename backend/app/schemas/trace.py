from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TraceStatus = Literal["success", "failed", "skipped"]


class TraceEvent(BaseModel):
    run_id: str
    step_name: str
    status: TraceStatus
    duration_ms: float = Field(ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime


class ToolCallEvent(TraceEvent):
    tool_name: str
    input_metadata: dict[str, Any] = Field(default_factory=dict)
    output_metadata: dict[str, Any] = Field(default_factory=dict)


class ModelCallEvent(TraceEvent):
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class TraceSummary(BaseModel):
    run_id: str
    started_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[TraceEvent] = Field(default_factory=list)
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    model_calls: list[ModelCallEvent] = Field(default_factory=list)
