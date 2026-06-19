from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.base import Base
from backend.app.database.models import RepositoryRecord
from backend.app.database.repositories import (
    create_analysis_run_record,
    create_repository_record,
    create_trace_event_record,
)


def test_database_records_and_relationships() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()
    try:
        repository = create_repository_record(
            db,
            repo_name="sample-api",
            local_path="/tmp/sample-api",
            framework="fastapi",
            total_files=12,
        )
        analysis_run = create_analysis_run_record(
            db,
            repository_id=repository.id,
            issue_text="Import error on startup",
            status="running",
            detected_framework="fastapi",
        )
        trace_event = create_trace_event_record(
            db,
            run_id=analysis_run.id,
            step_name="scan",
            status="ok",
            duration_ms=25,
            metadata_json={"total_files": 12},
        )

        UUID(repository.id)
        UUID(analysis_run.id)
        UUID(trace_event.id)

        stored_repository = db.get(RepositoryRecord, repository.id)
        assert stored_repository is not None
        assert stored_repository.analysis_runs[0].id == analysis_run.id
        assert analysis_run.repository.id == repository.id
        assert trace_event.run_id == analysis_run.id
    finally:
        db.close()
