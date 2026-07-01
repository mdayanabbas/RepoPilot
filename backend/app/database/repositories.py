from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models import (
    AnalysisRunRecord,
    FixPlanRecord,
    ModelCallRecord,
    RepositoryRecord,
    RetrievalResultRecord,
    TraceEventRecord,
    ToolCallRecord,
)
from backend.app.database.models import utc_now
from backend.app.schemas.fix_plan import FixPlan
from backend.app.schemas.retrieval import RetrievalResult


def create_repository_record(
    db: Session,
    *,
    repo_name: str,
    local_path: str,
    repo_url: str | None = None,
    branch: str | None = None,
    framework: str | None = None,
    total_files: int = 0,
) -> RepositoryRecord:
    record = RepositoryRecord(
        repo_name=repo_name,
        repo_url=repo_url,
        local_path=local_path,
        branch=branch,
        framework=framework,
        total_files=total_files,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_repository_record(db: Session, repository_id: str) -> RepositoryRecord | None:
    return db.get(RepositoryRecord, repository_id)


def update_repository_record(
    db: Session,
    *,
    repository_id: str,
    framework: str | None = None,
    total_files: int | None = None,
) -> RepositoryRecord | None:
    record = db.get(RepositoryRecord, repository_id)
    if record is None:
        return None
    if framework is not None:
        record.framework = framework
    if total_files is not None:
        record.total_files = total_files
    db.commit()
    db.refresh(record)
    return record


def create_analysis_run_record(
    db: Session,
    *,
    repository_id: str,
    issue_text: str,
    status: str = "pending",
    detected_framework: str | None = None,
) -> AnalysisRunRecord:
    record = AnalysisRunRecord(
        repository_id=repository_id,
        issue_text=issue_text,
        status=status,
        detected_framework=detected_framework,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_analysis_run_status(
    db: Session,
    *,
    analysis_run_id: str,
    status: str,
    error_message: str | None = None,
    detected_framework: str | None = None,
) -> AnalysisRunRecord | None:
    record = db.get(AnalysisRunRecord, analysis_run_id)
    if record is None:
        return None

    record.status = status
    record.error_message = error_message
    if detected_framework is not None:
        record.detected_framework = detected_framework
    if status in {"success", "failed"}:
        record.completed_at = utc_now()
    db.commit()
    db.refresh(record)
    return record


def get_analysis_run_record(
    db: Session,
    analysis_run_id: str,
) -> AnalysisRunRecord | None:
    return db.get(AnalysisRunRecord, analysis_run_id)


def create_retrieval_result_records(
    db: Session,
    *,
    analysis_run_id: str,
    retrieval: RetrievalResult,
) -> list[RetrievalResultRecord]:
    records = [
        RetrievalResultRecord(
            analysis_run_id=analysis_run_id,
            file_path=file.file_path,
            score=file.score,
            reason=file.reason,
        )
        for file in retrieval.files
    ]
    db.add_all(records)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


def create_fix_plan_record(
    db: Session,
    *,
    analysis_run_id: str,
    fix_plan: FixPlan,
) -> FixPlanRecord:
    record = FixPlanRecord(
        analysis_run_id=analysis_run_id,
        suspected_issue=fix_plan.suspected_issue,
        root_cause=fix_plan.root_cause,
        files_to_change_json=[
            item.model_dump(mode="json") for item in fix_plan.files_to_change
        ],
        fix_plan_json={
            "steps": [item.model_dump(mode="json") for item in fix_plan.fix_plan]
        },
        validation_plan_json={
            "commands": [
                item.model_dump(mode="json") for item in fix_plan.validation_plan
            ]
        },
        confidence=fix_plan.confidence,
        risk_level=fix_plan.risk_level,
        requires_human_review=fix_plan.requires_human_review,
        assumptions_json=fix_plan.assumptions,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_trace_event_record(
    db: Session,
    *,
    run_id: str,
    step_name: str,
    status: str,
    duration_ms: int | None = None,
    metadata_json: dict[str, object] | None = None,
    error_message: str | None = None,
) -> TraceEventRecord:
    metadata = dict(metadata_json or {})
    if error_message is not None:
        metadata["error_message"] = error_message
    record = TraceEventRecord(
        run_id=run_id,
        step_name=step_name,
        status=status,
        duration_ms=duration_ms,
        metadata_json=metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_model_call_record(
    db: Session,
    *,
    run_id: str,
    provider: str,
    model: str,
    status: str,
    latency_ms: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    error_message: str | None = None,
) -> ModelCallRecord:
    record = ModelCallRecord(
        run_id=run_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        status=status,
        latency_ms=latency_ms,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_tool_call_record(
    db: Session,
    *,
    run_id: str,
    tool_name: str,
    status: str,
    duration_ms: int | None = None,
    input_json: dict[str, Any] | None = None,
    output_json: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> ToolCallRecord:
    record = ToolCallRecord(
        run_id=run_id,
        tool_name=tool_name,
        input_json=input_json or {},
        output_json=output_json or {},
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_trace_event_records(db: Session, run_id: str) -> list[TraceEventRecord]:
    return list(
        db.scalars(
            select(TraceEventRecord)
            .where(TraceEventRecord.run_id == run_id)
            .order_by(TraceEventRecord.created_at)
        )
    )


def list_model_call_records(db: Session, run_id: str) -> list[ModelCallRecord]:
    return list(
        db.scalars(
            select(ModelCallRecord)
            .where(ModelCallRecord.run_id == run_id)
            .order_by(ModelCallRecord.created_at)
        )
    )


def list_tool_call_records(db: Session, run_id: str) -> list[ToolCallRecord]:
    return list(
        db.scalars(
            select(ToolCallRecord)
            .where(ToolCallRecord.run_id == run_id)
            .order_by(ToolCallRecord.created_at)
        )
    )
