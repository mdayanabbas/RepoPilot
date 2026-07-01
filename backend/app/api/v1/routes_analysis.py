from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.repositories import get_analysis_run_record
from backend.app.dependencies import get_db, get_settings
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import (
    AnalysisRunResponse,
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
)
from backend.app.schemas.repository import to_repository_metadata_response
from backend.app.settings import Settings
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow

router = APIRouter(prefix="/analysis", tags=["Analysis"])


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
        analysis_run_id=result.analysis_run_id,
        repository=to_repository_metadata_response(result.repository),
        scan=result.scan,
        framework=result.framework,
        extracted_routes=result.extracted_routes,
        retrieval=result.retrieval,
        context_summary=result.context_summary,
        fix_plan=result.fix_plan,
    )


@router.get("/{analysis_run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(
    analysis_run_id: str,
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    record = get_analysis_run_record(db, analysis_run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunResponse(
        analysis_run_id=record.id,
        repository_id=record.repository_id,
        issue_text=record.issue_text,
        status=record.status,
        detected_framework=record.detected_framework,
        error_message=record.error_message,
    )
