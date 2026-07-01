from fastapi import APIRouter

from backend.app.api.v1.routes_analysis import router as analysis_router
from backend.app.api.v1.routes_architecture import router as architecture_router
from backend.app.api.v1.routes_health import router as health_router
from backend.app.api.v1.routes_llm import router as llm_router
from backend.app.api.v1.routes_repositories import router as repositories_router
from backend.app.api.v1.routes_traces import router as traces_router
from backend.app.dependencies import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.API_PREFIX)
api_router.include_router(health_router)
api_router.include_router(repositories_router)
api_router.include_router(architecture_router)
api_router.include_router(analysis_router)
api_router.include_router(llm_router)
api_router.include_router(traces_router)
