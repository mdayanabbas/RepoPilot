from fastapi import APIRouter, Depends

from backend.app.agent.service import LLMService
from backend.app.dependencies import get_settings
from backend.app.schemas.llm import (
    LLMProvidersResponse,
    LLMTestRequest,
    LLMTestResponse,
)
from backend.app.settings import Settings

router = APIRouter(prefix="/llm", tags=["LLM"])
SUPPORTED_LLM_PROVIDERS = ["groq", "lmstudio"]


@router.get("/providers", response_model=LLMProvidersResponse)
def get_llm_providers(
    settings: Settings = Depends(get_settings),
) -> LLMProvidersResponse:
    return LLMProvidersResponse(
        primary_provider=settings.PRIMARY_LLM_PROVIDER,
        fallback_provider=settings.FALLBACK_LLM_PROVIDER,
        supported_providers=SUPPORTED_LLM_PROVIDERS,
    )


@router.post("/test", response_model=LLMTestResponse)
async def test_llm_provider(
    request: LLMTestRequest,
    settings: Settings = Depends(get_settings),
) -> LLMTestResponse:
    response = await LLMService(settings).generate_json(request.prompt)
    return LLMTestResponse(
        provider_used=response.provider_used,
        attempts=response.attempts,
        content=response.response.content,
    )
