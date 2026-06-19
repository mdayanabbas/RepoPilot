from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.core.errors import RepoPilotError


def _error_response(error: RepoPilotError) -> dict[str, dict[str, object]]:
    return {
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
            "details": error.details,
        }
    }


async def repopilot_exception_handler(
    request: Request,
    exc: RepoPilotError,
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_response(exc))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RepoPilotError, repopilot_exception_handler)
