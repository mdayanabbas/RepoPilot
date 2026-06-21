from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

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


class FixPlan(StrictFixPlanModel):
    suspected_issue: str
    root_cause: str
    files_to_change: list[FileToChange]
    fix_plan: list[FixPlanStep]
    validation_plan: list[ValidationPlanItem]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    requires_human_review: bool
    assumptions: list[str]
