from backend.app.agent.service import LLMService
from backend.app.intelligence.route_index import RouteIndexer
from backend.app.intelligence.service import IntelligenceService
from backend.app.repository.service import RepositoryService
from backend.app.retrieval.context_builder import ContextBuilder
from backend.app.retrieval.service import RetrievalService
from backend.app.scanner.framework_detector import detect_framework
from backend.app.scanner.service import ScannerService
from backend.app.schemas.analysis import (
    AnalysisContextSummary,
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResult,
)
from backend.app.schemas.framework import SupportedFramework
from backend.app.schemas.intelligence import RouteIndex
from backend.app.schemas.repository import LoadRepositoryRequest
from backend.app.schemas.retrieval import ContextBuildInput, RetrievalInput
from backend.app.schemas.scan import ScanResult
from backend.app.settings import Settings
from backend.app.workflows.generate_fix_plan_workflow import (
    GenerateFixPlanWorkflow,
    LLMServiceProtocol,
)


class AnalyzeRepositoryWorkflow:
    def __init__(
        self,
        llm_service: LLMServiceProtocol | None = None,
        *,
        repository_service: RepositoryService | None = None,
        scanner_service: ScannerService | None = None,
        intelligence_service: IntelligenceService | None = None,
        route_indexer: RouteIndexer | None = None,
        retrieval_service: RetrievalService | None = None,
        context_builder: ContextBuilder | None = None,
        fix_plan_workflow: GenerateFixPlanWorkflow | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository_service = repository_service or RepositoryService()
        self.scanner_service = scanner_service or ScannerService()
        self.intelligence_service = intelligence_service or IntelligenceService()
        self.route_indexer = route_indexer or RouteIndexer()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.context_builder = context_builder or ContextBuilder(settings)

        if fix_plan_workflow is not None:
            self.fix_plan_workflow = fix_plan_workflow
        else:
            service = llm_service or LLMService(settings or Settings())
            self.fix_plan_workflow = GenerateFixPlanWorkflow(service)

    async def run(
        self,
        request: AnalyzeRepositoryRequest,
    ) -> AnalyzeRepositoryResult:
        repository = self.repository_service.load_repository(
            LoadRepositoryRequest(
                source_type=request.source_type,
                source=request.source,
                branch=request.branch,
            )
        )
        scan = self.scanner_service.scan_repository(repository.local_path)
        framework = detect_framework(repository.local_path, scan)
        symbol_index = self.intelligence_service.analyze_repository(
            repository.local_path,
            scan,
        )
        extracted_routes = self._extract_routes(
            repository.local_path,
            framework.framework,
            scan,
        )
        retrieval = self.retrieval_service.retrieve(
            RetrievalInput(
                issue_text=request.issue,
                scanned_files=scan.files,
                framework=framework.framework,
                symbol_index=symbol_index,
                route_index=extracted_routes,
            )
        )
        context = self.context_builder.build(
            ContextBuildInput(
                issue_text=request.issue,
                workspace_path=repository.local_path,
                framework=framework.framework,
                selected_files=retrieval.files,
                route_index=extracted_routes,
                symbol_index=symbol_index,
            )
        )
        fix_plan = None
        if framework.framework != SupportedFramework.unknown:
            fix_plan = await self.fix_plan_workflow.run(context)

        return AnalyzeRepositoryResult(
            repository=repository,
            scan=scan,
            framework=framework,
            extracted_routes=extracted_routes,
            retrieval=retrieval,
            context_summary=AnalysisContextSummary(
                selected_file_count=len(context.selected_files),
                relevant_route_count=len(context.relevant_routes),
                relevant_symbol_count=len(context.relevant_symbols),
                file_context_count=len(context.file_contexts),
                total_context_chars=context.total_context_chars,
            ),
            fix_plan=fix_plan,
        )

    async def analyze(
        self,
        request: AnalyzeRepositoryRequest,
    ) -> AnalyzeRepositoryResult:
        return await self.run(request)

    def _extract_routes(
        self,
        repository_path: str,
        framework: SupportedFramework,
        scan: ScanResult,
    ) -> RouteIndex:
        if framework not in {SupportedFramework.fastapi, SupportedFramework.flask}:
            return RouteIndex()
        return self.route_indexer.build(repository_path, framework, scan)
