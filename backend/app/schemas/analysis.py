from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.framework import FrameworkDetectionResult
from backend.app.schemas.intelligence import RouteIndex
from backend.app.schemas.repository import (
    RepositoryMetadata,
    RepositoryRecordResponse,
    RepositorySourceType,
)
from backend.app.schemas.repository import RepositoryMetadataResponse
from backend.app.schemas.retrieval import RetrievalResult
from backend.app.schemas.scan import ScanResult


class AnalyzeRepositoryRequest(BaseModel):
    source_type: RepositorySourceType
    source: str = Field(min_length=1)
    branch: str | None = None
    issue: str = Field(min_length=1)


class AnalysisContextSummary(BaseModel):
    selected_file_count: int = Field(ge=0)
    relevant_route_count: int = Field(ge=0)
    relevant_symbol_count: int = Field(ge=0)
    file_context_count: int = Field(ge=0)
    total_context_chars: int = Field(ge=0)


class AnalyzeRepositoryResult(BaseModel):
    run_id: str
    analysis_run_id: str | None = None
    repository: RepositoryMetadata
    scan: ScanResult
    framework: FrameworkDetectionResult
    extracted_routes: RouteIndex
    retrieval: RetrievalResult
    context_summary: AnalysisContextSummary
    fix_plan: FixPlan | None = None


class AnalyzeRepositoryResponse(BaseModel):
    run_id: str
    analysis_run_id: str | None = None
    repository: RepositoryMetadataResponse
    scan: ScanResult
    framework: FrameworkDetectionResult
    extracted_routes: RouteIndex
    retrieval: RetrievalResult
    context_summary: AnalysisContextSummary
    fix_plan: FixPlan | None = None


class AnalysisRunResponse(BaseModel):
    analysis_run_id: str
    repository_id: str
    issue_text: str
    status: str
    detected_framework: str | None = None
    error_message: str | None = None


class AnalysisRunSummary(BaseModel):
    analysis_run_id: str
    repository_id: str
    repo_name: str | None = None
    issue_text: str
    status: str
    detected_framework: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime


class PersistedRetrievalResult(BaseModel):
    file_path: str
    score: float = Field(ge=0.0)
    reason: str


class PersistedFixPlan(BaseModel):
    suspected_issue: str
    root_cause: str
    files_to_change: list[dict[str, Any]] = Field(default_factory=list)
    fix_plan: dict[str, Any] = Field(default_factory=dict)
    validation_plan: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: str
    requires_human_review: bool
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime


class AnalysisRunDetailResponse(BaseModel):
    analysis_run_id: str
    repository_id: str
    repository: RepositoryRecordResponse | None = None
    issue_text: str
    status: str
    detected_framework: str | None = None
    error_message: str | None = None
    retrieval_results: list[PersistedRetrievalResult] = Field(default_factory=list)
    fix_plan: PersistedFixPlan | None = None
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
