from time import perf_counter
from typing import Any, Awaitable, Callable, TypeVar

from backend.app.schemas.llm import LLMRouterResponse
from backend.app.tracing.service import TraceService
from backend.app.tracing.trace_context import TraceContext

T = TypeVar("T", bound=LLMRouterResponse)


async def log_model_call(
    trace_service: TraceService,
    context: TraceContext,
    step_name: str,
    action: Callable[[], Awaitable[T]],
    *,
    metadata: dict[str, Any] | None = None,
) -> T:
    started_at = perf_counter()
    try:
        response = await action()
    except Exception as exc:
        trace_service.log_model_call(
            context,
            step_name=step_name,
            status="failed",
            duration_ms=_elapsed_ms(started_at),
            metadata=metadata,
            error_message=str(exc),
        )
        raise

    usage = response.response.usage
    trace_service.log_model_call(
        context,
        step_name=step_name,
        status="success",
        duration_ms=_elapsed_ms(started_at),
        provider=response.provider_used,
        model=response.response.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        metadata=metadata,
    )
    return response


def _elapsed_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
