from backend.app.agent.provider_factory import ProviderFactory
from backend.app.agent.router import LLMRouter
from backend.app.schemas.llm import LLMRouterResponse
from backend.app.settings import Settings


class LLMService:
    def __init__(
        self,
        settings: Settings,
        *,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        factory = provider_factory or ProviderFactory(settings)
        self.router: LLMRouter = factory.create_router()

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict | None = None,
    ) -> LLMRouterResponse:
        return await self.router.generate_json(prompt, response_schema)
