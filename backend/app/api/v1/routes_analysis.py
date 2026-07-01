from fastapi import APIRouter, Depends

from backend.app.dependencies import get_settings
from backend.app.repository.service import RepositoryService
from backend.app.schemas.analysis import (
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
) -> AnalyzeRepositoryResponse:
    workflow = AnalyzeRepositoryWorkflow(
        repository_service=RepositoryService(settings.WORKSPACE_ROOT),
        settings=settings,
    )
    result = await workflow.run(request)
    return AnalyzeRepositoryResponse(
        repository=to_repository_metadata_response(result.repository),
        scan=result.scan,
        framework=result.framework,
        extracted_routes=result.extracted_routes,
        retrieval=result.retrieval,
        context_summary=result.context_summary,
        fix_plan=result.fix_plan,
    )
