from pydantic import BaseModel, Field

from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.framework import FrameworkDetectionResult
from backend.app.schemas.intelligence import RouteIndex
from backend.app.schemas.repository import RepositoryMetadata, RepositorySourceType
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
    repository: RepositoryMetadata
    scan: ScanResult
    framework: FrameworkDetectionResult
    extracted_routes: RouteIndex
    retrieval: RetrievalResult
    context_summary: AnalysisContextSummary
    fix_plan: FixPlan | None = None
