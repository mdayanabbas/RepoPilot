from fastapi import APIRouter

from backend.app.api.v1.routes_health import router as health_router
from backend.app.dependencies import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.API_PREFIX)
api_router.include_router(health_router)
