from enum import StrEnum

from pydantic import BaseModel, Field


class SupportedFramework(StrEnum):
    fastapi = "fastapi"
    flask = "flask"
    unknown = "unknown"


class FrameworkSignal(BaseModel):
    framework: SupportedFramework
    source: str
    message: str
    weight: float = Field(ge=0.0, le=1.0)


class FrameworkDetectionResult(BaseModel):
    framework: SupportedFramework
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[FrameworkSignal]
