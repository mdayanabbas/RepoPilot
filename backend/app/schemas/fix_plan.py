from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from backend.app.schemas.llm import LLMProviderAttempt, LLMUsage

RiskLevel: TypeAlias = Literal["low", "medium", "high"]


class StrictFixPlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FileToChange(StrictFixPlanModel):
    file_path: str
    reason: str
    risk: RiskLevel


class FixPlanStep(StrictFixPlanModel):
    step: int
    description: str
    target_file: str


class ValidationPlanItem(StrictFixPlanModel):
    command: str
    purpose: str


class FixPlanProviderMetadata(StrictFixPlanModel):
    provider_used: str
    model: str
    usage: LLMUsage
    latency_ms: float = Field(ge=0.0)
    attempts: list[LLMProviderAttempt]


class FixPlan(StrictFixPlanModel):
    _provider_metadata: FixPlanProviderMetadata | None = PrivateAttr(default=None)

    suspected_issue: str
    root_cause: str
    files_to_change: list[FileToChange]
    fix_plan: list[FixPlanStep]
    validation_plan: list[ValidationPlanItem]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    requires_human_review: bool
    assumptions: list[str]

    @property
    def provider_metadata(self) -> FixPlanProviderMetadata | None:
        return self._provider_metadata

    def attach_provider_metadata(
        self,
        metadata: FixPlanProviderMetadata,
    ) -> None:
        self._provider_metadata = metadata
