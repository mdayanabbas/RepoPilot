from typing import TypedDict

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_settings
from backend.app.settings import Settings


class HealthResponse(TypedDict):
    status: str
    service: str
    version: str
    environment: str


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=None)
def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }
