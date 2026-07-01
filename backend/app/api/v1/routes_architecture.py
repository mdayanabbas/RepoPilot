from fastapi import APIRouter, Depends

from backend.app.architecture.service import ArchitectureService
from backend.app.dependencies import get_settings
from backend.app.intelligence.route_index import RouteIndexer
from backend.app.intelligence.service import IntelligenceService
from backend.app.repository.service import RepositoryService
from backend.app.scanner.framework_detector import detect_framework
from backend.app.scanner.service import ScannerService
from backend.app.schemas.architecture import (
    ArchitectureBuildResponse,
    ArchitectureFormat,
    BuildArchitectureRequest,
)
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.repository import LoadRepositoryRequest
from backend.app.settings import Settings

router = APIRouter(prefix="/architecture", tags=["Architecture"])


@router.post("/build", response_model=ArchitectureBuildResponse)
def build_architecture(
    request: BuildArchitectureRequest,
    settings: Settings = Depends(get_settings),
) -> ArchitectureBuildResponse:
    repository = RepositoryService(settings.WORKSPACE_ROOT).load_repository(
        LoadRepositoryRequest(
            source_type=request.source_type,
            source=request.source,
            branch=request.branch,
        )
    )
    scan = ScannerService().scan_repository(repository.local_path)
    framework = detect_framework(repository.local_path, scan).framework
    symbols = IntelligenceService().analyze_repository(repository.local_path, scan)
    routes = RouteIndexer().build(
        repository.local_path,
        (
            framework
            if framework in {SupportedFramework.fastapi, SupportedFramework.flask}
            else None
        ),
        scan,
    )
    architecture_service = ArchitectureService()
    graph = architecture_service.build_graph(
        scan_result=scan,
        symbol_index=symbols,
        route_index=routes,
    )
    mermaid = architecture_service.export_mermaid(graph)

    if request.format == ArchitectureFormat.mermaid:
        return ArchitectureBuildResponse(
            framework=framework,
            mermaid=mermaid,
            summary=graph.summary,
        )
    return ArchitectureBuildResponse(
        framework=framework,
        graph=graph,
        summary=graph.summary,
    )
