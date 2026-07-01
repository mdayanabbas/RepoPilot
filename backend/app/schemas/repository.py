from enum import StrEnum

from pydantic import BaseModel, Field


class RepositorySourceType(StrEnum):
    local = "local"
    git = "git"


class LoadRepositoryRequest(BaseModel):
    source_type: RepositorySourceType
    source: str = Field(min_length=1)
    branch: str | None = None


class RepositoryMetadata(BaseModel):
    workspace_id: str
    repo_name: str
    source_type: str
    source: str
    local_path: str
    branch: str | None
    total_files: int


class RepositoryMetadataResponse(BaseModel):
    workspace_id: str
    repo_name: str
    source_type: str
    branch: str | None
    total_files: int


class RepositoryRecordResponse(BaseModel):
    repository_id: str
    repo_name: str
    repo_url: str | None = None
    branch: str | None = None
    framework: str | None = None
    total_files: int


def to_repository_metadata_response(
    metadata: RepositoryMetadata,
) -> RepositoryMetadataResponse:
    return RepositoryMetadataResponse(
        workspace_id=metadata.workspace_id,
        repo_name=metadata.repo_name,
        source_type=metadata.source_type,
        branch=metadata.branch,
        total_files=metadata.total_files,
    )
