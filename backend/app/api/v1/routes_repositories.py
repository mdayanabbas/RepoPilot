from fastapi import APIRouter, Depends

from backend.app.dependencies import get_settings
from backend.app.repository.service import RepositoryService
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
