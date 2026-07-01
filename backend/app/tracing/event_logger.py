from time import perf_counter
from typing import Any, Callable, TypeVar

from backend.app.tracing.service import TraceService
from backend.app.tracing.trace_context import TraceContext

T = TypeVar("T")


def log_step(
    trace_service: TraceService,
    context: TraceContext,
    step_name: str,
    action: Callable[[], T],
    *,
    metadata: dict[str, Any] | None = None,
) -> T:
    started_at = perf_counter()
    try:
        result = action()
    except Exception as exc:
        trace_service.log_event(
            context,
            step_name=step_name,
            status="failed",
            duration_ms=_elapsed_ms(started_at),
            metadata=metadata,
            error_message=str(exc),
        )
        trace_service.log_tool_call(
            context,
            step_name=step_name,
            tool_name=step_name,
            status="failed",
            duration_ms=_elapsed_ms(started_at),
            input_metadata=metadata,
            error_message=str(exc),
        )
        raise

    duration_ms = _elapsed_ms(started_at)
    trace_service.log_event(
        context,
        step_name=step_name,
        status="success",
        duration_ms=duration_ms,
        metadata=metadata,
    )
    trace_service.log_tool_call(
        context,
        step_name=step_name,
        tool_name=step_name,
        status="success",
        duration_ms=duration_ms,
        input_metadata=metadata,
    )
    return result


def log_skipped_step(
    trace_service: TraceService,
    context: TraceContext,
    step_name: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    trace_service.log_event(
        context,
        step_name=step_name,
        status="skipped",
        duration_ms=0.0,
        metadata=metadata,
    )


def _elapsed_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
