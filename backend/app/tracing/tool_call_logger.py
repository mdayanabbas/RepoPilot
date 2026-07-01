from time import perf_counter
from typing import Any, Callable, TypeVar

from backend.app.tracing.service import TraceService
from backend.app.tracing.trace_context import TraceContext

T = TypeVar("T")


def log_tool_call(
    trace_service: TraceService,
    context: TraceContext,
    step_name: str,
    tool_name: str,
    action: Callable[[], T],
    *,
    input_metadata: dict[str, Any] | None = None,
) -> T:
    started_at = perf_counter()
    try:
        result = action()
    except Exception as exc:
        trace_service.log_tool_call(
            context,
            step_name=step_name,
            tool_name=tool_name,
            status="failed",
            duration_ms=_elapsed_ms(started_at),
            input_metadata=input_metadata,
            error_message=str(exc),
        )
        raise

    trace_service.log_tool_call(
        context,
        step_name=step_name,
        tool_name=tool_name,
        status="success",
        duration_ms=_elapsed_ms(started_at),
        input_metadata=input_metadata,
    )
    return result


def _elapsed_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
