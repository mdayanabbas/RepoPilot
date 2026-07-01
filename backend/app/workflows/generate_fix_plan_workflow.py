from typing import Any, Protocol

from backend.app.agent.prompt_builder import build_fix_plan_prompt
from backend.app.agent.schema_validator import validate_fix_plan_payload
from backend.app.schemas.fix_plan import FixPlan, FixPlanProviderMetadata
from backend.app.schemas.llm import LLMRouterResponse
from backend.app.schemas.retrieval import StructuredContext


class LLMServiceProtocol(Protocol):
    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMRouterResponse: ...


class GenerateFixPlanWorkflow:
    def __init__(self, llm_service: LLMServiceProtocol) -> None:
        self.llm_service = llm_service

    async def run(self, context: StructuredContext) -> FixPlan:
        prompt = build_fix_plan_prompt(context)
        router_response = await self.llm_service.generate_json(
            prompt,
            FixPlan.model_json_schema(),
        )
        fix_plan = validate_fix_plan_payload(router_response.response.content)
        fix_plan.attach_provider_metadata(_provider_metadata(router_response))
        return fix_plan

    async def generate(self, context: StructuredContext) -> FixPlan:
        return await self.run(context)


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
