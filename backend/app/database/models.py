from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RepositoryRecord(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    local_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    framework: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    analysis_runs: Mapped[list["AnalysisRunRecord"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )


class AnalysisRunRecord(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id"),
        nullable=False,
    )
    issue_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    detected_framework: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    repository: Mapped[RepositoryRecord] = relationship(back_populates="analysis_runs")
    scan_results: Mapped[list["ScanResultRecord"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    code_symbols: Mapped[list["CodeSymbolRecord"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    retrieval_results: Mapped[list["RetrievalResultRecord"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    fix_plans: Mapped[list["FixPlanRecord"]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )


class ScanResultRecord(Base):
    __tablename__ = "scan_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id"),
        nullable=False,
    )
    total_files: Mapped[int] = mapped_column(Integer, nullable=False)
    python_files: Mapped[int] = mapped_column(Integer, nullable=False)
    config_files: Mapped[int] = mapped_column(Integer, nullable=False)
    test_files: Mapped[int] = mapped_column(Integer, nullable=False)
    ignored_files: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="scan_results")


class CodeSymbolRecord(Base):
    __tablename__ = "code_symbols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    symbol_type: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="code_symbols")


class RetrievalResultRecord(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="retrieval_results")


class FixPlanRecord(Base):
    __tablename__ = "fix_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_runs.id"),
        nullable=False,
    )
    suspected_issue: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    files_to_change_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    fix_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assumptions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="fix_plans")


class TraceEventRecord(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ModelCallRecord(Base):
    __tablename__ = "model_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ToolCallRecord(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
