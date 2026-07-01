from datetime import datetime

from pydantic import BaseModel, Field


class GitCommitInfo(BaseModel):
    commit_hash: str
    short_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    message: str
    changed_files: list[str] = Field(default_factory=list)


class FileChangeFrequency(BaseModel):
    file_path: str
    commit_count: int = Field(ge=0)
    last_modified_commit: str | None = None
    last_modified_at: datetime | None = None


class GitBlameLine(BaseModel):
    file_path: str
    line_number: int = Field(ge=1)
    commit_hash: str
    author_name: str
    committed_at: datetime
    line_content: str


class GitHistoryResult(BaseModel):
    recent_commits: list[GitCommitInfo] = Field(default_factory=list)
    change_frequency: list[FileChangeFrequency] = Field(default_factory=list)
    blame: list[GitBlameLine] = Field(default_factory=list)
