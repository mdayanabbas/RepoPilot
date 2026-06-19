from sqlalchemy.orm import Session

from backend.app.database.models import (
    AnalysisRunRecord,
    RepositoryRecord,
    TraceEventRecord,
)


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
) -> AnalysisRunRecord | None:
    record = db.get(AnalysisRunRecord, analysis_run_id)
    if record is None:
        return None

    record.status = status
    record.error_message = error_message
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
) -> TraceEventRecord:
    record = TraceEventRecord(
        run_id=run_id,
        step_name=step_name,
        status=status,
        duration_ms=duration_ms,
        metadata_json=metadata_json or {},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
