from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import Query
from sqlalchemy.orm import Session

from backend.app.database.models import (
    AnalysisRunRecord,
    FixPlanRecord,
    RepositoryRecord,
    RetrievalResultRecord,
)
from backend.app.database.repositories import (
    get_architecture_graph_for_analysis,
    get_analysis_run_record,
    get_fix_plan_for_analysis,
    get_retrieval_results_for_analysis,
    list_analysis_runs,
)
from backend.app.dependencies import get_db, get_settings
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import (
    AnalysisRunDetailResponse,
    AnalysisRunSummary,
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    PersistedFixPlan,
    PersistedRetrievalResult,
)
from backend.app.schemas.architecture import (
    ArchitectureFormat,
    ArchitectureGraph,
    ArchitectureSummary,
    PersistedArchitectureResponse,
)
from backend.app.schemas.repository import (
    RepositoryRecordResponse,
    to_repository_metadata_response,
)
from backend.app.settings import Settings
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow

router = APIRouter(prefix="/analysis", tags=["Analysis"])
ANALYSIS_ID_NOT_FOUND_MESSAGE = (
    "Analysis run not found. Make sure you are using analysis_run_id, not trace_run_id."
)


@router.get("", response_model=list[AnalysisRunSummary])
def list_analysis_history(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AnalysisRunSummary]:
    records = list_analysis_runs(db, limit=limit, offset=offset)
    response.headers["X-RepoPilot-Limit"] = str(limit)
    response.headers["X-RepoPilot-Offset"] = str(offset)
    response.headers["X-RepoPilot-Returned-Count"] = str(len(records))
    if offset > 0 and not records:
        response.headers["X-RepoPilot-Hint"] = (
            "No analysis runs at this offset. Try offset=0 to see the newest runs."
        )
    return [_to_analysis_summary(record) for record in records]


@router.post("/run", response_model=AnalyzeRepositoryResponse)
async def run_analysis(
    request: AnalyzeRepositoryRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AnalyzeRepositoryResponse:
    workflow = AnalyzeRepositoryWorkflow(
        repository_service=RepositoryService(settings.WORKSPACE_ROOT),
        db=db,
        settings=settings,
    )
    result = await workflow.run(request)
    return AnalyzeRepositoryResponse(
        run_id=result.run_id,
        trace_run_id=result.trace_run_id,
        analysis_run_id=result.analysis_run_id,
        repository=to_repository_metadata_response(result.repository),
        scan=result.scan,
        framework=result.framework,
        extracted_routes=result.extracted_routes,
        retrieval=result.retrieval,
        context_summary=result.context_summary,
        fix_plan=result.fix_plan,
    )


@router.get(
    "/{analysis_run_id}/architecture",
    response_model=PersistedArchitectureResponse,
)
def get_analysis_architecture(
    analysis_run_id: str,
    format: ArchitectureFormat = Query(default=ArchitectureFormat.json),
    db: Session = Depends(get_db),
) -> PersistedArchitectureResponse:
    analysis_run = get_analysis_run_record(db, analysis_run_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail=ANALYSIS_ID_NOT_FOUND_MESSAGE)

    record = get_architecture_graph_for_analysis(db, analysis_run_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Architecture graph is not available for this analysis run",
        )

    summary = ArchitectureSummary.model_validate(record.summary_json)
    if format == ArchitectureFormat.mermaid:
        return PersistedArchitectureResponse(
            analysis_run_id=analysis_run_id,
            framework=record.framework,
            mermaid=record.mermaid,
            summary=summary,
        )

    return PersistedArchitectureResponse(
        analysis_run_id=analysis_run_id,
        framework=record.framework,
        graph=ArchitectureGraph.model_validate(record.graph_json),
        summary=summary,
    )


@router.get("/{analysis_run_id}", response_model=AnalysisRunDetailResponse)
def get_analysis_run(
    analysis_run_id: str,
    db: Session = Depends(get_db),
) -> AnalysisRunDetailResponse:
    record = get_analysis_run_record(db, analysis_run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=ANALYSIS_ID_NOT_FOUND_MESSAGE)
    return _to_analysis_detail(
        record,
        retrieval_results=get_retrieval_results_for_analysis(db, analysis_run_id),
        fix_plan=get_fix_plan_for_analysis(db, analysis_run_id),
    )


def _to_analysis_summary(record: AnalysisRunRecord) -> AnalysisRunSummary:
    return AnalysisRunSummary(
        analysis_run_id=record.id,
        repository_id=record.repository_id,
        repo_name=record.repository.repo_name if record.repository else None,
        issue_text=record.issue_text,
        status=record.status,
        detected_framework=record.detected_framework,
        started_at=record.started_at,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


def _to_analysis_detail(
    record: AnalysisRunRecord,
    *,
    retrieval_results: list[RetrievalResultRecord],
    fix_plan: FixPlanRecord | None,
) -> AnalysisRunDetailResponse:
    return AnalysisRunDetailResponse(
        analysis_run_id=record.id,
        repository_id=record.repository_id,
        repository=_to_repository_response(record.repository),
        issue_text=record.issue_text,
        status=record.status,
        detected_framework=record.detected_framework,
        error_message=record.error_message,
        retrieval_results=[
            PersistedRetrievalResult(
                file_path=result.file_path,
                score=result.score,
                reason=result.reason,
            )
            for result in retrieval_results
        ],
        fix_plan=_to_fix_plan_response(fix_plan),
        started_at=record.started_at,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


def _to_repository_response(
    record: RepositoryRecord | None,
) -> RepositoryRecordResponse | None:
    if record is None:
        return None
    return RepositoryRecordResponse(
        repository_id=record.id,
        repo_name=record.repo_name,
        repo_url=record.repo_url,
        branch=record.branch,
        framework=record.framework,
        total_files=record.total_files,
    )


def _to_fix_plan_response(record: FixPlanRecord | None) -> PersistedFixPlan | None:
    if record is None:
        return None
    return PersistedFixPlan(
        suspected_issue=record.suspected_issue,
        root_cause=record.root_cause,
        files_to_change=record.files_to_change_json,
        fix_plan=record.fix_plan_json,
        validation_plan=record.validation_plan_json,
        confidence=record.confidence,
        risk_level=record.risk_level,
        requires_human_review=record.requires_human_review,
        assumptions=record.assumptions_json,
        created_at=record.created_at,
    )
