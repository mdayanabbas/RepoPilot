from fastapi import APIRouter

from backend.app.schemas.trace import TraceSummary
from backend.app.tracing.service import get_trace_service

router = APIRouter(prefix="/traces", tags=["Traces"])


@router.get("/{run_id}", response_model=TraceSummary)
def get_trace_events(run_id: str) -> TraceSummary:
    return get_trace_service().get_trace(run_id)
