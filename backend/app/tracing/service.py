from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.schemas.trace import (
    ModelCallEvent,
    ToolCallEvent,
    TraceEvent,
    TraceStatus,
    TraceSummary,
)
from backend.app.tracing.trace_context import TraceContext


class TraceService:
    def __init__(self) -> None:
        self._runs: dict[str, TraceContext] = {}
        self._events: dict[str, list[TraceEvent]] = {}
        self._tool_calls: dict[str, list[ToolCallEvent]] = {}
        self._model_calls: dict[str, list[ModelCallEvent]] = {}

    def start_run(self, metadata: dict[str, Any] | None = None) -> TraceContext:
        context = TraceContext(
            run_id=str(uuid4()),
            started_at=_utc_now(),
            metadata=metadata or {},
        )
        self._runs[context.run_id] = context
        self._events[context.run_id] = []
        self._tool_calls[context.run_id] = []
        self._model_calls[context.run_id] = []
        return context

    def log_event(
        self,
        context: TraceContext,
        *,
        step_name: str,
        status: TraceStatus,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            run_id=context.run_id,
            step_name=step_name,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
            error_message=error_message,
            created_at=_utc_now(),
        )
        self._events.setdefault(context.run_id, []).append(event)
        return event

    def log_tool_call(
        self,
        context: TraceContext,
        *,
        step_name: str,
        tool_name: str,
        status: TraceStatus,
        duration_ms: float,
        input_metadata: dict[str, Any] | None = None,
        output_metadata: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ToolCallEvent:
        event = ToolCallEvent(
            run_id=context.run_id,
            step_name=step_name,
            tool_name=tool_name,
            status=status,
            duration_ms=duration_ms,
            input_metadata=input_metadata or {},
            output_metadata=output_metadata or {},
            metadata=metadata or {},
            error_message=error_message,
            created_at=_utc_now(),
        )
        self._tool_calls.setdefault(context.run_id, []).append(event)
        return event

    def log_model_call(
        self,
        context: TraceContext,
        *,
        step_name: str,
        status: TraceStatus,
        duration_ms: float,
        provider: str | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> ModelCallEvent:
        event = ModelCallEvent(
            run_id=context.run_id,
            step_name=step_name,
            status=status,
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            metadata=metadata or {},
            error_message=error_message,
            created_at=_utc_now(),
        )
        self._model_calls.setdefault(context.run_id, []).append(event)
        return event

    def get_trace(self, run_id: str) -> TraceSummary:
        context = self._runs.get(run_id)
        if context is None:
            context = TraceContext(run_id=run_id, started_at=_utc_now(), metadata={})

        return TraceSummary(
            run_id=run_id,
            started_at=context.started_at,
            metadata=context.metadata,
            events=sorted(
                self._events.get(run_id, []),
                key=lambda event: event.created_at,
            ),
            tool_calls=sorted(
                self._tool_calls.get(run_id, []),
                key=lambda event: event.created_at,
            ),
            model_calls=sorted(
                self._model_calls.get(run_id, []),
                key=lambda event: event.created_at,
            ),
        )


_trace_service = TraceService()


def get_trace_service() -> TraceService:
    return _trace_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
