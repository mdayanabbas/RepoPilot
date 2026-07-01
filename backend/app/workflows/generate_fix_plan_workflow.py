from typing import Any, Protocol

from backend.app.agent.prompt_builder import build_fix_plan_prompt
from backend.app.agent.schema_validator import validate_fix_plan_payload
from backend.app.schemas.fix_plan import FixPlan, FixPlanProviderMetadata
from backend.app.schemas.llm import LLMRouterResponse
from backend.app.schemas.retrieval import StructuredContext
from backend.app.tracing.event_logger import log_step
from backend.app.tracing.model_call_logger import log_model_call
from backend.app.tracing.service import TraceService, get_trace_service
from backend.app.tracing.trace_context import TraceContext


class LLMServiceProtocol(Protocol):
    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMRouterResponse: ...


class GenerateFixPlanWorkflow:
    def __init__(
        self,
        llm_service: LLMServiceProtocol,
        *,
        trace_service: TraceService | None = None,
    ) -> None:
        self.llm_service = llm_service
        self.trace_service = trace_service or get_trace_service()

    async def run(
        self,
        context: StructuredContext,
        trace_context: TraceContext | None = None,
    ) -> FixPlan:
        active_trace = trace_context or self.trace_service.start_run(
            {"workflow": "generate_fix_plan"}
        )
        prompt = log_step(
            self.trace_service,
            active_trace,
            "build_prompt",
            lambda: build_fix_plan_prompt(context),
            metadata={
                "framework": context.framework.value,
                "selected_files": len(context.selected_files),
            },
        )
        router_response = await log_model_call(
            self.trace_service,
            active_trace,
            "call_llm",
            lambda: self.llm_service.generate_json(
                prompt,
                FixPlan.model_json_schema(),
            ),
            metadata={"response_schema": "FixPlan"},
        )
        fix_plan = log_step(
            self.trace_service,
            active_trace,
            "validate_fix_plan",
            lambda: validate_fix_plan_payload(router_response.response.content),
            metadata={"provider": router_response.provider_used},
        )
        fix_plan.attach_provider_metadata(_provider_metadata(router_response))
        return fix_plan

    async def generate(
        self,
        context: StructuredContext,
        trace_context: TraceContext | None = None,
    ) -> FixPlan:
        return await self.run(context, trace_context)


def _provider_metadata(
    router_response: LLMRouterResponse,
) -> FixPlanProviderMetadata:
    return FixPlanProviderMetadata(
        provider_used=router_response.provider_used,
        model=router_response.response.model,
        usage=router_response.response.usage,
        latency_ms=router_response.response.latency_ms,
        attempts=router_response.attempts,
    )
