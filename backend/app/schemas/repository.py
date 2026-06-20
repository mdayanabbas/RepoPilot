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
