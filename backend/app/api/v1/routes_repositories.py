from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database.models import AnalysisRunRecord
from backend.app.database.repositories import (
    get_repository_record,
    list_repository_analysis_runs,
)
from backend.app.dependencies import get_db, get_settings
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import AnalysisRunSummary
from backend.app.schemas.repository import (
    LoadRepositoryRequest,
    RepositoryMetadataResponse,
    to_repository_metadata_response,
)
from backend.app.settings import Settings

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post("/load", response_model=RepositoryMetadataResponse)
def load_repository(
    request: LoadRepositoryRequest,
    settings: Settings = Depends(get_settings),
) -> RepositoryMetadataResponse:
    metadata = RepositoryService(settings.WORKSPACE_ROOT).load_repository(request)
    return to_repository_metadata_response(metadata)


@router.get("/{repository_id}/analyses", response_model=list[AnalysisRunSummary])
def list_repository_analyses(
    repository_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AnalysisRunSummary]:
    repository = get_repository_record(db, repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return [
        _to_analysis_summary(record)
        for record in list_repository_analysis_runs(
            db,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )
    ]


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
