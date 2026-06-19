from enum import StrEnum

from pydantic import BaseModel, Field


class FileType(StrEnum):
    python = "python"
    test = "test"
    config = "config"
    markdown = "markdown"
    json = "json"
    yaml = "yaml"
    env = "env"
    text = "text"
    unknown = "unknown"


class ScannedFile(BaseModel):
    path: str
    file_type: FileType
    size_bytes: int = Field(ge=0)


class ScanResult(BaseModel):
    total_files: int
    python_files: int = 0
    test_files: int = 0
    config_files: int = 0
    markdown_files: int = 0
    json_files: int = 0
    yaml_files: int = 0
    env_files: int = 0
    text_files: int = 0
    unknown_files: int = 0
    files: list[ScannedFile]
