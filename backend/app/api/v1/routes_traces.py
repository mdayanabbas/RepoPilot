from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/traces", tags=["Traces"])


class TraceEventsResponse(BaseModel):
    run_id: str
    events: list[dict[str, object]] = Field(default_factory=list)


@router.get("/{run_id}", response_model=TraceEventsResponse)
def get_trace_events(run_id: str) -> TraceEventsResponse:
    return TraceEventsResponse(run_id=run_id, events=[])
