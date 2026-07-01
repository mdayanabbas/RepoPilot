from time import perf_counter

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
from backend.app.tracing.event_logger import log_skipped_step, log_step
from backend.app.tracing.service import TraceService, get_trace_service
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
        trace_service: TraceService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.trace_service = trace_service or get_trace_service()
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
            self.fix_plan_workflow = GenerateFixPlanWorkflow(
                service,
                trace_service=self.trace_service,
            )

    async def run(
        self,
        request: AnalyzeRepositoryRequest,
    ) -> AnalyzeRepositoryResult:
        trace_context = self.trace_service.start_run(
            {
                "workflow": "analyze_repository",
                "source_type": request.source_type.value,
                "branch": request.branch,
                "issue_length": len(request.issue),
            }
        )
        repository = log_step(
            self.trace_service,
            trace_context,
            "load_repository",
            lambda: self.repository_service.load_repository(
                LoadRepositoryRequest(
                    source_type=request.source_type,
                    source=request.source,
                    branch=request.branch,
                )
            ),
            metadata={"source_type": request.source_type.value},
        )
        scan = log_step(
            self.trace_service,
            trace_context,
            "scan_repository",
            lambda: self.scanner_service.scan_repository(repository.local_path),
            metadata={"workspace_id": repository.workspace_id},
        )
        framework = log_step(
            self.trace_service,
            trace_context,
            "detect_framework",
            lambda: detect_framework(repository.local_path, scan),
            metadata={"total_files": scan.total_files},
        )
        symbol_index = log_step(
            self.trace_service,
            trace_context,
            "parse_python_ast",
            lambda: self.intelligence_service.analyze_repository(
                repository.local_path,
                scan,
            ),
            metadata={"python_files": scan.python_files},
        )
        extracted_routes = log_step(
            self.trace_service,
            trace_context,
            "extract_routes",
            lambda: self._extract_routes(
                repository.local_path,
                framework.framework,
                scan,
            ),
            metadata={"framework": framework.framework.value},
        )
        retrieval = log_step(
            self.trace_service,
            trace_context,
            "retrieve_files",
            lambda: self.retrieval_service.retrieve(
                RetrievalInput(
                    issue_text=request.issue,
                    scanned_files=scan.files,
                    framework=framework.framework,
                    symbol_index=symbol_index,
                    route_index=extracted_routes,
                )
            ),
            metadata={"route_count": len(extracted_routes.routes)},
        )
        context = log_step(
            self.trace_service,
            trace_context,
            "build_context",
            lambda: self.context_builder.build(
                ContextBuildInput(
                    issue_text=request.issue,
                    workspace_path=repository.local_path,
                    framework=framework.framework,
                    selected_files=retrieval.files,
                    route_index=extracted_routes,
                    symbol_index=symbol_index,
                )
            ),
            metadata={"selected_files": len(retrieval.files)},
        )
        fix_plan = None
        if framework.framework != SupportedFramework.unknown:
            started_at = perf_counter()
            try:
                fix_plan = await self.fix_plan_workflow.run(context, trace_context)
            except Exception as exc:
                self.trace_service.log_event(
                    trace_context,
                    step_name="generate_fix_plan",
                    status="failed",
                    duration_ms=_elapsed_ms(started_at),
                    metadata={"framework": framework.framework.value},
                    error_message=str(exc),
                )
                raise
            self.trace_service.log_event(
                trace_context,
                step_name="generate_fix_plan",
                status="success",
                duration_ms=_elapsed_ms(started_at),
                metadata={"framework": framework.framework.value},
            )
        else:
            log_skipped_step(
                self.trace_service,
                trace_context,
                "unknown_framework_skip_llm",
                metadata={"framework": framework.framework.value},
            )

        return AnalyzeRepositoryResult(
            run_id=trace_context.run_id,
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


def _elapsed_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
