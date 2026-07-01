import argparse
import asyncio

from backend.app.core.errors import LLMProviderError
from backend.app.schemas.analysis import AnalyzeRepositoryRequest
from backend.app.schemas.repository import RepositorySourceType
from backend.app.tracing.service import get_trace_service
from backend.app.workflows.analyze_repository_workflow import AnalyzeRepositoryWorkflow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a RepoPilot analysis smoke test.")
    parser.add_argument("source", help="Local repository path to analyze.")
    parser.add_argument("issue", help="Issue text to analyze.")
    parser.add_argument("--branch", default=None, help="Optional branch for git sources.")
    parser.add_argument(
        "--source-type",
        choices=[item.value for item in RepositorySourceType],
        default=RepositorySourceType.local.value,
        help="Repository source type.",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    workflow = AnalyzeRepositoryWorkflow()
    try:
        result = await workflow.run(
            AnalyzeRepositoryRequest(
                source_type=RepositorySourceType(args.source_type),
                source=args.source,
                branch=args.branch,
                issue=args.issue,
            )
        )
    except LLMProviderError as exc:
        _print_provider_error(exc)
        return
    trace = get_trace_service().get_trace(result.run_id)

    print(f"run_id: {result.run_id}")
    print(f"framework: {result.framework.framework.value}")
    print("selected_files:")
    for file in result.retrieval.files:
        print(f"- {file.file_path} score={file.score:.2f} reason={file.reason}")

    if result.fix_plan is None:
        print("fix_plan: skipped")
    else:
        print("fix_plan:")
        print(f"- suspected_issue: {result.fix_plan.suspected_issue}")
        print(f"- root_cause: {result.fix_plan.root_cause}")
        print(f"- confidence: {result.fix_plan.confidence:.2f}")
        print(f"- risk_level: {result.fix_plan.risk_level}")

    print("trace_steps:")
    for event in trace.events:
        print(
            "- "
            f"{event.step_name} "
            f"status={event.status} "
            f"duration_ms={event.duration_ms:.2f}"
        )
    for event in trace.model_calls:
        print(
            "- "
            f"{event.step_name} "
            f"status={event.status} "
            f"provider={event.provider or ''} "
            f"model={event.model or ''}"
        )


def _print_provider_error(error: LLMProviderError) -> None:
    print("Analysis smoke test failed during LLM provider call.")
    print(f"error: {error}")
    attempts = error.details.get("attempts", [])
    if attempts:
        print("attempts:")
        for attempt in attempts:
            print(
                "- "
                f"provider={attempt.get('provider')} "
                f"model={attempt.get('model')} "
                f"success={attempt.get('success')} "
                f"latency_ms={attempt.get('latency_ms')} "
                f"error={attempt.get('error') or ''}"
            )


if __name__ == "__main__":
    asyncio.run(main())
