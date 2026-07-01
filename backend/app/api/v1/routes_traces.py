from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.schemas.trace import TraceSummary
from backend.app.tracing.service import TraceService

router = APIRouter(prefix="/traces", tags=["Traces"])


@router.get("/{run_id}", response_model=TraceSummary)
def get_trace_events(
    run_id: str,
    db: Session = Depends(get_db),
) -> TraceSummary:
    return TraceService(db).get_trace(run_id)
