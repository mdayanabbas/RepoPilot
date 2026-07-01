from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.database.repositories import (
    create_model_call_record,
    create_tool_call_record,
    create_trace_event_record,
    list_model_call_records,
    list_tool_call_records,
    list_trace_event_records,
)
from backend.app.schemas.trace import (
    ModelCallEvent,
    ToolCallEvent,
    TraceEvent,
    TraceStatus,
    TraceSummary,
)
from backend.app.tracing.trace_context import TraceContext


class TraceService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
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
        if self.db is not None:
            create_trace_event_record(
                self.db,
                run_id=context.run_id,
                step_name=step_name,
                status=status,
                duration_ms=_duration_to_int(duration_ms),
                metadata_json=event.metadata,
                error_message=error_message,
            )
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
        if self.db is not None:
            create_tool_call_record(
                self.db,
                run_id=context.run_id,
                tool_name=tool_name,
                status=status,
                duration_ms=_duration_to_int(duration_ms),
                input_json=event.input_metadata,
                output_json=event.output_metadata,
                error_message=error_message,
            )
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
        if self.db is not None:
            create_model_call_record(
                self.db,
                run_id=context.run_id,
                provider=provider or "",
                model=model or "",
                status=status,
                latency_ms=_duration_to_int(duration_ms),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                error_message=error_message,
            )
        return event

    def get_trace(self, run_id: str) -> TraceSummary:
        if self.db is not None:
            persisted = self._get_persisted_trace(run_id)
            if persisted is not None:
                return persisted

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

    def _get_persisted_trace(self, run_id: str) -> TraceSummary | None:
        if self.db is None:
            return None

        trace_records = list_trace_event_records(self.db, run_id)
        model_records = list_model_call_records(self.db, run_id)
        tool_records = list_tool_call_records(self.db, run_id)
        if not trace_records and not model_records and not tool_records:
            return None

        started_at = min(
            [
                record.created_at
                for record in [*trace_records, *model_records, *tool_records]
            ]
        )
        return TraceSummary(
            run_id=run_id,
            started_at=started_at,
            metadata={},
            events=[
                TraceEvent(
                    run_id=record.run_id,
                    step_name=record.step_name,
                    status=_status(record.status),
                    duration_ms=float(record.duration_ms or 0),
                    metadata=_trace_metadata(record.metadata_json),
                    error_message=_trace_error(record.metadata_json),
                    created_at=record.created_at,
                )
                for record in trace_records
            ],
            tool_calls=[
                ToolCallEvent(
                    run_id=record.run_id,
                    step_name=record.tool_name,
                    tool_name=record.tool_name,
                    status=_status(record.status),
                    duration_ms=float(record.duration_ms or 0),
                    input_metadata=record.input_json,
                    output_metadata=record.output_json,
                    error_message=record.error_message,
                    created_at=record.created_at,
                )
                for record in tool_records
            ],
            model_calls=[
                ModelCallEvent(
                    run_id=record.run_id,
                    step_name="call_llm",
                    status=_status(record.status),
                    duration_ms=float(record.latency_ms or 0),
                    provider=record.provider,
                    model=record.model,
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    total_tokens=record.total_tokens,
                    error_message=record.error_message,
                    created_at=record.created_at,
                )
                for record in model_records
            ],
        )


_trace_service = TraceService()


def get_trace_service() -> TraceService:
    return _trace_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _duration_to_int(duration_ms: float) -> int:
    return max(int(round(duration_ms)), 0)


def _status(status: str) -> TraceStatus:
    if status in {"success", "failed", "skipped"}:
        return status  # type: ignore[return-value]
    return "failed"


def _trace_error(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("error_message")
    return value if isinstance(value, str) else None


def _trace_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if key != "error_message"}
