from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.api.v1.routes_health import router as health_router
from backend.app.dependencies import get_settings
from backend.app.exceptions import register_exception_handlers
from backend.app.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.APP_DEBUG,
        version="0.1.0",
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
