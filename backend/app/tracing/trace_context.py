from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceContext(BaseModel):
    run_id: str
    started_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
